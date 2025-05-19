import functools
import voluptuous as vol
import sys
import logging
import datetime
import time
import json
import os
import asyncio
import pathlib
from homeassistant.helpers.event import async_track_time_change


from homeassistant.components import switch
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import (
    CONF_NAME,
    CONF_OPTIMISTIC,
    CONF_PAYLOAD_OFF,
    CONF_PAYLOAD_ON,
)
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType

from homeassistant.components.mqtt import (
    CONF_COMMAND_TOPIC,
    CONF_QOS,
    CONF_RETAIN,
    PLATFORMS,
    subscription,
)
from homeassistant.components import mqtt
from homeassistant.components.mqtt.debug_info import log_messages
from homeassistant.components.mqtt.mixins import (
    MQTT_ENTITY_COMMON_SCHEMA,
    MqttEntity,
    async_setup_entry_helper,
)

MQTT_SWITCH_ATTRIBUTES_BLOCKED = frozenset(
    {
        switch.ATTR_CURRENT_POWER_W,
        switch.ATTR_TODAY_ENERGY_KWH,
    }
)

from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
)

_LOGGER = logging.getLogger(__name__)
from . import DOMAIN, SERVICE_AU190


JSON_FILE = "_data.json"
JSON_DIR = "au190"

DEFAULT_NAME = "au190 MQTT irrigation"
DEFAULT_PAYLOAD_ON = "ON"
DEFAULT_PAYLOAD_OFF = "OFF"
DEFAULT_OPTIMISTIC = False
CONF_STATE_ON = "state_on"
CONF_STATE_OFF = "state_off"

CONF_Z_CMND = "z_cmnd"
CONF_Z_STAT = "z_stat"

CONF_M_CMND = "m_cmnd"
CONF_M_STAT = "m_stat"
CONF_M_TEMPLATE = "m_template"

CONF_M_POWER_STAT = "m_power_stat"
CONF_M_POWER_TEMPLATE = "m_power_template"
CONF_M_POWER_DAILY_TEMPLATE = "m_powerdaily_template"
CONF_M_POWER_MONTHLY_TEMPLATE = "m_powermonthly_template"

CONF_MD_STAT = "md_stat"
CONF_MD_TEMPLATE = "md_template"
CONF_MD_ASSIGN = "md_assign"

CONF_WATERLIM_STAT = "waterLim_stat"
CONF_WATERLIM_TEMPLATE = "waterLim_template"

CONF_RAINLIM_STAT = "rainLim_stat"
CONF_RAINLIM_TEMPLATE = "rainLim_template"

CONF_PAYLOAD_AVAILABLE = "payload_available"
CONF_PAYLOAD_NOT_AVAILABLE = "payload_not_available"

DEFAULT_PAYLOAD_AVAILABLE = "Online"
DEFAULT_PAYLOAD_NOT_AVAILABLE = "Offline"

MAX_MD_SENSOR       = 6                         # Max, number of MD sensors that can be attached
MD_MAX_COUNT        = 10                        # Max, count the Md ON status in an interval of time
MD_TIME_INTERVAL    = 5                         # Count MD ON status in x min

MOTOR_RUNNING_ON    = True
WATER_LIMIT_ON      = True
RAIN_LIMIT_ON       = True
MD_ON               = True




PLATFORM_SCHEMA = mqtt.MQTT_RW_PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_COMMAND_TOPIC): "",
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_OPTIMISTIC, default=DEFAULT_OPTIMISTIC): cv.boolean,
        vol.Optional(CONF_PAYLOAD_OFF, default=DEFAULT_PAYLOAD_OFF): cv.string,
        vol.Optional(CONF_PAYLOAD_ON, default=DEFAULT_PAYLOAD_ON): cv.string,
        vol.Optional(CONF_STATE_OFF): cv.string,
        vol.Optional(CONF_STATE_ON): cv.string,

        vol.Required(CONF_Z_CMND, default=list): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(CONF_Z_STAT, default=list): vol.All(cv.ensure_list, [cv.string]),

        vol.Optional(CONF_MD_STAT, default=list): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_MD_TEMPLATE, default=list): vol.All(cv.ensure_list, [cv.template]),
        vol.Optional(CONF_MD_ASSIGN, default=list): vol.All(cv.ensure_list, [cv.string]),

        vol.Optional(CONF_M_CMND): cv.string,
        vol.Optional(CONF_M_STAT): cv.string,
        vol.Optional(CONF_M_TEMPLATE): cv.template,

        vol.Optional(CONF_M_POWER_STAT): cv.string,
        vol.Optional(CONF_M_POWER_TEMPLATE): cv.template,
        vol.Optional(CONF_M_POWER_DAILY_TEMPLATE): cv.template,
        vol.Optional(CONF_M_POWER_MONTHLY_TEMPLATE): cv.template,

        vol.Optional(CONF_WATERLIM_STAT): cv.string,
        vol.Optional(CONF_WATERLIM_TEMPLATE): cv.template,

        vol.Optional(CONF_RAINLIM_STAT): cv.string,
        vol.Optional(CONF_RAINLIM_TEMPLATE): cv.template,

        vol.Optional(CONF_PAYLOAD_AVAILABLE, default=DEFAULT_PAYLOAD_AVAILABLE): cv.string,
        vol.Optional(CONF_PAYLOAD_NOT_AVAILABLE, default=DEFAULT_PAYLOAD_NOT_AVAILABLE): cv.string,

    }
).extend(MQTT_ENTITY_COMMON_SCHEMA.schema)


