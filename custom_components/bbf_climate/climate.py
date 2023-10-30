import logging

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

from homeassistant.components.mqtt.client import publish as mqtt_publish
from homeassistant.components.mqtt.client import subscribe as mqtt_subscribe

_LOGGER = logging.getLogger(__name__)

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
        super().__init__()
        self._attr_has_entity_name = True
        self._attr_name = config[CONF_NAME]
        self.set_topic = config[CONF_MQTT_SET_TOPIC]
        self.get_topic = config[CONF_MQTT_GET_TOPIC]

        self.hass = hass
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

        self.subscriber = mqtt_subscribe(self.hass, self.set_topic, self.update)

    def set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

        mqtt_publish(hass=self.hass, topic=self.set_topic, payload=f"set new hvac mode - {self.hvac_mode}")

    def set_temperature(self, **kwargs):
        """Set new target temperature."""

        self._attr_target_temperature = kwargs.get(ATTR_TEMPERATURE)
        self.async_write_ha_state()

        mqtt_publish(hass=self.hass, topic=self.get_topic, payload=f"set new temperature mode - {self.target_temperature}")

    def update(self, topic, payload, qos) -> None:
        _LOGGER.info(f"i've get value {payload}")


