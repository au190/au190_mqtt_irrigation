import asyncio
import logging
import sys
from homeassistant import config_entries
from homeassistant.helpers.dispatcher import async_dispatcher_send
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.const import ATTR_ENTITY_ID

_LOGGER = logging.getLogger(__name__)

DOMAIN = "au190_mqtt_irrigation"
DATA_SERVICE_EVENT = "au190_service_idle"
SERVICE_AU190= "au190_fc"

ATTR_COUNT_DOWN = "countDown"
ATTR_TIMERS = "timers"

async def async_setup(hass, config):
    """Set up the au190 component."""
    conf = config.get(DOMAIN)
    hass.data[DOMAIN] = conf or {}
    hass.data[DATA_SERVICE_EVENT] = asyncio.Event()

    #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", conf, DOMAIN, DATA_SERVICE_EVENT)

    if conf is not None:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_IMPORT}
            )
        )

    async def service_handle(service):
        """Dispatch a service call."""
        hass.data[DATA_SERVICE_EVENT].clear()
        async_dispatcher_send(hass, DOMAIN, service.service, service.data)
        await hass.data[DATA_SERVICE_EVENT].wait()

    hass.services.async_register(DOMAIN, SERVICE_AU190, service_handle)


    return True

async def async_setup_entry(hass, entry):
    """Set up au190 from a config entry."""
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, DOMAIN)
    )
    return True
