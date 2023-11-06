# bbf climate integration

This Home Assistant integration give the ability to create climate instance. 
This instance creates mqtt message with byte message to inels controller and subscribe to mqtt topic with callback.

## Installation

Download folder to the `custom_components` folder.

in `configuration.yaml` and next:

```shell
climate:
  - platform: bbf_climate
    temperature_sensor: <TEMPERATURE_SENSOR_ENTITY_ID>
    set_topic: "<SET_MQTT_TOPIC>"
    get_topic: "<CALLBACK_MQTT_TOPIC>"
```

- `temperature_sensor` - Insert here our temperature sensor id. For example "sensor.temperature_humidity_sensor_temperature".
- `set_topic` - provide topic name to which you want to push message.
- `get_topic` - provide topic name from which you want to listen feedback.

After that restart Home Assistant. After that you will be able to create climate card on the dashboard.


## Additional

Additionally, you can change climate entity name. For this add this parameter to configuration file:

```shell
climate:
  - platform: bbf_climate
    name: <YUOR_NAME_FOR_ENTITY>
    ...
```