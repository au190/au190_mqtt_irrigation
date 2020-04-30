"""Support for MQTT irrigation."""
import logging
import sys
import json
import voluptuous as vol
import datetime
import homeassistant.helpers.config_validation as cv
import os
import asyncio

from homeassistant.components import mqtt
from homeassistant.components.switch import SwitchDevice
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.helpers.event import (async_track_time_change)
from homeassistant.const import (
    CONF_DEVICE,
    CONF_ICON,
    CONF_NAME,
    CONF_OPTIMISTIC,
    CONF_PAYLOAD_OFF,
    CONF_PAYLOAD_ON,
)
from homeassistant.components.mqtt import (
    CONF_COMMAND_TOPIC,
    CONF_QOS,
    CONF_RETAIN,
    CONF_UNIQUE_ID,
    MqttAttributes,
    MqttAvailability,
    MqttDiscoveryUpdate,
    MqttEntityDeviceInfo,
    subscription,
)

from . import (
    SERVICE_ATTRIBUTES,
    SERVICE_GET_INFO,
    SERVICE_SWITCH_ZONES,
    DOMAIN
)

_LOGGER = logging.getLogger(__name__)

CONF_TOPIC = "topic"
CONF_ZONE_IDs = "zones_ids"
CONF_MD_IDs = "md_ids"

CONF_MD_1 = "md1"
CONF_MD_2 = "md2"
CONF_MD_3 = "md3"
CONF_WATER_LIM = "waterLim"
CONF_RAIN_LIM = "rainLim"
CONF_MOTOR = "motor"

CONF_MD_1_TEMPLATE = "md1_value_template"
CONF_MD_2_TEMPLATE = "md2_value_template"
CONF_MD_3_TEMPLATE = "md3_value_template"
CONF_WATER_LIM_TEMPLATE = "waterLim_value_template"
CONF_RAIN_LIM_TEMPLATE = "rainLim_value_template"
CONF_MOTOR_TEMPLATE = "motor_value_template"
CONF_P_TEMPLATE = "power_value_template"
CONF_PD_TEMPLATE = "powdaily_value_template"
CONF_PM_TEMPLATE = "powmontly_value_template"

JSON_FILE = "_schedule_data.json"
JSON_DIR = "au190"

DEFAULT_NAME = "au190 MQTT irrigation"
DEFAULT_PAYLOAD_ON = "ON"
DEFAULT_PAYLOAD_OFF = "OFF"
DEFAULT_OPTIMISTIC = False
CONF_STATE_ON = "state_on"
CONF_STATE_OFF = "state_off"


#   Index id in the vector of the sensors
idx_Md1     = 0                       #motion detection
idx_Md2     = 1                       #motion detection
idx_Md3     = 2                       #motion detection
idx_RainL   = 3                       #index of Rain Limit
idx_WaterL  = 4                       #index of water Limit


MOTOR_RUNNING_ON    = True
WATER_LIMIT_ON      = True
MD_ON               = 1

MD_MAX_COUNT = 10                    # Max count the Md ON status in an interval of time
MD_TIME_INTERVAL = 5                 # Count MD ON status in x min


PLATFORM_SCHEMA = (
    mqtt.MQTT_RW_PLATFORM_SCHEMA.extend(
        {
            vol.Optional(CONF_COMMAND_TOPIC): "",
            vol.Optional(CONF_DEVICE): mqtt.MQTT_ENTITY_DEVICE_INFO_SCHEMA,
            vol.Optional(CONF_ICON): cv.icon,
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
            vol.Optional(CONF_OPTIMISTIC, default=DEFAULT_OPTIMISTIC): cv.boolean,
            vol.Optional(CONF_PAYLOAD_OFF, default=DEFAULT_PAYLOAD_OFF): cv.string,
            vol.Optional(CONF_PAYLOAD_ON, default=DEFAULT_PAYLOAD_ON): cv.string,

            vol.Required(CONF_ZONE_IDs, default=list): vol.All(cv.ensure_list, [cv.positive_int]),
            vol.Required(CONF_MD_IDs, default=list): vol.All(cv.ensure_list, [cv.positive_int]),
            vol.Required(CONF_TOPIC): cv.string,

            vol.Optional(CONF_MD_1): cv.string,
            vol.Optional(CONF_MD_2): cv.string,
            vol.Optional(CONF_MD_3): cv.string,
            vol.Optional(CONF_WATER_LIM): cv.string,
            vol.Optional(CONF_RAIN_LIM): cv.string,
            vol.Optional(CONF_MOTOR): cv.string,
            vol.Optional(CONF_MD_1_TEMPLATE): cv.template,
            vol.Optional(CONF_MD_2_TEMPLATE): cv.template,
            vol.Optional(CONF_MD_3_TEMPLATE): cv.template,
            vol.Optional(CONF_WATER_LIM_TEMPLATE): cv.template,
            vol.Optional(CONF_RAIN_LIM_TEMPLATE): cv.template,
            vol.Optional(CONF_MOTOR_TEMPLATE): cv.template,
            vol.Optional(CONF_P_TEMPLATE): cv.template,
            vol.Optional(CONF_PD_TEMPLATE): cv.template,
            vol.Optional(CONF_PM_TEMPLATE): cv.template,

            vol.Optional(CONF_STATE_OFF): cv.string,
            vol.Optional(CONF_STATE_ON): cv.string,
            vol.Optional(CONF_UNIQUE_ID): cv.string,
        }
    )
    .extend(mqtt.MQTT_AVAILABILITY_SCHEMA.schema)
    .extend(mqtt.MQTT_JSON_ATTRS_SCHEMA.schema)
)



async def async_setup_platform(  hass: HomeAssistantType, config: ConfigType, async_add_entities, discovery_info=None):
    """Set up MQTT irrigation through configuration.yaml."""
    await _async_setup_entity(hass, config, async_add_entities, discovery_info)

