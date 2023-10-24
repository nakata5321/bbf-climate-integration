import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.climate import (
    ClimateEntity
)
from homeassistant.components.climate.const import (
    FAN_ON,
    FAN_OFF,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    HVACMode,
    HVACAction
)


from homeassistant.const import (
    CONF_NAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from homeassistant.components.mqtt.client import publish as mqtt_publish

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


async def async_setup_platform(
        hass: HomeAssistant, config: ConfigType, async_add_entities) -> None:

    """Set up the Template Climate."""
    async_add_entities([BbfClimate(hass, config)])


class BbfClimate(ClimateEntity):

    def __init__(self, hass: HomeAssistant, config: ConfigType):
        super().__init__()
        self._current_humidity = None
        self._current_temp = None
        self.hass = hass

        self._attr_fan_modes = [FAN_ON, FAN_OFF, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
        self._attr_hvac_action = HVACAction.OFF

        self._attr_name = config[CONF_NAME]
        self._attr_min_temp = 16
        self._attr_max_temp = 33
        self._attr_target_temperature_step = 0.5

        self._current_fan_mode = FAN_LOW  # default optimistic state
        self._current_operation = HVACMode.OFF  # default optimistic state
        self._current_swing_mode = HVACMode.OFF  # default optimistic state
        self._target_temp = DEFAULT_TEMP  # default optimistic state
        self._attr_target_temperature_high = None
        self._attr_target_temperature_low = None

        self._available = True
        self._unit_of_measurement = hass.config.units.temperature_unit
        self._attr_supported_features = 0

        self._attr_hvac_modes = [
                HVACMode.OFF,
                HVACMode.COOL,
                HVACMode.HEAT,
            ]

    def set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        mqtt_publish(hass=self.hass, topic=CONF_MQTT_SET_TOPIC, payload="set new hvac mode")

    def set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        pass

    def set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        pass

    def set_humidity(self, humidity):
        """Set new target humidity."""
        pass

    def set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        pass

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        mqtt_publish(hass=self.hass, topic=CONF_MQTT_SET_TOPIC, payload=f"set new temperature mode - {self._target_temp}")

    def turn_aux_heat_on(self) -> None:
        """Turn auxiliary heater on."""
        pass

    def turn_aux_heat_off(self) -> None:
        """Turn auxiliary heater off."""
        pass