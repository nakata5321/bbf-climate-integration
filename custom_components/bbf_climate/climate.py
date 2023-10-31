import asyncio
import logging
import time
from random import randint

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.climate import (
    ClimateEntity
)
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature
)

from homeassistant.const import (
    CONF_NAME,
    ATTR_TEMPERATURE
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .utils import to_thread

from paho.mqtt import client as mqtt_client
from homeassistant.components.mqtt.const import DATA_MQTT

_LOGGER = logging.getLogger(__name__)

# set mqtt parameters
FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60

DOMAIN = "bbf_climate"
DEFAULT_NAME = "BBF Climate"
# CONF_CURRENT_TEMP_TEMPLATE = "current_temperature_template"
CONF_MQTT_SET_TOPIC = "set_topic"
CONF_MQTT_GET_TOPIC = "get_topic"

DEFAULT_TEMP = 21
DEFAULT_PRECISION = 1.0

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_MQTT_SET_TOPIC): cv.string,
        vol.Required(CONF_MQTT_GET_TOPIC): cv.string,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None) -> None:
    """Set up the BBF Climate."""
    async_add_entities([BbfClimate(hass, config)])


class BbfClimate(ClimateEntity):

    def __init__(self, hass: HomeAssistant, config: ConfigType):
        # Set Climate attributes
        super().__init__()
        self._attr_has_entity_name = True
        self._attr_name = config[CONF_NAME]
        self.set_topic = config[CONF_MQTT_SET_TOPIC]
        self.get_topic = config[CONF_MQTT_GET_TOPIC]
        self._attr_temperature_unit = hass.config.units.temperature_unit
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_min_temp = 16
        self._attr_max_temp = 26
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_hvac_modes = [
                HVACMode.OFF,
                HVACMode.COOL,
                HVACMode.HEAT,
            ]
        self._attr_target_temperature = 21

        self.hass = hass

        # get information about MQTT client
        self.mqtt_data = self.hass.data[DATA_MQTT].client.conf
        self.mqtt_broker = self.mqtt_data["broker"]
        self.mqtt_port = self.mqtt_data["port"]
        self.mqtt_client_id = f'bbf-climate-{randint(0, 1000)}'
        self.mqtt_username = self.mqtt_data["username"]
        self.mqtt_password = self.mqtt_data["password"]

        # Create mqtt client
        self.mqtt_client = self.connect_mqtt()
        self.mqtt_client.loop_start()

    def on_disconnect(self, client, userdata, rc):
        _LOGGER.warning("Disconnected with result code: %s", rc)
        reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
        while reconnect_count < MAX_RECONNECT_COUNT:
            _LOGGER.info("Reconnecting in %d seconds...", reconnect_delay)
            time.sleep(reconnect_delay)

            try:
                client.reconnect()
                _LOGGER.info("Reconnected successfully!")
                return
            except Exception as err:
                _LOGGER.error("%s. Reconnect failed. Retrying...", err)

            reconnect_delay *= RECONNECT_RATE
            reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
            reconnect_count += 1
        _LOGGER.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)

    def connect_mqtt(self):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                _LOGGER.info("Connected to MQTT Broker!")
            else:
                _LOGGER.warning("Failed to connect, return code %d\n", rc)

        # Set Connecting Client ID
        client = mqtt_client.Client(self.mqtt_client_id)
        client.username_pw_set(self.mqtt_username, self.mqtt_password)
        client.on_connect = on_connect
        client.on_disconnect = self.on_disconnect
        client.connect(self.mqtt_broker, self.mqtt_port)
        return client

    @to_thread
    def mqtt_publish(self, client: mqtt_client.Client, topic: str, msg: str) -> None:
        msg_count = 1
        while True:
            time.sleep(1)
            result = client.publish(topic, msg)
            # result: [0, 1]
            status = result[0]
            if status == 0:
                _LOGGER.info(f"Send `{msg}` to topic `{topic}`")
                break
            else:
                _LOGGER.warning(f"Failed to send message to topic {topic}")
            msg_count += 1
            if msg_count > 5:
                _LOGGER.error(f"unable to sent message {msg} to topic {topic}")
                break




    # Climate set methods
    def set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

        asyncio.ensure_future(self.mqtt_publish(client=self.mqtt_client, topic=self.set_topic, msg=f"set new hvac mode - {self.hvac_mode}"))

    def set_temperature(self, **kwargs):
        """Set new target temperature."""

        self._attr_target_temperature = kwargs.get(ATTR_TEMPERATURE)
        self.async_write_ha_state()

        asyncio.ensure_future(self.mqtt_publish(client=self.mqtt_client, topic=self.get_topic, msg=f"set new temperature mode - {self.target_temperature}"))

    def update(self, topic, payload, qos) -> None:
        _LOGGER.info(f"i've get value {payload}")