async def _async_setup_entity(hass, config, async_add_entities, config_entry=None, discovery_hash=None):
    """Set up the MQTT irrigation."""

    devices = []

    devices.append(Au190_MqttIrrigation(config, config_entry, discovery_hash))
    async_add_entities(devices, True)

    #- register Services
    async def async_service_get_data(service_name, service_data):
        """Handle the service call."""
        try:
            attr = dict(service_data)
            entity_id = service_data.get('entity_id')

            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", service_name, entity_id, attr)

            for device in devices:
                if device.entity_id == entity_id :
                    #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "] [%s][%s][%s]", device.entity_id, entity_id, attr)
                    if service_name == SERVICE_ATTRIBUTES:
                        await device.async_set_attributes(attr)
                    elif service_name == SERVICE_GET_INFO:
                        await device._reqInfo(attr)
                    elif service_name == SERVICE_SWITCH_ZONES:
                        attr["pulsetime"] = -1  # force to not use
                        await device.async_my_turn_on(**attr)



        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    async_dispatcher_connect(hass, DOMAIN, async_service_get_data)


# pylint: disable=too-many-ancestors
class Au190_MqttIrrigation(
    MqttAttributes,
    MqttAvailability,
    MqttDiscoveryUpdate,
    MqttEntityDeviceInfo,
    SwitchDevice,
    RestoreEntity,

):
    """Representation of a irrigation that can be toggled using MQTT."""

    def __init__(self, config, config_entry, discovery_hash):
        """Initialize the MQTT irrigation."""
        self._state = False
        self._sub_state = None

        self.topic = config.get(CONF_TOPIC)
        self._unique_id = config.get(CONF_UNIQUE_ID)
        self.zones_ids = config.get(CONF_ZONE_IDs)
        self.md_ids = config.get(CONF_MD_IDs)


        # au190
        self.no_of_zones = len(self.zones_ids)
        self._filename = None

        self._attrs = {}            #Holds the Config data from client
        self._irrigation = {}       #Holds local data

        # Load config
        self._setup_from_config(config)
        device_config = config.get(CONF_DEVICE)

        MqttAttributes.__init__(self, config)
        MqttAvailability.__init__(self, config)
        MqttDiscoveryUpdate.__init__(self, discovery_hash, self.discovery_update)
        MqttEntityDeviceInfo.__init__(self, device_config, config_entry)

    async def async_added_to_hass(self):
        """Subscribe to MQTT events."""
        await self._create_data()
        await super().async_added_to_hass()
        await self._subscribe_topics()
        await self._load_from_file()
        await self._reqInfo("")

    '''
    
    
    '''
    async def _create_data(self):
        try:

            if len(self.zones_ids) <= 0:

                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [Please define minimum one zone!]")

            self._irrigation.update({"command_info": "cmnd/" + self.topic + "/Status"})
            self._irrigation.update({"state_topic": "stat/" + self.topic + "/#"})

            # Attr config
            self._attrs.update({"au190": {"type":2}})

            command_list = []
            topics_list = []
            command_pulseTime_list = []
            state_pulseTime_list = []

            attr_status_list = []
            attr_enable_zone_list = []
            attr_pulsetime_list = []

            for x in self.zones_ids:

                command_list.append("cmnd/" + self.topic + "/POWER" + str(x))
                topics_list.append("stat/" + self.topic + "/POWER" + str(x))
                command_pulseTime_list.append("cmnd/" + self.topic + "/PulseTime" + str(x))
                state_pulseTime_list.append("PulseTime" + str(x))

                # Attr config
                attr_status_list.append("OFF")
                attr_enable_zone_list.append(False)
                attr_pulsetime_list.append(160)


                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s] [%s] [%s]", x, self._irrigation, x)

            command_list.append("cmnd/" + self.topic + "/POWER7")                   #Need for Motor turn ON/OFF
            topics_list.append("stat/" + self.topic + "/POWER7")                    #Need for Motor turn ON/OFF

            self._irrigation.update({"command_topics": command_list})
            self._irrigation.update({"command_pulse_times": command_pulseTime_list})
            self._irrigation.update({"state_topics": topics_list})                  # to check if the input topic is correct
            self._irrigation.update({"state_pulse_times": state_pulseTime_list})    # to check if the input topic is correct

            self._irrigation.update({"au190": {}})                                  # Only those vaules where I need former value

            self._irrigation["au190"]["WaterL_Fc"] = ""                             # List of callback Fc if != "" suspended WaterLim

            self._irrigation["au190"]['enable_irrig_sys'] = True                    # manual
            self._irrigation["au190"]['irrig_sys_status'] = True
            self._irrigation["au190"]['disable_req'] = 0                            # Who initiated the disable request (manual or error) 0-default, 1-manual, 2-error

            self._irrigation["au190"].update({"pulsetime": attr_pulsetime_list})    # Pulstime from the device, this walue is already set and confirmed


            self._irrigation["au190"]["md_status"] = []
            self._irrigation["au190"]["md_status"].append({"count": 0, "time": datetime.datetime.now()})                # Count the Md ON status in an interval of time
            self._irrigation["au190"]["md_status"].append({"count": 0, "time": datetime.datetime.now()})
            self._irrigation["au190"]["md_status"].append({"count": 0, "time": datetime.datetime.now()})


            self._irrigation["au190"]["motor"] = False
            self._irrigation["au190"]['scheduled_w_status'] = {"on": False, "fc_listener": ""}               #sche_w_status Scheduled watering status

            self._irrigation["au190"]["waterLim"] = False
            self._irrigation["au190"]["rainLim"] = False

            self._irrigation["au190"]["scheduler_fc"] = []                          #Holds the function list and the callback data

            # Attr config
            self._attrs["au190"]['enable_irrig_sys'] = True                         # True or False, manual enable disable
            self._attrs["au190"]['irrig_sys_status'] = True                         # True or False, diabled if motor runnin too long

            self._attrs["au190"].update({"status": attr_status_list})               # zone staus
            self._attrs["au190"].update({"enable_zone": attr_enable_zone_list})     # zone enable
            self._attrs["au190"].update({"pulsetime": attr_pulsetime_list})         # zone pulsetime

            self._attrs["au190"].update({"enable_scheduler": False})
            self._attrs["au190"].update({"scheduler": []})
            self._attrs["au190"]["irrigdays"] = [True,True,True,True,True,True,True]#Irrigation days

            self._attrs["au190"]["waterLim"] = False
            self._attrs["au190"]["waterLimLogic"] = False                           #Ater the sendor is on there is a timeout
            self._attrs["au190"]["rainLim"] = False
            self._attrs["au190"]["rainLimLogic"] = False                            #Ater the sendor is on there is a timeout
            self._attrs["au190"]["motor"] = False

            self._attrs["au190"]["P"] = 0
            self._attrs["au190"]["PD"] = 0
            self._attrs["au190"]["PW"] = 0
            self._attrs["au190"]["PM"] = 0
            self._attrs["au190"]["PY"] = 0

            self._attrs["au190"]["enable_md"] = False
            self._attrs["au190"]["md"] = []                                 #List contains the Start and End time
            self._attrs["au190"]["md_on_time"] = 100                        #If Md activated this irrigation will be on this amount of time in Esp special secconds - min value 10 sec max vaule is 10 min

            self._attrs["au190"]["md_status"] = []
            self._attrs["au190"]["md_status"].append(0)                     # 0-OFF 1-ON 2-Suspended
            self._attrs["au190"]["md_status"].append(0)
            self._attrs["au190"]["md_status"].append(0)


            self._attrs["au190"]["enable_protection"] = False

            self._attrs["au190"]["enable_waterL"] = False
            self._attrs["au190"]["waterLimTout"] = 60                       #After watrer limit reached, how long suspend the motor (system) in secconds - min value 1 min

            self._attrs["au190"]["enable_rainL"] = False
            self._attrs["au190"]["rainLimTout"] = 36000                     # If rany rany do not watering this time

            self._attrs["au190"]["enable_motorRunningToL"] = False
            self._attrs["au190"]["motorRunningTout"] = 60                   #If the motor running to long in secconds - min value 1 min


        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    async def discovery_update(self, discovery_payload):
        """Handle updated discovery message."""
        config = PLATFORM_SCHEMA(discovery_payload)
        self._setup_from_config(config)
        await self.attributes_discovery_update(config)
        await self.availability_discovery_update(config)
        await self.device_info_discovery_update(config)
        await self._subscribe_topics()
        self.async_write_ha_state()

    def _setup_from_config(self, config):
        """(Re)Setup the entity."""

        self._config = config

    async def _subscribe_topics(self):
        """(Re)Subscribe to topics."""

        _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s] [%s]", self.entity_id, self.name)

        my_dir = self.hass.config.path(JSON_DIR)
        self._filename = my_dir + os.sep + self.entity_id + JSON_FILE
        if not os.path.exists(my_dir):
            os.makedirs(my_dir)

        topics = {}
        qos = self._config[CONF_QOS]

        def add_subscription(topics, topic, msg_callback):
            topics[topic] = {
                "topic": topic,
                "msg_callback": msg_callback,
                "qos": qos,
            }

        '''
            if template exist   rerender 
            if not exist        return the msg.payload
        '''
        def render_template(msg, template_name):

            template = self._config.get(template_name)
            if template is not None:
                template.hass = self.hass
                payload = template.async_render_with_possible_json_value(msg.payload, "")
            else:
                payload = msg.payload
            return payload


        @callback
        def state_message_md_1(msg):
            """Handle new MQTT state messages."""
            try:
                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)

                self._md_update_status(0, msg.payload)
                asyncio.run_coroutine_threadsafe(self._md_logic(0), self.hass.loop)  # .result()


            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


        @callback
        def state_message_md_2(msg):
            """Handle new MQTT state messages."""
            try:
                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)

                self._md_update_status(1, msg.payload)
                asyncio.run_coroutine_threadsafe(self._md_logic(1), self.hass.loop)  # .result()


            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


        @callback
        def state_message_md_3(msg):
            """Handle new MQTT state messages."""
            try:
                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)

                self._md_update_status(2, msg.payload)
                asyncio.run_coroutine_threadsafe(self._md_logic(2), self.hass.loop)  # .result()


            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


        @callback
        def state_message_waterLim(msg):
            """Handle new MQTT state messages."""
            try:
                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)

                self._attrs["au190"]["waterLim"] = self.convToBool(msg.payload)
                asyncio.run_coroutine_threadsafe(self._waterLim_logic(), self.hass.loop)  # .result()


            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


        @callback
        def state_message_rainLim(msg):
            """Handle new MQTT state messages."""
            try:
                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)

                self._attrs["au190"]["rainLim"] = self.convToBool(msg.payload)
                asyncio.run_coroutine_threadsafe(self._rainLim_logic(), self.hass.loop)  # .result()


            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


        @callback
        def state_message_motor(msg):
            """Handle new MQTT state messages."""
            try:
                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)

                self._attrs["au190"]["motor"] = self.convToBool(msg.payload)
                asyncio.run_coroutine_threadsafe(self._motorRunningToL_logic(), self.hass.loop)  # .result()


            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


        '''
           If the state topic has template the message comes here
        '''
        @callback
        def state_message_sensors(msg):
            """Handle new MQTT state messages."""
            try:
                #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)

                data = render_template(msg, CONF_MD_1_TEMPLATE)
                if data != "":
                    self._md_update_status(0, data)
                    asyncio.run_coroutine_threadsafe(self._md_logic(0), self.hass.loop)  # .result()

                data = render_template(msg, CONF_MD_2_TEMPLATE)
                if data != "":
                    self._md_update_status(1, data)
                    asyncio.run_coroutine_threadsafe(self._md_logic(1), self.hass.loop)  # .result()

                data = render_template(msg, CONF_MD_3_TEMPLATE)
                if data != "":
                    self._md_update_status(2, data)
                    asyncio.run_coroutine_threadsafe(self._md_logic(2), self.hass.loop)  # .result()

                data = render_template(msg, CONF_WATER_LIM_TEMPLATE)
                if data != "":
                    self._attrs["au190"]["waterLim"] = self.convToBool(data)
                    asyncio.run_coroutine_threadsafe(self._waterLim_logic(), self.hass.loop)  # .result()

                data = render_template(msg, CONF_RAIN_LIM_TEMPLATE)
                if data != "":
                    self._attrs["au190"]["rainLim"] = self.convToBool(data)
                    asyncio.run_coroutine_threadsafe(self._rainLim_logic(), self.hass.loop)  # .result()

                data = render_template(msg, CONF_MOTOR_TEMPLATE)
                if data != "":
                    self._attrs["au190"]["motor"] = self.convToBool(data)

                    try:
                        # ---    If irrig_sys_status is disabled fore the value to zero
                        if (not self._irrigation["au190"]['enable_irrig_sys'] or not self._irrigation["au190"]['irrig_sys_status']):

                            self._attrs["au190"]["motor"] = False
                            self._attrs["au190"]["P"] = 0

                        else:  # Update power data

                            self._attrs["au190"]["P"]  = render_template(msg, CONF_P_TEMPLATE)
                            self._attrs["au190"]["PD"] = render_template(msg, CONF_PD_TEMPLATE)
                            #self._attrs["au190"]["PW"] = render_template(msg, "{{ value_json.PW }}")
                            self._attrs["au190"]["PM"] = render_template(msg, CONF_PM_TEMPLATE)
                            #self._attrs["au190"]["PY"] = render_template(msg, "{{ value_json.PY }}")

                    except Exception as e1:{}

                    asyncio.run_coroutine_threadsafe(self._motorRunningToL_logic(), self.hass.loop)#.result()

            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

        @callback
        def state_message_received(msg):
            """Handle new MQTT state messages."""
            try:
                payload = msg.payload
                topic = msg.topic
                pL_o = {}
                #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", topic, payload, msg)
                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)

                if msg.payload[0] == "{":

                    pL_o = json.loads(msg.payload)  # decode json data
                    first_element = list(pL_o.keys())[0]

                    if self.isInList("state_pulse_times", first_element) >= 0:

                        id = self.isInList("state_pulse_times", first_element)
                        self._irrigation["au190"]["pulsetime"][id] = pL_o[first_element]["Set"]

                        '''
                            turn ON for while
                            
                        '''
                        self._publish(self._irrigation["command_topics"][id], self._config[CONF_PAYLOAD_ON])

                        self.myasync_write_ha_state()
                        _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]-x- [%s][%s]", id, payload)

                    elif self.my_hasattr_Idx(pL_o, 'StatusNET'):

                        self._attrs.update({'IpAddress': pL_o['StatusNET']['IPAddress']})
                        self.myasync_write_ha_state()

                    elif self.my_hasattr_Idx(pL_o, 'StatusSTS'):

                        self._attrs.update({'SSId': pL_o['StatusSTS']['Wifi']['SSId'] + " (" + str(pL_o['StatusSTS']['Wifi']['RSSI']) + "%)"})
                        self._attrs.update({'Uptime': pL_o['StatusSTS']['Uptime']})
                        self._attrs.update({'Time': pL_o['StatusSTS']['Time']})
                        self.myasync_write_ha_state()

                else:

                    id = self.isInList("state_topics", topic) #stat/irrig/POWER1

                    if id >= 0 and id < self.no_of_zones: # On Off Zones

                       self._attrs["au190"]["status"][id] = payload
                       self.myasync_write_ha_state()
                       _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]zone_%s [%s]", id, self._attrs["au190"]["status"])

                    elif id == self.no_of_zones:# Motor turon ON/OFF

                        '''
                            Update the status only after motor OFF or ON its confiremd form the Mosquitto broker
                            Only if the request(disable_req) was comming from 
                                1.  manual 
                                2.  error motor running too long
                        '''
                        if payload == "ON":     #ok
                            self._attrs["au190"]['enable_irrig_sys'] = True
                            self._attrs["au190"]['irrig_sys_status'] = True
                            self._irrigation["au190"]['enable_irrig_sys'] = True
                            self._irrigation["au190"]['irrig_sys_status'] = True

                            #--------------------------------------------------------------------------------------------------------------------------------------
                            #   Manual enable, reset all var to default
                            #   Do not reset the attrs data that contains the sensor data - its automatically updated in every x min
                            #--------------------------------------------------------------------------------------------------------------------------------------
                            if self._irrigation["au190"]['disable_req'] == 1:   #Manual enable, reset all var to default


                                asyncio.run_coroutine_threadsafe(self._clear_motorRunningToLFc(), self.hass.loop)  # .result()
                                self._irrigation["au190"]["motor"] = False

                                self._irrigation["au190"]["waterLim"] = False
                                self._attrs["au190"]["waterLimLogic"] = False
                                asyncio.run_coroutine_threadsafe(self._clear_WaterLFc(), self.hass.loop)  # .result()

                                self._irrigation["au190"]["rainLim"] = False

                                asyncio.run_coroutine_threadsafe(self._motorRunningToL_logic(), self.hass.loop)  # .result()
                                asyncio.run_coroutine_threadsafe(self._waterLim_logic(), self.hass.loop)  # .result()
                                asyncio.run_coroutine_threadsafe(self._rainLim_logic(), self.hass.loop)  # .result()
                                #asyncio.run_coroutine_threadsafe(self._md_logic(0), self.hass.loop)  # .result()
                                #asyncio.run_coroutine_threadsafe(self._md_logic(1), self.hass.loop)  # .result()
                                #asyncio.run_coroutine_threadsafe(self._md_logic(2), self.hass.loop)  # .result()

                                self._irrigation["au190"]["md_status"] = []
                                self._irrigation["au190"]["md_status"].append({"count": 0, "time": datetime.datetime.now()})  # Count the Md ON status in an interval of time
                                self._irrigation["au190"]["md_status"].append({"count": 0, "time": datetime.datetime.now()})
                                self._irrigation["au190"]["md_status"].append({"count": 0, "time": datetime.datetime.now()})

                                self._attrs["au190"]["md_status"] = []
                                self._attrs["au190"]["md_status"].append(0)  # 0-OFF 1-ON 2-Suspended
                                self._attrs["au190"]["md_status"].append(0)
                                self._attrs["au190"]["md_status"].append(0)


                        elif payload == "OFF": #nok
                            # update oly after its confiremd form the Mosquitto broker
                            if self._irrigation["au190"]['disable_req'] == 1:
                                self._attrs["au190"]['enable_irrig_sys'] = False
                                self._irrigation["au190"]['enable_irrig_sys'] = False
                            elif self._irrigation["au190"]['disable_req'] == 2:
                                self._attrs["au190"]['irrig_sys_status'] = False
                                self._irrigation["au190"]['irrig_sys_status'] = False

                        self._irrigation["au190"]['disable_req'] = 0 #set to default
                        self.myasync_write_ha_state()

            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))



        if self._config.get(CONF_MD_1) is not None and self._config.get(CONF_MD_1_TEMPLATE) is not None:
            add_subscription(topics, self._config.get(CONF_MD_1), state_message_sensors)
        elif self._config.get(CONF_MD_1) is not None:
            add_subscription(topics, self._config.get(CONF_MD_1), state_message_md_1)

        if self._config.get(CONF_MD_2) is not None and self._config.get(CONF_MD_2_TEMPLATE) is not None:
            add_subscription(topics, self._config.get(CONF_MD_2), state_message_sensors)
        elif self._config.get(CONF_MD_2) is not None:
            add_subscription(topics, self._config.get(CONF_MD_2), state_message_md_2)

        if  self._config.get(CONF_MD_3) is not None and self._config.get(CONF_MD_3_TEMPLATE) is not None:
            add_subscription(topics, self._config.get(CONF_MD_3), state_message_sensors)
        elif self._config.get(CONF_MD_3) is not None:
            add_subscription(topics, self._config.get(CONF_MD_3), state_message_md_3)

        if self._config.get(CONF_WATER_LIM) is not None and self._config.get(CONF_WATER_LIM_TEMPLATE) is not None:
            add_subscription(topics, self._config.get(CONF_WATER_LIM), state_message_sensors)
        elif self._config.get(CONF_WATER_LIM) is not None:
            add_subscription(topics, self._config.get(CONF_WATER_LIM), state_message_waterLim)

        if  self._config.get(CONF_RAIN_LIM) is not None and self._config.get(CONF_RAIN_LIM_TEMPLATE) is not None:
            add_subscription(topics, self._config.get(CONF_RAIN_LIM), state_message_sensors)
        elif self._config.get(CONF_RAIN_LIM) is not None:
            add_subscription(topics, self._config.get(CONF_RAIN_LIM), state_message_rainLim)

        if  self._config.get(CONF_MOTOR) is not None and self._config.get(CONF_MOTOR_TEMPLATE) is not None:
            add_subscription(topics, self._config.get(CONF_MOTOR), state_message_sensors)
        elif self._config.get(CONF_MOTOR) is not None:
            add_subscription(topics, self._config.get(CONF_MOTOR), state_message_motor)

        add_subscription(topics, self._irrigation["state_topic"], state_message_received)

        self._sub_state = await subscription.async_subscribe_topics(self.hass, self._sub_state, topics)


    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        self._sub_state = await subscription.async_unsubscribe_topics(self.hass, self._sub_state)
        await MqttAttributes.async_will_remove_from_hass(self)
        await MqttAvailability.async_will_remove_from_hass(self)


    @property
    def state_attributes(self):
        """Return the optional state attributes."""
        #self._attrs["time"] = time.time() #if no change in the attr - no event in the client
        #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s", self._attrs)
        return self._attrs

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the irrigation."""
        return self._config[CONF_NAME]

    @property
    def is_on(self):
        """Return true if device is on."""
        #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s", self._state)
        return self._state

    @property
    def assumed_state(self):
        """Return true if we do optimistic updates."""
        return False

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def icon(self):
        """Return the icon."""
        return self._config.get(CONF_ICON)

    async def async_turn_on(self, **kwargs):
        None

    '''
        min turn on is 10 sec
        
        kwargs  - zone
                - pulsetime - if missing using from config
    
    '''
    async def async_my_turn_on(self, **kwargs):
        """
        Turn the device on.
        This method is a coroutine.
        """
        try:
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", kwargs)

            if  (not self._irrigation["au190"]['enable_irrig_sys'] or not self._irrigation["au190"]['irrig_sys_status']
                  or self._attrs["au190"]["waterLimLogic"]
                ): #

                    return

            id = int(kwargs["zone"])
            allways_on = False
            if 'allways_on' in kwargs:
                allways_on = kwargs["allways_on"]
                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> allways_on [%s]", allways_on)


            if self._attrs["au190"]["status"][id] == self._config[CONF_PAYLOAD_OFF] or allways_on:

                self.async_turn_off_all_zones(id)

                if kwargs["pulsetime"] >= 0:  # comming form Md
                    running_time = kwargs["pulsetime"]
                else:
                    running_time = self._attrs["au190"]["pulsetime"][id]

                pulseTime = self._forceTimeLimit(running_time, 112, 112)

                if (self._irrigation["au190"]["pulsetime"][id] != pulseTime):

                    self._publish(self._irrigation["command_pulse_times"][id], pulseTime)

                else:
                    #Just turn ON
                    self._publish(self._irrigation["command_topics"][id], self._config[CONF_PAYLOAD_ON])
            else:
                # Just turn OFF
                self._publish(self._irrigation["command_topics"][id], self._config[CONF_PAYLOAD_OFF])

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    '''
        Optimistic mode
    '''
    def async_turn_off_all_zones(self, id):
        was_on = False
        idx = 0
        for zone_id in self._attrs["au190"]["status"]:
            if zone_id != self._config[CONF_PAYLOAD_OFF] and idx != id:
                was_on = True
                self._publish(self._irrigation["command_topics"][idx], self._config[CONF_PAYLOAD_OFF])
                #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s]", idx, id)
            idx = idx + 1

        #if was_on: #time delay between on and off
            #await asyncio.sleep(0.5) #second

    def _publish(self, topic, payload):

        _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s]", topic, payload)
        try:
            mqtt.async_publish(
                self.hass,
                topic,
                payload,
                self._config[CONF_QOS],
                self._config[CONF_RETAIN],
            )

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    async def _reqInfo(self, data):
        #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", self.entity_id)
        self._publish(self._irrigation["command_info"], 0)

    '''
        1.  Get data from client
        2.  Save to file
        3.  Load data from file
        4.  Update the attributes local var
        5.  Sends back to client the new variable and updates the client
        6.  Updates the 
    '''
    async def async_set_attributes(self, data):
        """ ."""
        try:
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", data)
            await self._save_to_file(data["au190"])
            await self._load_from_file()
            self.myasync_write_ha_state()

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    async def _zone_on(self, id, pulsetime = -1, allways_on = False):
        _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", id, pulsetime, allways_on)

        if self._attrs["au190"]["irrigdays"][datetime.datetime.now().weekday()] or allways_on:

            kwargs = {}
            kwargs['zone'] = id
            kwargs['pulsetime'] = pulsetime
            kwargs['allways_on'] = allways_on

            await self.async_my_turn_on(**kwargs)

    async def _async_wake_up(self, acction_time):
        try:
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", acction_time)

            id = None
            for entry in self._irrigation["au190"]["scheduler_fc"]:

                start_time = entry['start_time']

                if start_time.hour == acction_time.hour and start_time.minute == acction_time.minute and start_time.second == acction_time.second:
                    id = entry['id']
                    break

            if id != None:
                await self._md_update_scheduled_on()
                await self._zone_on(id)
            else:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: Invalid Time: [%s]", acction_time)

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    '''
        
    '''
    async def _setSchedulerTask(self):
        try:
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]%s", self.entity_id, self._attrs["au190"])

            # --- Manual Enable/Disable Irrigation system
            await self._enable_irrigation_system1(self._attrs["au190"]['enable_irrig_sys'])


            # --- Remove all scheduler listener
            for entry in self._irrigation["au190"]["scheduler_fc"]:
                #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]-- [%s]", fc_listener)
                fc_listener = entry["fc_listener"]
                fc_listener()
            self._irrigation["au190"]["scheduler_fc"] = []

            #--- Set scheduler for zones
            FMT = '%H:%M:%S'

            if self._attrs["au190"]['enable_scheduler']:
                for start_time in self._attrs["au190"]['scheduler']:

                    start_time = start_time + ":00"
                    #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", start_time)

                    idx = 0
                    for id in range(len(self._attrs["au190"]["enable_zone"])):

                        if self._attrs["au190"]["enable_zone"][id]:

                            #duration = self._forceTimeLimit(self._attrs["au190"]["pulsetime"][id], 130, 130) - 100  # Convert to seconnds
                            if idx == 0:
                                idx = + 1
                                starttime = datetime.datetime.strptime(start_time, FMT)  # delay x sec between zonees
                                #start_time = starttime.strftime(FMT)
                            else:
                                previous_run = self._forceTimeLimit(self._attrs["au190"]["pulsetime"][previous_id], 112, 112) - 100  # Convert to seconnds
                                starttime = starttime + datetime.timedelta(seconds=previous_run) + datetime.timedelta(seconds=1)  # delay x sec between zonees


                            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "] - [Zone%s][%s:%s:%s][%s]", (id+1), starttime.hour, starttime.minute, starttime.second, duration)
                            fc_listener = async_track_time_change(self.hass, self._async_wake_up, hour=starttime.hour, minute=starttime.minute, second=starttime.second)
                            self._irrigation["au190"]["scheduler_fc"].append({"start_time": starttime, "id": id, "fc_listener": fc_listener})

                            previous_id = id

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    async def _motorRunningToL_logic(self):
        try:
            '''
                motorRunningToLong
                motorRunningTout = in secconds - min value 1 min

                1.  If enable_irrig_sys and irrig_sys_status enabled
                2.  If enabled enable_motorRunningToL and enable_protection and
                3.  If Motor status changed
                4.  
            '''
            if (self._irrigation["au190"]['enable_irrig_sys'] and self._irrigation["au190"]['irrig_sys_status'] and
                self._attrs["au190"]["enable_motorRunningToL"] and self._attrs["au190"]["enable_protection"] and
                self._attrs["au190"]["motor"] != self._irrigation["au190"]["motor"]
            ):

                if self._attrs["au190"]["motor"] == MOTOR_RUNNING_ON:

                    # ---    Add time out for Motor

                    duration = int(self._attrs["au190"]["motorRunningTout"])

                    if duration < 60:
                        duration = 60

                    starttime = datetime.datetime.now() + datetime.timedelta(seconds=duration)

                    fc_listener = async_track_time_change(self.hass, self._enable_irrigation_system2(False), hour=starttime.hour, minute=starttime.minute, second=starttime.second)
                    self._irrigation["au190"]["motorRunningToL_Fc"] = fc_listener

                    _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> ###1### motorRunningToLong [%s][%s]", self._attrs["au190"], starttime)

                else:
                    await self._clear_motorRunningToLFc()
                    _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> ###0### motorRunningToLong [%s]", self._attrs["au190"])

            self._irrigation["au190"]["motor"] = self._attrs["au190"]["motor"]
            self.myasync_write_ha_state()

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    async def _md_logic(self, zone):
        try:
            '''
              zone starts with index 0
              
              md_on_time = in Esp special secconds - min value 10 sec max vaule is 10 min

              1.  If enable_irrig_sys and irrig_sys_status enabled
              2.  If not suspended self._irrigation["au190"]["WaterL_Fc"] = ""
              3.  If enabled enable_md
              4.  If times between the set time
              5.  If no self._irrigation["au190"]['scheduled_w_status']['on'] If not running the Scheduled watering
              6.  Count the ON status in 10 min interval if the count is > x disable that Md on that zome

            '''
            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> Zone%s", zone)

            if (self._irrigation["au190"]['enable_irrig_sys'] and self._irrigation["au190"]['irrig_sys_status'] and
                self._irrigation["au190"]["WaterL_Fc"] == "" and
                self._attrs["au190"]["enable_md"] and
                await self._check_md_times() and
                not self._irrigation["au190"]['scheduled_w_status']['on']
            ):

                md_on_time = int(self._attrs["au190"]["md_on_time"])
                if md_on_time < 100 or md_on_time > 700:
                    md_on_time = 100

                if self._attrs["au190"]["md_status"][zone] == MD_ON and self._irrigation["au190"]["md_status"][zone]["count"] < MD_MAX_COUNT:
                    '''
                       Count the ON status in 5 min interval
                       if the count is > x disable that Md on that zome
                       else reset the counter 
                    '''

                    if self._time_duration(self._irrigation["au190"]["md_status"][zone]["time"], datetime.datetime.now()) > MD_TIME_INTERVAL:
                        self._irrigation["au190"]["md_status"][zone]["count"] = 0
                        self._irrigation["au190"]["md_status"][zone]["time"] = datetime.datetime.now()

                    if self._irrigation["au190"]["md_status"][zone]["count"] == MD_MAX_COUNT - 1:  # Suspend Zone
                        self._attrs["au190"]["md_status"][zone] = 2
                        _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Md Zone%s suspended: [%s][%s]", zone, self._irrigation["au190"]["md_status"][zone]["time"], self._irrigation["au190"]["md_status"][zone]["count"])

                    self._irrigation["au190"]["md_status"][zone]["count"] = self._irrigation["au190"]["md_status"][zone]["count"] + 1
                    # _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> Md Zone%s [%s][%s]", zone, self._irrigation["au190"]["md_status"][zone]["time"], self._irrigation["au190"]["md_status"][zone]["count"])

                    await self._zone_on(self.md_ids[zone] - 1, md_on_time, True)

            self.myasync_write_ha_state()   #Show the sensor status on client even if disabled
        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    async def _md_update_scheduled_on(self):
        try:
            '''
               Update if running the Scheduled watering 
               
            '''
            if not self._irrigation["au190"]['scheduled_w_status']['on']:

                self._irrigation["au190"]['scheduled_w_status']['on'] = True

                # Calculate all zones duration
                idx = 0
                duration = 0
                for id in range(len(self._attrs["au190"]["enable_zone"])):
                    if self._attrs["au190"]["enable_zone"][id]:
                        duration += self._forceTimeLimit(self._attrs["au190"]["pulsetime"][id], 112, 112) - 100 # Convert to seconnds
                starttime = datetime.datetime.now() + datetime.timedelta(seconds=duration)

                fc_listener = async_track_time_change(self.hass, self._md_enable_Suspended, hour=starttime.hour, minute=starttime.minute, second=starttime.second)
                self._irrigation["au190"]['scheduled_w_status']['fc_listener'] = fc_listener

                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> Time to run [%s][%s]", self.entity_id, starttime)

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    async def _md_enable_Suspended(self, acction_time):
        try:
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", acction_time)

            self._irrigation["au190"]['scheduled_w_status']['on'] = False

            fc_listener = self._irrigation["au190"]['scheduled_w_status']['fc_listener']
            fc_listener()
            self._irrigation["au190"]['scheduled_w_status']['fc_listener'] = ""
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> Done [%s]", self.entity_id)

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    def _md_update_status(self, zone, data):
        try:
            '''
                Data can be 0,1,2
            '''
            if self._attrs["au190"]["md_status"][zone] < 2:

                if data.lower() in ['true', '1', 'yes', 'on']:
                    data = 1
                else:
                    data = 0
                self._attrs["au190"]["md_status"][zone] = data

            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s]", zone, data)

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))



    async def _waterLim_logic(self):
        try:
            '''
              WaterL
              waterLimTout = in secconds - min value 1 min

              1.  If enable_irrig_sys and irrig_sys_status enabled
              1.  If enabled enable_waterL and enable_protection and
              2.  If WaterL status changed
              3.  
            '''
            if (self._irrigation["au190"]['enable_irrig_sys'] and self._irrigation["au190"]['irrig_sys_status'] and
                self._attrs["au190"]["enable_waterL"] and self._attrs["au190"]["enable_protection"] and
                self._attrs["au190"]["waterLim"] != self._irrigation["au190"]["waterLim"]
            ):

                if self._attrs["au190"]["waterLim"] == WATER_LIMIT_ON:

                    # ---    Suspend the system and enable again after x min

                    # turn off the Motor
                    self.async_turn_off_all_zones(-1)  # Turn off all the zoens before disable

                    # turn off the Motor
                    await self._enable_Suspended(CONF_PAYLOAD_OFF)
                    self._attrs["au190"]["waterLimLogic"] = True

                    _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> ###1### WaterL_suspended [%s]", self._attrs["au190"])

                else:

                    await self._clear_WaterLFc()
                    duration = int(self._attrs["au190"]["waterLimTout"])

                    if duration < 60:
                        duration = 60

                    starttime = datetime.datetime.now() + datetime.timedelta(seconds=duration)

                    fc_listener = async_track_time_change(self.hass, self._enable_Suspended(CONF_PAYLOAD_ON), hour=starttime.hour, minute=starttime.minute, second=starttime.second)
                    self._irrigation["au190"]["WaterL_Fc"] = fc_listener

                    _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> ###0### WaterL_suspended [%s]", self._attrs["au190"])


                self._irrigation["au190"]["waterLim"] = self._attrs["au190"]["waterLim"]
            self.myasync_write_ha_state()   #Show the sensor status on client even if disabled
        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    async def _rainLim_logic(self):
        try:
            '''
              enable_rainL
              rainLimTout = in secconds - min value 

              1.  If enable_irrig_sys and irrig_sys_status enabled
              1.  If enabled enable_rainL and enable_protection and
              2.  
              3.  
            '''
            if (self._irrigation["au190"]['enable_irrig_sys'] and self._irrigation["au190"]['irrig_sys_status'] and
                    self._attrs["au190"]["enable_rainL"] and self._attrs["au190"]["enable_protection"]
            ):
                None


            self.myasync_write_ha_state()
        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    '''

    '''
    async def _clear_motorRunningToLFc(self):
        if self._irrigation["au190"]["motorRunningToL_Fc"] != "":
            fc_listener = self._irrigation["au190"]["motorRunningToL_Fc"]
            fc_listener()
            self._irrigation["au190"]["motorRunningToL_Fc"] = ""

    '''

    '''
    async def _clear_WaterLFc(self):
        if self._irrigation["au190"]["WaterL_Fc"] != "":
            fc_listener = self._irrigation["au190"]["WaterL_Fc"]
            fc_listener()
            self._irrigation["au190"]["WaterL_Fc"] = ""

    '''
    
    '''
    async def _check_md_times(self):

        if len(self._attrs["au190"]["md"]) == 0:
            return True
        else:

            for entry in self._attrs["au190"]["md"]:
                inputTime = datetime.datetime.now().strftime('%H:%M')
                #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", entry['start_time'], inputTime, entry['end_time'])
                ret = self._is_time_between(inputTime, entry['start_time'], entry['end_time'], '23:59')
                if ret:
                    return True
            return False

    '''

    '''
    async def _enable_Suspended(self, data):
        try:

            if (self._irrigation["au190"]['enable_irrig_sys'] and self._irrigation["au190"]['irrig_sys_status']):

                await self._enable_Motor(data)

                if data == CONF_PAYLOAD_ON:
                    self._attrs["au190"]["waterLimLogic"] = False

                await self._clear_WaterLFc()

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    '''
        Enable or disable the Motor
        
        data = CONF_PAYLOAD_ON
        data = CONF_PAYLOAD_OFF
    '''
    async def _enable_Motor(self, data):
        try:
            # turn on/off the Motor
            self._publish(self._irrigation["command_topics"][self.no_of_zones], self._config[data])
            #asyncio.run_coroutine_threadsafe(self._publish(self._irrigation["command_topics"][self.no_of_zones], self._config[data]), self.hass.loop)# .result()

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    '''
        data    - True or False
    '''
    async def _enable_irrigation_system1(self, data):

        if (self._irrigation["au190"]['enable_irrig_sys'] != data):

            self._attrs["au190"]['enable_irrig_sys'] = not self._attrs["au190"]['enable_irrig_sys']  # update oly after its confiremd form the Mosquitto broker
            self._irrigation["au190"]['disable_req'] = 1

            if data:

                await self._enable_Motor(CONF_PAYLOAD_ON)

            elif not data:

                # # Turn off all the zoens before disable
                self.async_turn_off_all_zones(-1)

                # turn off the Motor
                await self._enable_Motor(CONF_PAYLOAD_OFF)

    '''
    
    '''
    async def _enable_irrigation_system2(self, data):

        if (self._irrigation["au190"]['irrig_sys_status'] != data ):

            self._irrigation["au190"]['disable_req'] = 2

            if data:

                await self._enable_Motor(CONF_PAYLOAD_ON)

            elif not data:

                # # Turn off all the zoens before disable
                self.async_turn_off_all_zones(-1)

                # turn off the Motor
                await self._enable_Motor(CONF_PAYLOAD_OFF)
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "]--> ### Motor run too long !")


    async def _load_from_file(self):
        """Load data from a file or return None."""
        try:
            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s]", self.entity_id, self._filename)

            with open(self._filename) as fptr:
                jsonf = json.loads(fptr.read())
                self._attrs.update(jsonf)
                await self._setSchedulerTask()
            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", self.entity_id, self._filename, jsonf['au190'])

        except IOError as e:
            await self._setSchedulerTask()
            #_LOGGER.warning("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))
        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    '''
        data = {"time": json_obj["time"]}

    '''
    async def _save_to_file(self, data):
        """Create json and save it in a file."""

        #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", self.entity_id, self._filename, data)
        try:
            with open(self._filename, "w") as fptr:
                fptr.write(json.dumps({"au190": data}))

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    '''
        Check if a json object (o) has attribute (k)

    '''
    def my_hasattr(self, o, k):
        try:
            # log.info("my_hasattr________:[" + str(o) + "][" + str(k) + "]")
            t = o[k]
            # log.info("my_hasattr___x___:[" + str(o) + "][" + str(k) + "]")
            return True

        except Exception as e:
            return False


    '''
          Check if a json object (o) contains the first x character attribute (k) or if the object has a part of an attribute then return the attribute

          PulseTime1
          PulseTime2
          PulseTime3

        self.my_hasattr_Idx(pL_o, 'PulseTime')
    '''
    def my_hasattr_Idx(self, o, k):
        ret = False
        try:

            l = len(k)
            for key in o:
                # log.info('[' + key + ']=' + o[key])
                if key[:l] == k:
                    ret = key
                    # log.info('---x---[' + key + ']=' + o[key])

        except Exception as e:
            return False
        return ret


    '''
        Check if the list contains that element
    '''
    def isInList(self, list_elenet, topic):

        try:
            if topic in self._irrigation[list_elenet]:
               return self._irrigation[list_elenet].index(topic)

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

        return -1

    def myasync_write_ha_state(self):
        #_LOGGER.debug('--> myasync_write_ha_state:')
        FMT = '%Y-%m-%dT%H:%M:%S.%f'
        self._attrs["Time"] = datetime.datetime.now().strftime(FMT)
        #self.state = datetime.datetime.now().strftime(FMT)
        self.async_write_ha_state()

    def convToBool(self, data):
        try:
            return data.lower() in ['true', '1', 'yes', 'on']
        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    '''
        If time is between to times ?
        end_day = '23:59:59'
        end_day = '23:59'

        FMT = '%Y-%m-%dT%H:%M:%S.%f'
        
        x = _is_time_between('08:00:00', '07:00:00', '08:00:00', '23:59:59')
        x = _is_time_between('08:00:00', '21:00:00', '06:00:00', '23:59:59')
        x = _is_time_between('08:00:00', '02:00:00', '22:00:00', '23:59:59')
        x = _is_time_between('08:00:00', '22:00:00', '07:00:00', '23:59:59')
        x = _is_time_between('06:00:00', '22:00:00', '07:00:00', '23:59:59')

    '''

    def _is_time_between(self, inputTime, start, end, end_day):
        try:

            # _LOGGER.debug('--> _is_time_between[' + self.t + '][' + intime + '][' + start + '][' + end + ']')

            if start <= inputTime <= end:
                return True
            elif start > end:
                # end_day = '23:59:59'
                if start <= inputTime <= end_day:
                    return True
                elif inputTime <= end:
                    return True
            return False

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

        return False

    '''
        Return the duration in minutes
    '''
    def _time_duration(self, start_time, end_time):
        try:

            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s]", start_time, end_time)
            duration = end_time - start_time
            return int(duration.total_seconds() / 60)

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    '''
        Tasmota time 0 - infinite
        Force to 0,1 sec

        0 / OFF = disable use of PulseTime for Relay<x>
        1..111 = set PulseTime for Relay<x> in 0.1 second increments
        112..64900 = set PulseTime for Relay<x>, offset by 100, in 1 second increments. Add 100 to desired interval in seconds, e.g., PulseTime 113 = 13 seconds and PulseTime 460 = 6 minutes (i.e., 360 seconds)
        
        Sec - Tasmota Sec
        0   -   0,1
        1   -   10
        2   -   20
        .........
        11  -   110
        ------------
        12  -   112
        13  -   113
        ..........
    '''
    def _forceTimeLimit(self, value, min_value, limit):
        ret = 112 #12 sec
        try:
            if value < limit:
                ret = min_value
            else:
                ret = value
        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))
        return ret


