import os
from dotenv import load_dotenv
from service.secret_manager import ensure_secrets

# Ensure secrets exist before loading
ensure_secrets()
load_dotenv()

class Config:
    # Honda Identity Service (HIDAS)
    IDENTITY_HOST = "https://identity.services.honda.com"
    CLIENT_ID = os.getenv("HONDA_CLIENT_ID", "AcuraEVAndroidAppPrOd0083")
    CLIENT_SECRET = os.getenv("HONDA_CLIENT_SECRET", "")

    # Honda Web Services
    WSC_HOST = "https://wsc.hondaweb.com"

    # AWS IoT MQTT endpoint
    MQTT_HOST = "am7ptks1rwalc-ats.iot.us-east-2.amazonaws.com"
    MQTT_AUTHORIZER_NAME = "CPSD-IOT-CustAuthorizer-prod"

    # Common headers
    COMMON_HEADERS = {
        "hondaHeaderType.country_code": "US",
        "hondaHeaderType.language_code": "en",
        "hondaHeaderType.businessId": "ACURA EV",
        "User-Agent": "okhttp/4.12.0",
    }

    # Dashboard filters
    DASHBOARD_FILTERS = [
        "DigitalTwin",
        "EV BATTERY LEVEL",
        "EV CHARGE STATE",
        "EV PLUG STATE",
        "EV PLUG VOLTAGE",
        "GET COMMUTE SCHEDULE",
        "HIGH VOLTAGE BATTERY PRECONDITIONING STATUS",
        "VEHICLE RANGE",
        "odometer",
        "tireStatus",
        "HV BATTERY CHARGE COMPLETE TIME",
        "TARGET CHARGE LEVEL SETTINGS",
        "GET CHARGE MODE",
        "CABIN PRECONDITIONING TEMP CUSTOM SETTING",
        "CHARGER POWER LEVEL",
        "HANDS FREE CALLING",
        "ENERGY EFFICIENCY",
    ]
