import time
import logging
import voluptuous as vol
from random import randint
from paho.mqtt import client as mqtt_client


from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant, callback
from homeassistant.components.mqtt.const import DATA_MQTT
from homeassistant.components.climate import ClimateEntity
from homeassistant.helpers.event import async_track_state_change
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature
from homeassistant.const import CONF_NAME, ATTR_TEMPERATURE, STATE_UNKNOWN, STATE_UNAVAILABLE

from .utils import convert_temp_from_hex, convert_temp_to_hex

_LOGGER = logging.getLogger(__name__)

# set mqtt parameters
FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60

DOMAIN = "bbf_climate"
DEFAULT_NAME = "BBF Climate"

CONF_TEMPERATURE_ENTITY_ID = "temperature_sensor"
CONF_MQTT_SET_TOPIC = "set_topic"
CONF_MQTT_GET_TOPIC = "get_topic"

DEFAULT_TEMP = 21
DEFAULT_PRECISION = 1.0

INELS_HVAC_MODES = {"off": "00", "heat": "01", "cool": "03"}

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_TEMPERATURE_ENTITY_ID): cv.entity_id,
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
        self.hass = hass

        self._attr_has_entity_name = True
        self._attr_name = config[CONF_NAME]
        self._temperature_sensor = config[CONF_TEMPERATURE_ENTITY_ID]
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
        self._attr_current_temperature = 21

        # get information about MQTT client
        self.mqtt_data = self.hass.data[DATA_MQTT].client.conf
        self.mqtt_broker = self.mqtt_data["broker"]
        self.mqtt_port = self.mqtt_data["port"]
        self.mqtt_client_id = f"bbf-climate-{randint(0, 1000)}"
        self.mqtt_username = self.mqtt_data["username"]
        self.mqtt_password = self.mqtt_data["password"]

        # Create mqtt client
        self.mqtt_client = self.connect_mqtt()
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.subscribe(self.get_topic)
        self.mqtt_client.loop_start()

        # callback values
        self.critical_temp_raw = convert_temp_to_hex(50)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        _LOGGER.debug(f"async_added_to_hass {self} {self.name} {self.supported_features}")

        if self._temperature_sensor:
            async_track_state_change(self.hass, self._temperature_sensor, self._async_temp_sensor_changed)

    async def _async_temp_sensor_changed(self, entity_id, old_state, new_state) -> None:
        """Handle temperature sensor changes."""
        if new_state is None:
            return

        self._async_update_temp(new_state)
        self.async_write_ha_state()

        output_message = self.create_msg()
        self.mqtt_publish(client=self.mqtt_client, topic=self.set_topic, msg=output_message)

    @callback
    def _async_update_temp(self, state) -> None:
        """Update thermostat with the latest state from temperature sensor."""
        try:
            if state.state != STATE_UNKNOWN and state.state != STATE_UNAVAILABLE:
                self._attr_current_temperature = float(state.state)
        except ValueError as ex:
            _LOGGER.error("Unable to update from temperature sensor: %s", ex)

    def on_disconnect(self, client, userdata, rc):
        """reconnect to mqtt broker in case of disconnected"""

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

    def connect_mqtt(self) -> mqtt_client.Client:
        """
        function to create mqtt client and connect to mqtt broker. mqtt broker data is taken from home assistant

        """

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

    def mqtt_publish(self, client: mqtt_client.Client, topic: str, msg: str) -> None:
        """
        publish msg to given topic. in case of fail retry 5 times
        :param client: mqtt client
        :param topic: topic name
        :param msg: message
        """
        msg_count = 1
        while True:
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
            time.sleep(1)

    def on_message(self, client: mqtt_client.Client, userdata, msg) -> None:
        """
        callback function. update target temperature and HVAC mode
        """
        _LOGGER.info(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        message = msg.payload.decode()

        required_therm_term = convert_temp_from_hex(message, 8, 12)
        required_ac_term = convert_temp_from_hex(message, 20, 24)

        value_on_off = message.split("\n")[30:31]
        value_on_off = bin(int(value_on_off[0], 16))[2:].zfill(8)[4:]
        if value_on_off[3] == "0":
            self._attr_hvac_mode = HVACMode.OFF
        else:
            if value_on_off[1] == "1":
                self._attr_hvac_mode = HVACMode.HEAT
            if value_on_off[0] == "1":
                self._attr_hvac_mode = HVACMode.COOL

        if required_ac_term > 26:
            required_ac_term = 26
        if required_therm_term > 26:
            required_therm_term = 26

        self._attr_target_temperature = required_ac_term

        if self.hvac_mode == HVACMode.HEAT:
            self._attr_target_temperature = required_therm_term

        self.async_write_ha_state()

    def create_msg(self) -> str:
        """
        create byte message to send to inels controller
        :return: string with bytes
        """
        # create output message
        message = ""
        actual_temp_raw = convert_temp_to_hex(self.current_temperature)
        message = message + actual_temp_raw + "\n" + self.critical_temp_raw  # data 0-7
        current_temp = convert_temp_to_hex(self.target_temperature)
        message = message + "\n" + current_temp + "\n" + current_temp  # data 8-15
        message = message + "\n00\n07"  # data 16-17

        message = message + "\n" + INELS_HVAC_MODES[self.hvac_mode]
        return message

    # Climate set methods
    def set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

        output_message = self.create_msg()
        self.mqtt_publish(client=self.mqtt_client, topic=self.set_topic, msg=output_message)

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        self._attr_target_temperature = kwargs.get(ATTR_TEMPERATURE)
        self.async_write_ha_state()

        output_message = self.create_msg()
        self.mqtt_publish(client=self.mqtt_client, topic=self.set_topic, msg=output_message)
