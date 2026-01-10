"""Constants for the Xinao Energy Analysis integration."""

DOMAIN = "xinao_energy"

# Default values
DEFAULT_UPDATE_INTERVAL = 30  # minutes
DEFAULT_CLIENT_TYPE = "gaswx"

# Configuration
CONF_TOKEN = "token"
CONF_PAYMENT_NO = "payment_no"
CONF_COMPANY_CODE = "company_code"
CONF_UPDATE_INTERVAL = "update_interval"

# API
API_URL = "https://wechatapp.ecej.com/livingpay/v3/xcx/electricity/getEnergyAnalysis.json"
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
    "arrears_amount": {
        "name": "Arrears Amount",
        "unit": "CNY",
        "icon": "mdi:cash-minus",
        "device_class": "monetary",
        "state_class": "total",
    },
    "current_month_usage": {
        "name": "Current Month Usage",
        "unit": "m³",
        "icon": "mdi:fire",
        "device_class": "gas",
        "state_class": "total_increasing",
    },
    "current_month_cost": {
        "name": "Current Month Cost",
        "unit": "CNY",
        "icon": "mdi:currency-cny",
        "device_class": "monetary",
        "state_class": "total_increasing",
    },
    "total_gas_count": {
        "name": "Total Gas Count",
        "unit": "m³",
        "icon": "mdi:fire",
        "device_class": "gas",
        "state_class": "total_increasing",
    },
    "available_days": {
        "name": "Available Days",
        "unit": "days",
        "icon": "mdi:calendar-range",
        "device_class": None,
        "state_class": None,
    },
}
