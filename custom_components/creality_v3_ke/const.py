"""Constants for the Creality Ender-3 V3 KE integration."""

DOMAIN = "creality_v3_ke"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_MODE = "mode"
CONF_BED_TEMP_OFFSET = "bed_temp_offset"   # °C correction added to raw bed reading
CONF_NOZZLE_TEMP_OFFSET = "nozzle_temp_offset"  # °C correction for nozzle if needed

MODE_WEBSOCKET = "websocket"
MODE_MOONRAKER = "moonraker"

DEFAULT_PORT_WEBSOCKET = 9999
DEFAULT_PORT_MOONRAKER = 7125
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_BED_TEMP_OFFSET = 10      # +10°C default — matches your reported gap
DEFAULT_NOZZLE_TEMP_OFFSET = 0    # nozzle typically accurate

# Normalised data keys
KEY_STATUS          = "status"
KEY_EXTRUDER_TEMP   = "extruder_temperature"
KEY_EXTRUDER_TARGET = "extruder_target"
KEY_BED_TEMP        = "bed_temperature"
KEY_BED_TARGET      = "bed_target"
KEY_PROGRESS        = "progress"
KEY_PRINT_TIME      = "print_time"
KEY_PRINT_TIME_LEFT = "print_time_left"
KEY_FILENAME        = "filename"
KEY_FAN_SPEED       = "fan_speed"
KEY_LAYER_CURRENT   = "layer_current"
KEY_LAYER_TOTAL     = "layer_total"
KEY_PRINT_SPEED     = "print_speed"
KEY_FLOW_RATE       = "flow_rate"
KEY_ONLINE          = "online"
KEY_RAW_DATA        = "raw_data"