async def async_setup_platform(hass: HomeAssistant, config: ConfigType, async_add_entities, discovery_info=None):
    """Set up MQTT switch through configuration.yaml."""
    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)
    await _async_setup_entity(hass, async_add_entities, config)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up MQTT switch dynamically through MQTT discovery."""
    setup = functools.partial(_async_setup_entity, hass, async_add_entities, config_entry=config_entry)
    await async_setup_entry_helper(hass, switch.DOMAIN, setup, PLATFORM_SCHEMA)


async def _async_setup_entity(hass, async_add_entities, config, config_entry=None, discovery_data=None):
    """Set up the MQTT switch."""

    devices = []
    devices.append(Au190_MqttIrrigation(hass, config, config_entry, discovery_data))
    async_add_entities(devices)

    # - register Services
    async def async_service_get_data(service_name, service_data):
        """Handle the service call."""
        try:
            kwargs = dict(service_data)
            entity_id = service_data.get("entity_id")

            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", service_name, entity_id, kwargs)

            for device in devices:
                if device.entity_id == entity_id:
                    _LOGGER.debug("[" + sys._getframe().f_code.co_name + "] [%s][%s][%s]", device.entity_id, entity_id, kwargs)
                    if service_name == SERVICE_AU190:
                        await device.async_au190(**kwargs)

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e) )

    async_dispatcher_connect(hass, DOMAIN, async_service_get_data)


class Au190_MqttIrrigation(MqttEntity, SwitchEntity, RestoreEntity):
    """Representation of a switch that can be toggled using MQTT."""

    _attributes_extra_blocked = MQTT_SWITCH_ATTRIBUTES_BLOCKED

    def __init__(self, hass, config, config_entry, discovery_data):
        """Initialize the MQTT switch."""
        self._state = False
        self.hass   = hass

        # au190
        self.z_cmnd = config.get(CONF_Z_CMND)
        self.z_stat = config.get(CONF_Z_STAT)

        self.m_cmnd = config.get(CONF_M_CMND)
        self.m_stat = config.get(CONF_M_STAT)

        self.md_stat = config.get(CONF_MD_STAT)
        self.md_template = config.get(CONF_MD_TEMPLATE)
        self.md_assign = config.get(CONF_MD_ASSIGN)
        self.no_of_md = 0

        self.no_of_zones = len(self.z_cmnd)
        self._filename = None

        self._attrs = {}            #Holds the Config data from client saved in the file
        self._irrigation = {}       #Holds local data

        MqttEntity.__init__(self, hass, config, config_entry, discovery_data)

    @staticmethod
    def config_schema():
        """Return the config schema."""
        return PLATFORM_SCHEMA

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def assumed_state(self):
        """Return true if we do optimistic updates."""
        return False

    # ---------------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------------

    def _publish(self, topic, payload):

        #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s]", topic, payload)
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

    async def _subscribe_topics(self):
        """(Re)Subscribe to topics."""

        await self._create_data()
        _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s [%s]", self.entity_id, self.name)

        my_dir = self.hass.config.path(JSON_DIR)
        self._filename = my_dir + os.sep + self.entity_id + JSON_FILE
        if not os.path.exists(my_dir):
            os.makedirs(my_dir)

        await self._load_from_file()

        topics = {}
        qos = self._config[CONF_QOS]

        def add_subscription(topics, topic, msg_callback):

            if self.my_hasattr(topics, topic):
                _LOGGER.fatal("[" + sys._getframe().f_code.co_name + "]--> [Yaml config is not good. This topic [%s] is aleardy assigned to a function. You have to use different topic for each sensor !]", topic)
                return False

            topics[topic] = {
                "topic": topic,
                "msg_callback": msg_callback,
                "qos": qos,
            }
            return True

        '''
            If no template return the original msg.payload
            if template exist - rerender

            template - must be from config !!!
        '''
        def render_template(msg, template):
            try:
                if template is not None:

                    template.hass = self.hass
                    payload = template.async_render_with_possible_json_value(msg.payload, "")
                else:
                    payload = msg.payload

                return payload
            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

        def state_message_md(msg, idx):
            """Handle new MQTT state messages."""
            try:
                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s] [%s]", idx, msg)

                t_template = self.md_template[idx]
                if t_template.template == "":
                    t_template = None

                data = render_template(msg, t_template)

                if data == DEFAULT_PAYLOAD_ON or data == DEFAULT_PAYLOAD_OFF:

                    if self._attrs["au190"]["md_status"][idx] != "error":
                        self._attrs["au190"]["md_status"][idx] = self.convToBool(data)
                        asyncio.run_coroutine_threadsafe(self._md_logic(idx), self.hass.loop)

                else:
                    _LOGGER.error("[" + sys._getframe().f_code.co_name + "]--> [msg: %s][Yaml config is not good. Template configuration [md_template: %s] not good !]", msg, self.md_template[idx])

            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

        @callback
        def state_message_md_0(msg):
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s] [%s]", 0, msg)
            state_message_md(msg, 0)

        @callback
        def state_message_md_1(msg):
            state_message_md(msg, 1)

        @callback
        def state_message_md_2(msg):
            state_message_md(msg, 2)

        @callback
        def state_message_md_3(msg):
            state_message_md(msg, 3)

        @callback
        def state_message_md_4(msg):
            state_message_md(msg, 4)

        @callback
        def state_message_md_5(msg):
            state_message_md(msg, 5)

        '''
            State topic POWER for zones

            stat/irrig_test/POWER1 = ON
        '''
        @callback
        def state_message_zone(msg):
            try:
                payload = msg.payload
                topic = msg.topic
                #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", topic, payload, msg)
                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)

                idx = self.getListIdx("state_topics", topic)  # stat/irrig/POWER1

                if idx >= 0 and idx < self.no_of_zones:  # On Off Zones

                    self._attrs["au190"]["status"][idx] = payload
                    self.myasync_write_ha_state()
                    #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]zone_%s [%s]", idx, self._attrs["au190"]["status"])

            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

        '''
           State topic PulseTime for zones

           stat/basic/RESULT = {"PulseTime1":{"Set":220,"Remaining":220}}

        '''
        @callback
        def state_message_pulsetime(msg):
            """Handle new MQTT state messages."""
            try:
                #payload = msg.payload
                topic = msg.topic
                pL_o = {}
                # _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", topic, payload, msg)

                if msg.payload[0] == "{":  # is json ?

                    pL_o = json.loads(msg.payload)  # decode json data
                    first_element = list(pL_o.keys())[0]
                    first_elementidx = topic + '/' + first_element

                    if self.getListIdx("state_pulse_times_idx", first_elementidx) >= 0:

                        _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)

                        idx = self.getListIdx("state_pulse_times_idx", first_elementidx)
                        self._irrigation["au190"]["pulsetime"][idx] = pL_o[first_element]["Set"]

                        '''
                            Send turn ON msg to the zone
                        '''
                        #self._publish(self._irrigation["command_on_topics"][idx], self._config[CONF_PAYLOAD_ON]) # Old ON
                        self._publish(self._irrigation["command_on_topics"][idx], self._irrigation["command_on_payload_topics"][idx])
                        self.myasync_write_ha_state()
                        # _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]-x- [%s][%s]", idx, payload)

            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

        '''
            Enable Disable the motor

        '''
        @callback
        def state_message_enable_motor(msg):
            """Handle new MQTT state messages."""
            try:
                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)

                data = render_template(msg, self._config.get(CONF_M_TEMPLATE))

                if data == DEFAULT_PAYLOAD_ON or data == DEFAULT_PAYLOAD_OFF:

                    if data == DEFAULT_PAYLOAD_ON:
                        self._attrs["au190"]['irrig_sys_status'] = 1
                    elif self._attrs["au190"]['irrig_sys_status'] == 1:
                        self._attrs["au190"]['irrig_sys_status'] = 0

                    asyncio.run_coroutine_threadsafe(self._irrigation_system(), self.hass.loop)
                else:
                    _LOGGER.error("[" + sys._getframe().f_code.co_name + "]--> [msg: %s][Yaml config is not good. Template configuration [%s: %s] not good !]", msg, CONF_M_TEMPLATE, self._config.get(CONF_M_TEMPLATE))

            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

        '''
            Motor ON or OFF
            If the motor is running I get that info form the motor current consumption.

            Accepting float or int values
        '''
        @callback
        def state_message_motor_power(msg):
            """Handle new MQTT state messages."""
            try:
                #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)

                data = render_template(msg, self._config.get(CONF_M_POWER_TEMPLATE))

                if self.is_number(data): # Must be number

                    data = float(data)
                    self._attrs["au190"]["P"] = data

                    if  data >= 100: # x WATT
                        self._attrs["au190"]["motorPower"] = True
                    else:
                        self._attrs["au190"]["motorPower"] = False

                    asyncio.run_coroutine_threadsafe(self._motorRunningToL_logic(), self.hass.loop)

                else:
                    _LOGGER.error("[" + sys._getframe().f_code.co_name + "]--> [msg: %s][Yaml config is not good. Template configuration [%s: %s] not good !]", msg, CONF_M_POWER_TEMPLATE, self._config.get(CONF_M_POWER_TEMPLATE))

                '''

                '''
                if self._config.get(CONF_M_POWER_DAILY_TEMPLATE) is not None:
                    data = render_template(msg, self._config.get(CONF_M_POWER_DAILY_TEMPLATE))

                    if self.is_number(data):  # Must be number

                        self._attrs["au190"]["PD"] = float(data)

                    else:
                        _LOGGER.error("[" + sys._getframe().f_code.co_name + "]--> [msg: %s][Yaml config is not good. Template configuration [%s: %s] not good !]", msg, CONF_M_POWER_DAILY_TEMPLATE, self._config.get(CONF_M_POWER_DAILY_TEMPLATE))

                '''

                '''
                if self._config.get(CONF_M_POWER_MONTHLY_TEMPLATE) is not None:
                    data = render_template(msg, self._config.get(CONF_M_POWER_MONTHLY_TEMPLATE))

                    if self.is_number(data):  # Must be number

                        self._attrs["au190"]["PM"] = float(data)

                    else:
                        _LOGGER.error("[" + sys._getframe().f_code.co_name + "]--> [msg: %s][Yaml config is not good. Template configuration [%s: %s] not good !]", msg, CONF_M_POWER_MONTHLY_TEMPLATE, self._config.get(CONF_M_POWER_MONTHLY_TEMPLATE))

            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

        @callback
        def state_message_waterLim(msg):
            """Handle new MQTT state messages."""
            try:
                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)

                data = render_template(msg, self._config.get(CONF_WATERLIM_TEMPLATE))

                if data == DEFAULT_PAYLOAD_ON or data == DEFAULT_PAYLOAD_OFF:
                    self._attrs["au190"]["waterLim"] = self.convToBool(data)
                    asyncio.run_coroutine_threadsafe(self._waterLim_logic(), self.hass.loop)
                else:
                    _LOGGER.error("[" + sys._getframe().f_code.co_name + "]--> [msg: %s][Yaml config is not good. Template configuration [%s: %s] not good !]", msg, CONF_WATERLIM_TEMPLATE, self._config.get(CONF_WATERLIM_TEMPLATE))

            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


        @callback
        def state_message_rainLim(msg):
            """Handle new MQTT state messages."""
            try:
                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)

                data = render_template(msg, self._config.get(CONF_RAINLIM_TEMPLATE))

                if data == DEFAULT_PAYLOAD_ON or data == DEFAULT_PAYLOAD_OFF:
                    self._attrs["au190"]["rainLim"] = self.convToBool(data)
                    asyncio.run_coroutine_threadsafe(self._rainLim_logic(), self.hass.loop)
                else:
                    _LOGGER.error("[" + sys._getframe().f_code.co_name + "]--> [msg: %s][Yaml config is not good. Template configuration [%s: %s] not good !]", msg, CONF_RAINLIM_TEMPLATE, self._config.get(CONF_RAINLIM_TEMPLATE))

            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


        @callback
        def state_message_info(msg):
            """Handle new MQTT state messages."""
            '''
            12:53:44 MQT: stat/basic/STATUS = {"Status":{"Module":1,"FriendlyName":["Basic"],"Topic":"basic","ButtonTopic":"0","Power":0,"PowerOnState":0,"LedState":1,"LedMask":"FFFF","SaveData":1,"SaveState":1,"SwitchTopic":"0","SwitchMode":[1,0,0,0,0,0,0,0],"ButtonRetain":0,"SwitchRetain":0,"SensorRetain":0,"PowerRetain":0}}
            12:53:44 MQT: stat/basic/STATUS1 = {"StatusPRM":{"Baudrate":115200,"GroupTopic":"tasmotas","OtaUrl":"http://thehackbox.org/tasmota/release/tasmota.bin","RestartReason":"Power on","Uptime":"0T03:18:43","StartupUTC":"2021-05-03T08:35:01","Sleep":50,"CfgHolder":4621,"BootCount":12,"SaveCount":324,"SaveAddress":"F8000"}}
            12:53:44 MQT: stat/basic/STATUS2 = {"StatusFWR":{"Version":"7.2.0(tasmota)","BuildDateTime":"2020-02-10T18:26:43","Boot":31,"Core":"2_6_1","SDK":"2.2.2-dev(5ab15d1)","Hardware":"ESP8266EX","CR":"273/1151"}}
            12:53:45 MQT: stat/basic/STATUS3 = {"StatusLOG":{"SerialLog":2,"WebLog":2,"MqttLog":0,"SysLog":0,"LogHost":"","LogPort":514,"SSId":["Roby",""],"TelePeriod":300,"Resolution":"558180C0","SetOption":["0000A009","2805C8000100060000005A00000000000000","00008000","00000000"]}}
            12:53:45 MQT: stat/basic/STATUS4 = {"StatusMEM":{"ProgramSize":594,"Free":344,"Heap":23,"ProgramFlashSize":1024,"FlashSize":1024,"FlashChipId":"14405E","FlashMode":3,"Features":["00000809","8FDAE397","003683A0","22B617CD","01001BC0","00007881"],"Drivers":"1,2,3,4,5,6,7,8,9,10,12,16,18,19,20,21,22,24,26,29","Sensors":"1,2,3,4,5,6,7,8,9,10,14,15,17,18,20,22,26,34"}}
            12:53:45 MQT: stat/basic/STATUS5 = {"StatusNET":{"Hostname":"basic-5911","IPAddress":"192.168.2.45","Gateway":"192.168.2.1","Subnetmask":"255.255.255.0","DNSServer":"192.168.2.190","Mac":"B4:E6:2D:3A:B7:17","Webserver":2,"WifiConfig":4}}
            12:53:45 MQT: stat/basic/STATUS6 = {"StatusMQT":{"MqttHost":"192.168.2.190","MqttPort":1883,"MqttClientMask":"Basic","MqttClient":"Basic","MqttUser":"au190","MqttCount":1,"MAX_PACKET_SIZE":1000,"KEEPALIVE":30}}
            12:53:45 MQT: stat/basic/STATUS7 = {"StatusTIM":{"UTC":"Mon May 03 11:53:45 2021","Local":"Mon May 03 12:53:45 2021","StartDST":"Sun Mar 28 02:00:00 2021","EndDST":"Sun Oct 31 03:00:00 2021","Timezone":"+01:00","Sunrise":"05:25","Sunset":"20:08"}}
            12:53:45 MQT: stat/basic/STATUS10 = {"StatusSNS":{"Time":"2021-05-03T12:53:45"}}
            12:53:45 MQT: stat/basic/STATUS11 = {"StatusSTS":{"Time":"2021-05-03T12:53:45","Uptime":"0T03:18:44","UptimeSec":11924,"Heap":24,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":1,"POWER":"OFF","Wifi":{"AP":1,"SSId":"Roby","BSSId":"84:16:F9:D3:3C:80","Channel":2,"RSSI":64,"Signal":-68,"LinkCount":1,"Downtime":"0T00:00:06"}}}

            12:55:13 MQT: tele/basic/STATE = {"Time":"2021-05-03T12:55:13","Uptime":"0T03:20:12","UptimeSec":12012,"Heap":24,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":1,"POWER":"OFF","Wifi":{"AP":1,"SSId":"Roby","BSSId":"84:16:F9:D3:3C:80","Channel":2,"RSSI":60,"Signal":-70,"LinkCount":1,"Downtime":"0T00:00:06"}}

            # My special hardware
            15:54:21 --> {"topic":"stat/x1/STATUS0","Time":"2021-09-26T15:54:22","Uptime":"00T00:00:19","SSId":"Roby","Ip":"192.168.2.155","RSSI":66}

            '''
            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)
            try:
                if msg.payload[0] == "{":
                    pL_o = json.loads(msg.payload)  # decode json data

                    if self.my_hasattr_Idx(pL_o, 'StatusNET'):

                        t_topic = self.conv_power_to_pulseTime(3, msg.topic)
                        self._attrs['i'][t_topic].update({'IpAddress': pL_o['StatusNET']['IPAddress']})

                    elif self.my_hasattr_Idx(pL_o, 'StatusSTS'):

                        t_topic = self.conv_power_to_pulseTime(3, msg.topic)
                        self._attrs['i'][t_topic].update({'SSId': pL_o['StatusSTS']['Wifi']['SSId'] + " (" + str(pL_o['StatusSTS']['Wifi']['RSSI']) + "%)"})
                        self._attrs['i'][t_topic].update({'Uptime': pL_o['StatusSTS']['Uptime']})
                        self._attrs['i'][t_topic].update({'Time': pL_o['StatusSTS']['Time']})

                    elif self.my_hasattr_Idx(pL_o, 'Wifi'):

                        t_topic = self.conv_power_to_pulseTime(3, msg.topic)
                        self._attrs['i'][t_topic].update({'SSId': pL_o['Wifi']['SSId'] + " (" + str(pL_o['Wifi']['RSSI']) + "%)"})
                        self._attrs['i'][t_topic].update({'Uptime': pL_o['Uptime']})
                        self._attrs['i'][t_topic].update({'Time': pL_o['Time']})

                    elif self.my_hasattr_Idx(pL_o, 'Ip'):# My special hardware

                        t_topic = self.conv_power_to_pulseTime(3, msg.topic)
                        self._attrs['i'][t_topic].update({'IpAddress': pL_o['Ip']})
                        self._attrs['i'][t_topic].update({'SSId': pL_o['SSId'] + " (" + str(pL_o['RSSI']) + "%)"})
                        self._attrs['i'][t_topic].update({'Uptime': pL_o['Uptime']})
                        self._attrs['i'][t_topic].update({'Time': pL_o['Time']})


                    self.myasync_write_ha_state()

            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


        @callback
        def state_message_available(msg):
            '''
                tele/basic/LWT = Online (retained)
            '''
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)
            try:

                if msg.payload == self._config[CONF_PAYLOAD_AVAILABLE]:
                    t_topic = self.conv_power_to_pulseTime(3, msg.topic)
                    self._attrs['i'][t_topic].update({'available': True})
                elif msg.payload == self._config[CONF_PAYLOAD_NOT_AVAILABLE]:
                    t_topic = self.conv_power_to_pulseTime(3, msg.topic)
                    self._attrs['i'][t_topic].update({'available': False})


                self._attrs['_state'] = True #State of the Irrigation
                for item in self._attrs['i']:
                    #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "] [%s][%s]", item, self._attrs['i'][item]['available'])

                    if self.my_hasattr_Idx(self._attrs['i'][item], 'available'):
                        if not self._attrs['i'][item]['available']:
                            self._attrs['_state'] = False

                            t_topic = item
                            self._attrs['i'][t_topic].update({'IpAddress': 'Unavailable'})
                            self._attrs['i'][t_topic].update({'SSId': 'Unavailable'})
                            self._attrs['i'][t_topic].update({'Uptime': 'Unavailable'})
                            self._attrs['i'][t_topic].update({'Time': 'Unavailable'})


                self.myasync_write_ha_state()

            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))





        '''
        --------------------------------------------------------------------------------------------------------------------------------------

            Set listeners

            Cannot use the same topic for multiple functions !!!

        --------------------------------------------------------------------------------------------------------------------------------------
        '''

        for item in self._irrigation["state_topics"]:
            if not add_subscription(topics, item, state_message_zone):
                return False

        for item in self._irrigation["state_pulse_times"]:
            if not add_subscription(topics, item, state_message_pulsetime):
                return False

        for idx in range(self.no_of_md):
            item = self.md_stat[idx]
            fc = eval("state_message_md_"+ str(idx))
            if not add_subscription(topics, item, fc):
                return False

        if self.m_stat is not None:
            if not add_subscription(topics, self.m_stat, state_message_enable_motor):
                return False

        if self._config.get(CONF_M_POWER_STAT) is not None:
            if not add_subscription(topics, self._config.get(CONF_M_POWER_STAT), state_message_motor_power):
                return False


        if self._config.get(CONF_WATERLIM_STAT) is not None:
            if not add_subscription(topics, self._config.get(CONF_WATERLIM_STAT), state_message_waterLim):
                return False

        if self._config.get(CONF_RAINLIM_STAT) is not None:
            if not add_subscription(topics, self._config.get(CONF_RAINLIM_STAT), state_message_rainLim):
                return False


        for item in self._irrigation["state_info"]:
            add_subscription(topics, item, state_message_info)


        for item in self._irrigation["state_available"]:
            add_subscription(topics, item, state_message_available)



        self._sub_state = await subscription.async_subscribe_topics(self.hass, self._sub_state, topics)

        '''
            Init data

            1.  Do not turn off the System (PulseTime = 0)
            2.  Get the System actual status
            3.  Get the IP of the Tasmota devices

        '''
        if self.m_stat is not None:
            tmsg = self.conv_power_to_pulseTime(2, self.m_cmnd)
            self._publish(tmsg, 0)              #Send the pulsetime = 0, allways on
            self._publish(self.m_cmnd, "")      #Get the status

        for item in self._irrigation["command_info"]:
            self._publish(item, 0)

        return True


    '''


    '''
    async def _create_data(self):
        try:

            if (self.no_of_zones != len(self.z_stat) or self.no_of_zones <= 0):
                _LOGGER.fatal("[" + sys._getframe().f_code.co_name + "]--> [Yaml config is not good. Please define the CONF_Z_CMND and CONF_Z_STAT, elements of CONF_Z_CMND and CONF_Z_STAT must be equal!]")
                return False

            self.no_of_md = len(self.md_stat)
            if (self.no_of_md > MAX_MD_SENSOR):
                _LOGGER.fatal("[" + sys._getframe().f_code.co_name + "]--> [Yaml config is not good. Too many Md sensor]")
                self.no_of_md = MAX_MD_SENSOR

            if self.no_of_md != len(self.md_template):
                _LOGGER.fatal("[" + sys._getframe().f_code.co_name + "]--> [Yaml config is not good. If you are using Md sensors(md_stat) you must define Md temaplate(md_template) and must has equal number of elements]")
                return False

            if self.no_of_md != len(self.md_assign):
                _LOGGER.fatal("[" + sys._getframe().f_code.co_name + "]--> [Yaml config is not good. Values in *md_assign* assignments have to be equal number of elements in *md_stat*! The number in this array, maps Md number to Zone index. Rerender mtion detection inputs to zone (values in *md_assign* assignments have to be equal elements as in *md_stat*). The first number represents the Md1 activates that number of Zone.]")
                return False

            for idx in range(self.no_of_md):
                if self.no_of_zones <= int(self.md_assign[idx]):
                    _LOGGER.fatal("[" + sys._getframe().f_code.co_name + "]--> [Yaml config is not good. Assignments *md_assign* values [%s] has to be lower then number the of zones. Number of zones in this case starts form 0. Ex: if you have 3 Zone: md_assign: [2,1,0]", self.md_assign[idx])
                    return False

            self._attrs.update({'i': {}})                                           # For info

            command_on_list = []
            command_on_payload_list = []
            command_off_list = []
            command_pulseTime_list = []

            state_list = []
            state_pulseTime_list = []
            state_pulseTime_list_idx = []

            command_info_list = []
            state_info_list = []

            state_available_list = []

            attr_status_list = []
            attr_enable_zone_list = []
            attr_pulsetime_list = []

            for idx in range(self.no_of_zones):

                z_cmnd = self.z_cmnd[idx].split(" ")        # cmnd/irrig/PWMIR5 50
                if len(z_cmnd) != 2:
                    _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Command not good: " + str(self.z_cmnd[idx]))

                command_on_list.append(z_cmnd[0])           # cmnd/irrig/PWMIR5
                command_on_payload_list.append(z_cmnd[1])   # 50

                cmnd_pulseTime = z_cmnd[0].replace("PWMIR", "PulseTime")  # cmnd/irrig/PulseTime5
                command_pulseTime_list.append(cmnd_pulseTime)

                cmnd_off = z_cmnd[0].replace("PWMIR", "POWER")            # cmnd/irrig/POWER5
                command_off_list.append(cmnd_off)

                state_list.append(self.z_stat[idx])

                '''
                    PulseTime payload message

                    Calculate events msg for PulseTime  -> stat/basic/RESULT = {"PulseTime1":{"Set":220,"Remaining":220}}
                    Calculate events msg for Info       -> tele/irrig_test/STATE
                '''
                state_pulseTime = self.conv_power_to_pulseTime(1, self.z_stat[idx])
                state_pulseTime_list_idx.append(state_pulseTime)            # Need to get the correct idx form the pulsetime event

                '''
                    Stat PulseTime event message.
                '''
                state_pulseTime = self.z_stat[idx]
                tidx = state_pulseTime.rfind("/")
                state_pulseTime = state_pulseTime[0:tidx] + '/RESULT'
                if state_pulseTime not in state_pulseTime_list:
                    state_pulseTime_list.append(state_pulseTime)            # For state pulseTime we need -> stat/basic/RESULT = {"PulseTime1":{"Set":220,"Remaining":220}}

                '''
                    command_info: "cmnd/basic/Status"
                '''
                command_info = state_pulseTime.replace("RESULT", "Status")
                command_info = command_info.replace("stat", "cmnd")
                if command_info not in command_info_list:
                    command_info_list.append(command_info)

                '''
                    Stat Info event message.

                    state_info: 'stat/basic/STATUS5'
                    state_info: 'stat/basic/STATUS11'

                    state_info: tele/basic/STATE
                '''
                state_info = command_info.replace("cmnd", "stat")
                state_info = state_info.replace("Status", "STATUS0") # My special hardware
                if state_info not in state_info_list:
                    state_info_list.append(state_info)

                state_info = state_info.replace("STATUS0", "STATUS5")
                if state_info not in state_info_list:
                    state_info_list.append(state_info)

                state_info = state_info.replace("STATUS5", "STATUS11")
                if state_info not in state_info_list:
                    state_info_list.append(state_info)

                state_info = state_info.replace("stat", "tele")
                state_info = state_info.replace("STATUS11", "STATE")
                if state_info not in state_info_list:
                    state_info_list.append(state_info)


                '''
                   Stat Info data
                '''
                t_topic = self.conv_power_to_pulseTime(3, state_info)
                self._attrs['i'].update({t_topic: {}})

                '''
                    Stat available event message.

                    tele/basic/LWT
                '''
                state_info = 'tele/' + t_topic + '/LWT'
                if state_info not in state_available_list:
                    state_available_list.append(state_info)


                # Attr config
                attr_status_list.append(DEFAULT_PAYLOAD_OFF)
                attr_enable_zone_list.append(False)
                attr_pulsetime_list.append(-1) # Force to update at the first time
                #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s] [%s][%s]", idx, self.z_cmnd[idx], self.z_stat[idx])


            self._irrigation.update({"command_on_topics": command_on_list})
            self._irrigation.update({"command_on_payload_topics": command_on_payload_list})
            self._irrigation.update({"command_off_topics": command_off_list})
            self._irrigation.update({"command_pulse_times": command_pulseTime_list})
            self._irrigation.update({"command_motor": self.m_cmnd})
            self._irrigation.update({"command_info": command_info_list})                    # Calculate events msg for info.
            self._irrigation.update({"state_topics": state_list})                           # to check if the input topic is correct
            self._irrigation.update({"state_pulse_times": state_pulseTime_list})            # Calculate events msg subscribe for.
            self._irrigation.update({"state_pulse_times_idx": state_pulseTime_list_idx})    # Calculate events msg. Need to get the correct idx form the pulsetime event
            self._irrigation.update({"state_info": state_info_list})                        # Calculate events msg for info.
            self._irrigation.update({"state_available": state_available_list})              # Calculate events msg for info.


            self._irrigation.update({"au190": {}})                                  # Only those vaules where I need former value

            self._irrigation["au190"]['irrig_sys_status'] = 1                       # 0 off, 1 On, 2 err motor running too long, 3 - waterLim suspended

            self._irrigation["au190"].update({"pulsetime": attr_pulsetime_list})    # Pulstime from the device, this value is already set and confirmed


            self._irrigation["au190"]["enable_md"]  = False
            self._irrigation["au190"]["md_status"] = []
            for idx in range(self.no_of_md):
                self._irrigation["au190"]["md_status"].append({"count": 0, "time": datetime.datetime.now()})                # Count the Md ON status in an interval of time

            self._irrigation["au190"]["enable_protection"] = False
            self._irrigation["au190"]["enable_motorRunningToL"] = False
            self._irrigation["au190"]["enable_waterL"] = False
            self._irrigation["au190"]["enable_rainL"] = False


            self._irrigation["au190"]["motorPower"] = False
            self._irrigation["au190"]['scheduled_w_status'] = {"on": False, "fc_listener": ""}               #sche_w_status Scheduled watering status

            self._irrigation["au190"]["waterLim"] = False

            self._irrigation["au190"]["scheduler_Fc"] = []                          #Holds the function list and the callback data
            self._irrigation["au190"]["WaterL_Fc"] = ""                             #List of callback Fc if != "" suspended WaterLim
            self._irrigation["au190"]["RainL_Fc"] = ""                              #Holds the function list and the callback data
            self._irrigation["au190"]["motorRunningToL_Fc"] = ""                    #Holds the function list and the callback data



            # Attr config - #Holds the Config data from client, and saved in the file

            self._attrs.update({"au190": {}})
            self._attrs["au190"]['irrig_sys_status'] = 1                            # 0 off, 1 On, 2 err motor running too long, 3 - waterLim suspended

            self._attrs["au190"].update({"status": attr_status_list})               # zone staus
            self._attrs["au190"].update({"enable_zone": attr_enable_zone_list})     # zone enable
            self._attrs["au190"].update({"pulsetime": attr_pulsetime_list})         # zone pulsetime

            self._attrs["au190"].update({"enable_scheduler": False})
            self._attrs["au190"].update({"scheduler": []})
            self._attrs["au190"]["irrigdays"] = [True,True,True,True,True,True,True]#Irrigation days

            self._attrs["au190"]["waterLim"] = False
            self._attrs["au190"]["waterLimLogic"] = False                           #After the sensor is on there is a timeout, it shows the logical value, not the real sensor value
            self._attrs["au190"]["rainLim"] = False
            self._attrs["au190"]["rainLimLogic"] = False                            #After the sensor is on there is a timeout, it shows the logical value, not the real sensor value
            self._attrs["au190"]["motorPower"] = False

            self._attrs["au190"]["P"] = 0
            self._attrs["au190"]["PD"] = 0
            self._attrs["au190"]["PW"] = 0
            self._attrs["au190"]["PM"] = 0
            self._attrs["au190"]["PY"] = 0

            self._attrs["au190"]["enable_md"] = False
            self._attrs["au190"]["md"] = []                                 #List contains the Start and End time
            self._attrs["au190"]["md_on_time"] = 100                        #If Md activated this irrigation will be on this amount of time in Esp special secconds - min value 10 sec max vaule is 10 min

            self._attrs["au190"]["md_status"] = []
            for idx in range(self.no_of_md):
                self._attrs["au190"]["md_status"].append(False)             # 0-OFF 1-ON 2-Suspended

            self._attrs["au190"]["enable_protection"] = False

            self._attrs["au190"]["enable_waterL"] = False
            self._attrs["au190"]["waterLimTout"] = 60                       #After watrer limit reached, how long suspend the motor (system) in secconds - min value 1 min

            self._attrs["au190"]["enable_rainL"] = False
            self._attrs["au190"]["rainLimTout"] = 60                        # If rany rany do not watering this time in sec

            self._attrs["au190"]["enable_motorRunningToL"] = False
            self._attrs["au190"]["motorRunningTout"] = 600                  #If the motor running to long in secconds - min value 1 min

            return True

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))
            return False

    '''
    '''
    @property
    def state_attributes(self):
        """Return the optional state attributes."""
        #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s", self._attrs)
        return self._attrs

    async def async_turn_on(self, **kwargs):
        None

    '''
        Turn on the Irrigation zone - min turn on is 10 sec

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

            if(self._irrigation["au190"]['irrig_sys_status'] != 1 or self._attrs["au190"]["waterLimLogic"] ): #
                return

            idx = int(kwargs["zone"])
            allways_on = False
            if 'allways_on' in kwargs:
                allways_on = kwargs["allways_on"]
                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> allways_on [%s]", allways_on)


            if self._attrs["au190"]["status"][idx] == self._config[CONF_PAYLOAD_OFF] or allways_on:

                self.async_turn_off_all_zones(idx)

                if kwargs["pulsetime"] >= 0:  # comming form Md
                    running_time = kwargs["pulsetime"]
                else:
                    running_time = self._attrs["au190"]["pulsetime"][idx]

                pulseTime = self._forceTimeLimit(running_time, 100)
                self._publish(self._irrigation["command_pulse_times"][idx], pulseTime) # I want to send always the PulseTime
                '''
                if (self._irrigation["au190"]["pulsetime"][idx] != pulseTime):

                    self._publish(self._irrigation["command_pulse_times"][idx], pulseTime)

                else:
                    #Just turn ON
                    self._publish(self._irrigation["command_on_topics"][idx], self._config[CONF_PAYLOAD_ON])
                '''
            else:
                # Just turn OFF
                self._publish(self._irrigation["command_off_topics"][idx], self._config[CONF_PAYLOAD_OFF])

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    '''
        Optimistic mode
    '''
    def async_turn_off_all_zones(self, zone_idx):
        #was_on = False
        idx = 0
        for zone_id in self._attrs["au190"]["status"]:
            if zone_id != self._config[CONF_PAYLOAD_OFF] and idx != zone_idx:
                #was_on = True
                self._publish(self._irrigation["command_off_topics"][idx], self._config[CONF_PAYLOAD_OFF])
                #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s]", idx, id)
            idx = idx + 1

        #if was_on: #time delay between on and off
            #await asyncio.sleep(0.5) #second

    '''
        allways_on - If true, allways turn ON the zone (output)
    '''
    async def _zone_on(self, idx, pulsetime = -1, allways_on = False):
        _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", idx, pulsetime, allways_on)

        kwargs = {}
        kwargs['zone'] = idx
        kwargs['pulsetime'] = pulsetime
        kwargs['allways_on'] = allways_on

        await self.async_my_turn_on(**kwargs)

    async def _scheduler_wake_up(self, acction_time):
        try:
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", acction_time)

            id = None
            for entry in self._irrigation["au190"]["scheduler_Fc"]:

                start_time = entry['start_time']

                if start_time.hour == acction_time.hour and start_time.minute == acction_time.minute and start_time.second == acction_time.second:
                    id = entry['id']
                    break

            if id != None:
                '''

                  Automatic irrigation

                  1.  If irrig_sys_status enabled
                  1.  If spesific weekday and
                  2.  If WaterL ok and
                  3.  If RainL ok

                '''
                if (self._irrigation["au190"]['irrig_sys_status'] == 1 and
                    self._attrs["au190"]["irrigdays"][datetime.datetime.now().weekday()] and
                    self._irrigation["au190"]["waterLim"] != WATER_LIMIT_ON and
                    self._attrs["au190"]["rainLimLogic"] != RAIN_LIMIT_ON
                ):
                    await self._md_update_scheduled_on()
                    await self._zone_on(id)

            else:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: Invalid Time: [%s]", acction_time)

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    '''

        Automatic irrigation scheduler

    '''
    async def _setSchedulerTask(self):
        try:
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", self._attrs["au190"]['enable_scheduler'])

            # --- Remove all scheduler listener
            for entry in self._irrigation["au190"]["scheduler_Fc"]:
                #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]-- [%s]", fc_listener)
                fc_listener = entry["fc_listener"]
                fc_listener()
            self._irrigation["au190"]["scheduler_Fc"] = []

            #--- Set scheduler for zones
            FMT = '%H:%M:%S'

            if self._attrs["au190"]['enable_scheduler']:
                for start_time in self._attrs["au190"]['scheduler']:

                    start_time = start_time + ":00"
                    #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", start_time)

                    idx = 0
                    for id in range(len(self._attrs["au190"]["enable_zone"])):

                        if self._attrs["au190"]["enable_zone"][id]:

                            if idx == 0:
                                previous_run = 0
                                idx = + 1
                                starttime = datetime.datetime.strptime(start_time, FMT)  # delay x sec between zonees
                                #start_time = starttime.strftime(FMT)
                            else:
                                previous_run = self._forceTimeLimit(self._attrs["au190"]["pulsetime"][previous_id], 111) - 100      # Convert to seconnds
                                starttime = starttime + datetime.timedelta(seconds=previous_run) + datetime.timedelta(seconds=1)    # delay x sec between zonees


                            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "] - [Zone%s][%s][%s:%s:%s]", (id), previous_run, starttime.hour, starttime.minute, starttime.second)
                            fc_listener = async_track_time_change(self.hass, self._scheduler_wake_up, hour=starttime.hour, minute=starttime.minute, second=starttime.second)
                            self._irrigation["au190"]["scheduler_Fc"].append({"start_time": starttime, "id": id, "fc_listener": fc_listener})

                            previous_id = id

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    async def _motorRunningToL_logic(self):
        try:
            '''
                motorRunningToLong
                motorRunningTout = in secconds - min value 1 min

                1.  If irrig_sys_status enabled 1 or 3
                2.  If enabled enable_motorRunningToL and enable_protection and
                3.  If Motor status changed
                4.
            '''
            if ( (self._irrigation["au190"]['irrig_sys_status'] == 1 or self._irrigation["au190"]['irrig_sys_status'] == 3 ) and
                self._attrs["au190"]["enable_motorRunningToL"] and self._attrs["au190"]["enable_protection"] and
                self._attrs["au190"]["motorPower"] != self._irrigation["au190"]["motorPower"]
            ):

                if self._attrs["au190"]["motorPower"] == MOTOR_RUNNING_ON:

                    # ---    Add time out for Motor

                    duration = int(self._attrs["au190"]["motorRunningTout"])

                    if duration < 60:
                        duration = 60

                    starttime = datetime.datetime.now() + datetime.timedelta(seconds=duration)

                    fc_listener = async_track_time_change(self.hass, self._enable_irrigation_system_h, hour=starttime.hour, minute=starttime.minute, second=starttime.second)
                    self._irrigation["au190"]["motorRunningToL_Fc"] = fc_listener

                    _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> ##### MotorRunningToLong [%s][%s]", self._attrs["au190"], starttime)

                else:
                    await self._clear_motorRunningToLFc()
                    _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> #####*** MotorRunningToLong OK [%s]", self._attrs["au190"])


            self._irrigation["au190"]["motorPower"] = self._attrs["au190"]["motorPower"]
            self.myasync_write_ha_state()

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    async def _md_logic(self, zone):
        try:
            '''
              zone starts with index 0

              md_on_time = in Esp special secconds - min value 10 sec max vaule is 10 min

              1.  If irrig_sys_status enabled
              2.  If not suspended self._irrigation["au190"]["WaterL_Fc"] = ""
              3.  If enabled enable_md
              4.  If times between the set time
              5.  If no self._irrigation["au190"]['scheduled_w_status']['on'] If not running the Scheduled watering
              6.  Count the ON status in 10 min interval if the count is > x disable that Md on that zome

            '''
            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> Zone%s", zone)

            if (self._irrigation["au190"]['irrig_sys_status'] == 1 and
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
                        self._attrs["au190"]["md_status"][zone] = "error"
                        _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Md Zone%s suspended: [%s][%s]", zone, self._irrigation["au190"]["md_status"][zone]["time"], self._irrigation["au190"]["md_status"][zone]["count"])

                    self._irrigation["au190"]["md_status"][zone]["count"] = self._irrigation["au190"]["md_status"][zone]["count"] + 1
                    # _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> Md Zone%s [%s][%s]", zone, self._irrigation["au190"]["md_status"][zone]["time"], self._irrigation["au190"]["md_status"][zone]["count"])

                    await self._zone_on(self.md_assign[zone], md_on_time, True)

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
                #idx = 0
                duration = 0
                for id in range(len(self._attrs["au190"]["enable_zone"])):
                    if self._attrs["au190"]["enable_zone"][id]:
                        duration += self._forceTimeLimit(self._attrs["au190"]["pulsetime"][id], 100) - 100 # Convert to seconnds
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

    '''
        Enable Disable the Motor == Enable Disable system
        Enable system is depends on this event - If this is not in use, not specified in config yaml we need to call the specific function.

        data = DEFAULT_PAYLOAD_ON
        data = DEFAULT_PAYLOAD_OFF
    '''
    async def _enable_Motor(self, data):
        try:
            if data == DEFAULT_PAYLOAD_ON or data == DEFAULT_PAYLOAD_OFF:
                # turn on/off the Motor
                if self._irrigation["command_motor"] != None:
                    self._publish(self._irrigation["command_motor"], data)
                else:
                    await self._irrigation_system()
            else:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "]--> [msg: %s][Yaml config is not good. Template configuration [%s: %s] not good !]", data, CONF_M_TEMPLATE, self._config.get(CONF_M_TEMPLATE))

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    '''
        Logic for ON|OFF of the Irrigation system

        Enable Disable the Motor == Enable Disable system

        Motor ON or OFF is just enable disable to run the motor.
        If the motor is running I get that info form the motor current consumption.

        self._attrs["au190"]['irrig_sys_status'] - the input value: 0 off, 1 On, 2 err motor running too long, 3 - waterLim suspended

    '''
    async def _irrigation_system(self):
        try:
            if self._irrigation["au190"]['irrig_sys_status'] == self._attrs["au190"]['irrig_sys_status'] : #Run only if different from previous
                return

            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s -> %s]", self._irrigation["au190"]['irrig_sys_status'], self._attrs["au190"]['irrig_sys_status'])

            self._irrigation["au190"]['irrig_sys_status'] = self._attrs["au190"]['irrig_sys_status']

            if self._attrs["au190"]['irrig_sys_status'] == 1:  # Manual turn ON, ok

                # --------------------------------------------------------------------------------------------------------------------------------------
                #   Manual enable, reset all vars to default
                #   Do not reset the attrs data that contains the sensor data - its automatically updated in every x min
                # --------------------------------------------------------------------------------------------------------------------------------------

                await self._clear_motorRunningToLFc()
                self._irrigation["au190"]["motorPower"] = False

                self._irrigation["au190"]["waterLim"] = False
                self._attrs["au190"]["waterLimLogic"] = False
                await self._clear_WaterL_Fc()

                self._attrs["au190"]["rainLimLogic"] = False
                await self._clear_RainL_Fc()

                await self._motorRunningToL_logic()
                await self._waterLim_logic()

                self._irrigation["au190"]["md_status"] = []
                self._attrs["au190"]["md_status"] = []
                for idx in range(self.no_of_md):
                    self._irrigation["au190"]["md_status"].append({"count": 0, "time": datetime.datetime.now()})  # Count the Md ON status in an interval of time
                    self._attrs["au190"]["md_status"].append(False)  # True False 2-Suspended


            #elif self._attrs["au190"]['irrig_sys_status'] == 0 or self._attrs["au190"]['irrig_sys_status'] == 2:  # manual turn off or error turn off

            self.myasync_write_ha_state()

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    async def _waterLim_logic(self):
        try:
            '''
              WaterL
              waterLimTout = in secconds - min value 1 min

              1.  If irrig_sys_status 1 or 3
              1.  If enabled enable_waterL and enable_protection and
              2.  If WaterL status changed
              3.
            '''
            if ( (self._irrigation["au190"]['irrig_sys_status'] == 1 or self._irrigation["au190"]['irrig_sys_status'] == 3) and
                self._attrs["au190"]["enable_waterL"] and self._attrs["au190"]["enable_protection"] and
                self._attrs["au190"]["waterLim"] != self._irrigation["au190"]["waterLim"]
            ):

                if self._attrs["au190"]["waterLim"] == WATER_LIMIT_ON:

                    # ---    Suspend the system and enable again after x min
                    await self._enable_irrigation_system(3)
                    await self._clear_WaterL_Fc()
                    self._attrs["au190"]["waterLimLogic"] = True

                    _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> ##### WaterL_suspended [%s]", self._attrs["au190"])

                else:

                    await self._clear_WaterL_Fc()
                    duration = int(self._attrs["au190"]["waterLimTout"])

                    if duration < 60:
                        duration = 60

                    starttime = datetime.datetime.now() + datetime.timedelta(seconds=duration)

                    fc_listener = async_track_time_change(self.hass, self._enable_SuspendedWaterLim, hour=starttime.hour, minute=starttime.minute, second=starttime.second)
                    self._irrigation["au190"]["WaterL_Fc"] = fc_listener

                self._irrigation["au190"]["waterLim"] = self._attrs["au190"]["waterLim"]

            self.myasync_write_ha_state()   #Show the sensor status on client even if disabled

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    async def _rainLim_logic(self):
        try:
            '''
              enable_rainL
              rainLimTout = in secconds - min value 10

              1.  If irrig_sys_status enabled
              1.  If enabled enable_rainL and enable_protection and
              2.
              3.
            '''
            if (self._irrigation["au190"]['irrig_sys_status'] == 1 and
                self._attrs["au190"]["enable_rainL"] and self._attrs["au190"]["enable_protection"]
            ):

                #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> rainLim [%s][%s]", self._attrs["au190"]["rainLim"], self._attrs["au190"]["rainLimLogic"])

                if(self._attrs["au190"]["rainLim"] == RAIN_LIMIT_ON):

                    await self._clear_RainL_Fc()
                    self._attrs["au190"]["rainLimLogic"] = self._attrs["au190"]["rainLim"]

                    _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> ##### RainLim_suspended [%s]", self._attrs["au190"])

                elif (self._attrs["au190"]["rainLim"] != RAIN_LIMIT_ON and self._attrs["au190"]["rainLimLogic"] != RAIN_LIMIT_ON): #Everithing is ok

                    None

                elif(self._attrs["au190"]["rainLimLogic"] == RAIN_LIMIT_ON): #RainLim is ok now - lets start the timer

                    await self._clear_RainL_Fc()

                    duration = int(self._attrs["au190"]["rainLimTout"])
                    if duration < 10:
                        duration = 10

                    starttime = datetime.datetime.now() + datetime.timedelta(seconds=duration)

                    fc_listener = async_track_time_change(self.hass, self._RainL_ok, hour=starttime.hour, minute=starttime.minute, second=starttime.second)
                    self._irrigation["au190"]["RainL_Fc"] = fc_listener

            self.myasync_write_ha_state()

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    '''

    '''
    async def _clear_motorRunningToLFc(self):
        try:
            if self._irrigation["au190"]["motorRunningToL_Fc"] != "":
                fc_listener = self._irrigation["au190"]["motorRunningToL_Fc"]
                fc_listener()
                self._irrigation["au190"]["motorRunningToL_Fc"] = ""

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    '''

    '''
    async def _clear_RainL_Fc(self):
        try:
            if self._irrigation["au190"]["RainL_Fc"] != "":
                fc_listener = self._irrigation["au190"]["RainL_Fc"]
                fc_listener()
                self._irrigation["au190"]["RainL_Fc"] = ""

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    async def _clear_WaterL_Fc(self):
        try:
            if self._irrigation["au190"]["WaterL_Fc"] != "":
                fc_listener = self._irrigation["au190"]["WaterL_Fc"]
                fc_listener()
                self._irrigation["au190"]["WaterL_Fc"] = ""

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

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

        data - ON

    '''
    async def _enable_SuspendedWaterLim(self, acction_time):
        try:
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", acction_time)

            if self._irrigation["au190"]['irrig_sys_status'] == 3:

                await self._enable_Motor(DEFAULT_PAYLOAD_ON)
                self._attrs["au190"]["waterLimLogic"] = False
                await self._clear_WaterL_Fc()

                _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> #####*** WaterL_suspended OK [%s]", self._attrs["au190"])

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    '''
        Enable/Disable Irrigation system

    '''
    async def _enable_irrigation_system_h(self, acction_time):
        await self._enable_irrigation_system(2)

    '''
    data    0   - Turn off Manual
            1   - Turn on Manual
            2   - Turn off Motor running too long
            3   - Turn off for while Water Lim
    '''
    async def _enable_irrigation_system(self, data):

        self._attrs["au190"]['irrig_sys_status'] = data

        if self._irrigation["au190"]['irrig_sys_status'] == self._attrs["au190"]['irrig_sys_status'] : #Run only if different from previous
            return

        if data == 1:
            await self._enable_Motor(DEFAULT_PAYLOAD_ON)
        else:
            # Turn off all the zoens before disable
            self.async_turn_off_all_zones(-1)

            # turn off the Motor
            await self._enable_Motor(DEFAULT_PAYLOAD_OFF)

            if data == 2:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "]--> ##### MotorRunningToLong - Motor running too long !")

    '''

    '''
    async def _RainL_ok(self, acction_time):
        try:

            self._attrs["au190"]["rainLimLogic"] = not RAIN_LIMIT_ON #RainL is ok
            self.myasync_write_ha_state()

            await self._clear_RainL_Fc()

            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> #####*** RainLim_suspended OK [%s]", self._attrs["au190"])

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    '''
        Load data form file or default data

    '''
    async def _load_from_file(self):
        """Load data from a file or return None."""
        try:
            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s]", self.entity_id, self._filename)

            file = pathlib.Path(self._filename)
            if file.exists():
                with open(self._filename) as fptr:
                    jsonf = json.loads(fptr.read())
                    self._attrs.update(jsonf)


            '''
                Update Automatic irrigation scheduler logic
            '''
            await self._setSchedulerTask()

            '''
                Update Md logic reset if turned form OFF -> ON
            '''
            if self._irrigation["au190"]["enable_md"] != self._attrs["au190"]["enable_md"]:
                self._irrigation["au190"]["enable_md"] = self._attrs["au190"]["enable_md"]

                self._irrigation["au190"]["md_status"] = []
                self._attrs["au190"]["md_status"] = []
                for idx in range(self.no_of_md):
                    self._irrigation["au190"]["md_status"].append({"count": 0,"time": datetime.datetime.now()})  # Count the Md ON status in an interval of time
                    self._attrs["au190"]["md_status"].append(False)  # True False 2-Suspended


            '''
                 Update Protection logic reset if turned form OFF -> ON
            '''
            if self._irrigation["au190"]["enable_protection"] != self._attrs["au190"]["enable_protection"]:
                self._irrigation["au190"]["enable_protection"] = self._attrs["au190"]["enable_protection"]

                await self._clear_motorRunningToLFc()
                self._irrigation["au190"]["motorPower"] = False
                await self._motorRunningToL_logic()  # has to be run again to check if the motor is running

                self._irrigation["au190"]["waterLim"] = False
                self._attrs["au190"]["waterLimLogic"] = False
                await self._clear_WaterL_Fc()
                await self._waterLim_logic()  # has to be run again to check if there is water

                self._attrs["au190"]["rainLimLogic"] = False
                await self._clear_RainL_Fc()

            else:

                '''
                    Update Motor Running too long logic reset if turned form OFF -> ON
                '''
                if self._irrigation["au190"]["enable_protection"] and self._irrigation["au190"]["enable_motorRunningToL"] != self._attrs["au190"]["enable_motorRunningToL"]:
                    self._irrigation["au190"]["enable_motorRunningToL"] = self._attrs["au190"][ "enable_motorRunningToL"]

                    await self._clear_motorRunningToLFc()
                    self._irrigation["au190"]["motorPower"] = False
                    await self._motorRunningToL_logic()  # has to be run again to check if the motor is running

                '''
                   Update Water limit logic reset if turned form OFF -> ON
                '''
                if self._irrigation["au190"]["enable_protection"] and self._irrigation["au190"]["enable_waterL"] != self._attrs["au190"]["enable_waterL"]:
                    self._irrigation["au190"]["enable_waterL"] = self._attrs["au190"][ "enable_waterL"]

                    self._irrigation["au190"]["waterLim"] = False
                    self._attrs["au190"]["waterLimLogic"] = False
                    await self._clear_WaterL_Fc()
                    await self._waterLim_logic()  # has to be run again to check if there is water

                '''
                   Update Rain limit logic reset if turned form OFF -> ON
                '''
                if self._irrigation["au190"]["enable_protection"] and self._irrigation["au190"]["enable_rainL"] != self._attrs["au190"]["enable_rainL"]:
                    self._irrigation["au190"]["enable_rainL"] = self._attrs["au190"]["enable_rainL"]

                    self._attrs["au190"]["rainLimLogic"] = False
                    await self._clear_RainL_Fc()

            '''
                 Update Manual - Enable/Disable Irrigation system
                 form here the input can be only 0 or 1
            '''
            await self._enable_irrigation_system(self._attrs["au190"]['irrig_sys_status']) # form here the input can be only 0 or 1


            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", self.entity_id, self._filename, jsonf['au190'])
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
            o[k]
            # log.info("my_hasattr___x___:[" + str(o) + "][" + str(k) + "]")
            return True

        except Exception:
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

        except Exception:
            return False
        return ret


    '''
        Check if the list contains that element and return the index in the list
    '''
    def getListIdx(self, list_elenet, topic):

        try:
            if topic in self._irrigation[list_elenet]:
               return self._irrigation[list_elenet].index(topic)

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

        return -1


    '''
       Force HA to send the status msg

       must be: FMT = '%Y-%m-%dT%H:%M:%S.%f'
    '''
    def myasync_write_ha_state(self):
        FMT = '%Y-%m-%dT%H:%M:%S.%f'
        self._attrs["Time"] = datetime.datetime.now().strftime(FMT)
        self.async_write_ha_state()


    '''
        Create PulseTime msg form Power msg

        fc = 1
            Needs to identify the Pulstime response
            "stat/basic/POWER1" -> "'stat/basic/RESULT/PulseTime1'"
            "stat/basic/POWER2" -> "stat/basic/RESULT/PulseTime2"

            "stat/basic/POWER" -> "stat/basic/RESULT/PulseTime1"
        fc = 2
            "stat/basic/POWER1" -> "'stat/basic/PulseTime1'"
            "stat/basic/POWER2" -> "stat/basic/PulseTime2"

            "stat/basic/POWER" -> "stat/basic/PulseTime1"

        fc = 3
            Get the topic from msg

            "stat/basic/POWER" -> "stat/basic/PulseTime1"

            return basic

    '''
    def conv_power_to_pulseTime(self, fc, msg):
        try:
            ret = None
            if fc == 1:

                tidx = msg.rfind("POWER") + 5
                if len(msg) == tidx:                    # if "stat/basic/POWER" -> "stat/basic/PulseTime1"
                    ret = msg.replace("POWER", "PulseTime1")
                else:
                    ret = msg.replace("POWER", "PulseTime")

                tidx = ret.rfind("/")
                ret = ret[0:tidx] + '/RESULT' + ret[tidx:]

            elif fc == 2:

                tidx = msg.rfind("POWER") + 5
                if len(msg) == tidx:  # if "stat/basic/POWER" -> "stat/basic/PulseTime1"
                    ret = msg.replace("POWER", "PulseTime1")
                else:
                    ret = msg.replace("POWER", "PulseTime")

                #tidx = ret.rfind("/")
                #ret = ret[0:tidx] + '/RESULT' + ret[tidx:]

            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s - %s", msg, ret)

            elif fc == 3:
                v = msg.split('/')
                if len(v) == 3:
                    ret = v[1]

            return ret
        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    '''
        Return data True or False

        Accepted Input values  = 'true', '1', 'yes', 'on' 'false', '0', 'no', 'off'

    '''
    def convToBool(self, data):
        try:
            if data.lower() in ['true', '1', 'yes', 'on']:
                return True
            elif data.lower() in ['false', '0', 'no', 'off']:
                return False
        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    '''

        Can be any integer or float number
        Returns True is string is a number.
    '''
    def is_number(self, n):
        return n.replace('.', '', 1).isdigit()

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
    def _forceTimeLimit(self, value, min_value):
        ret = 100 #10 sec
        try:
            if value < min_value:
                ret = min_value
            else:
                ret = value
        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))
        return ret


    async def async_au190(self, **kwargs):
        """
            Turn the device on.
            This method is a coroutine.
        """
        try:
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", kwargs)
            fc = int(kwargs["fc"])

            if (fc == 1):
                '''
                    Manual Irrigation

                '''
                #if self.is_number(kwargs["au190"]["zone"]):  # Must be number
                kwargs["zone"] = kwargs["au190"]["zone"]
                kwargs["pulsetime"] = -1  # force to not use
                await self.async_my_turn_on(**kwargs)

            elif (fc == 2):
                '''
                    Save data to server  - what we have in the au190 obj will be saved

                    1.  Get data from client
                    2.  Save to file
                    3.  Load data from file
                    4.  Update the attributes local var
                    5.  Sends back to client the new variable and updates the client

                '''
                await self._save_to_file(kwargs["au190"])
                await self._load_from_file()
                self.myasync_write_ha_state()

            elif (fc == 3):
                '''
                    Request info
                '''
                for item in self._irrigation["command_info"]:
                    self._publish(item, 0)

                self.myasync_write_ha_state()

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))