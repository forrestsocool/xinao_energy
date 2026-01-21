"""Constants for the Xinao Energy integration."""

DOMAIN = "xinao_energy"

# Default values
DEFAULT_UPDATE_INTERVAL = 30  # minutes
DEFAULT_CITY_ID = "62"

# Configuration
CONF_TOKEN = "token"
CONF_DEVICE_ID = "device_id"
CONF_CITY_ID = "city_id"
CONF_UPDATE_INTERVAL = "update_interval"

# API URLs
API_URL = "https://iot.ecej.com/app/device/model/detail/v1"
TOKEN_REFRESH_URL = "https://ucapi.ecej.com/uc/v1/token/refresh"
ORDER_LIST_URL = "https://oc.ecej.com/v1/order/bizOrderList"
API_SECRET = "8796135e9f8349d998345f9f13d8bd95"

# Sensor types
SENSOR_TYPES = {
    "balance": {
        "name": "Balance",
        "unit": "CNY",
        "icon": "mdi:cash",
        "device_class": "monetary",
        "state_class": "total",
    },
    "gas_price": {
        "name": "Gas Price",
        "unit": "CNY/m³",
        "icon": "mdi:currency-cny",
        "device_class": None,
        "state_class": None,
    },
    "today_cost": {
        "name": "Today Cost",
        "unit": "CNY",
        "icon": "mdi:cash-clock",
        "device_class": "monetary",
        "state_class": "total",
    },
    "today_usage": {
        "name": "Today Usage",
        "unit": "m³",
        "icon": "mdi:fire",
        "device_class": "gas",
        "state_class": "total",
    },
    "monthly_cost": {
        "name": "Monthly Cost",
        "unit": "CNY",
        "icon": "mdi:cash-multiple",
        "device_class": "monetary",
        "state_class": "total",
    },
    "monthly_usage": {
        "name": "Monthly Usage",
        "unit": "m³",
        "icon": "mdi:fire-circle",
        "device_class": "gas",
        "state_class": "total",
    },
    "last_recharge": {
        "name": "Last Recharge",
        "unit": "CNY",
        "icon": "mdi:cash-plus",
        "device_class": "monetary",
        "state_class": None,
    },
    "last_recharge_time": {
        "name": "Last Recharge Time",
        "unit": None,
        "icon": "mdi:clock-outline",
        "device_class": "timestamp",
        "state_class": None,
    },
}
