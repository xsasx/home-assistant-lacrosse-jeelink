"""Constants for the LaCrosse Jeelink integration."""

DOMAIN = "lacrosse_jeelink"

CONF_BAUD = "baud"
CONF_SENSORS = "sensors"
CONF_SENSOR_KEY = "sensor_key"
CONF_SENSOR_NAME = "sensor_name"
CONF_RADIO_ID = "radio_id"
CONF_EXPIRE_AFTER = "expire_after"

DEFAULT_BAUD = 57600
DEFAULT_EXPIRE_AFTER = 300
DEFAULT_DEVICE = "/dev/ttyUSB0"

PLATFORMS = ["sensor", "binary_sensor"]
