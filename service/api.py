import requests
import json
import uuid
import datetime
from service.config import Config
import logging

logger = logging.getLogger(__name__)

class HondaApi:
    @staticmethod
    def _get_headers(extra_headers=None):
        headers = Config.COMMON_HEADERS.copy()
        if extra_headers:
            headers.update(extra_headers)
        return headers

    @staticmethod
    def register_client():
        url = f"{Config.IDENTITY_HOST}/hidas/rs/client/register"
        data = {
            "client_id": Config.CLIENT_ID,
            "client_secret": Config.CLIENT_SECRET
        }
        resp = requests.post(url, headers={"Content-Type": "application/x-www-form-urlencoded"}, data=data)
        resp.raise_for_status()
        
        try:
            resp_json = resp.json()
            return resp_json.get("clientregistrationkey", {}).get("client_reg_key")
        except:
            raise Exception(f"Failed to parse register response: {resp.text}")

    @staticmethod
    def generate_token(client_reg_key, username, password):
        url = f"{Config.IDENTITY_HOST}/hidas/rs/token/generate"
        data = {
            "client_reg_key": client_reg_key,
            "device_description": "Python_Flet_Client",
            "username": username,
            "password": password
        }
        resp = requests.post(url, headers={"Content-Type": "application/x-www-form-urlencoded"}, data=data)
        resp.raise_for_status()

        resp_json = resp.json()
        if resp_json.get("request_status") != "success":
            raise Exception(f"Auth failed: {resp.text}")

        return {
            "access_token": resp_json["token"]["access_token"],
            "hidas_ident": resp_json["user"]["hidas_ident"],
            "user": resp_json["user"]
        }

    @staticmethod
    def get_vehicles(access_token, hidas_ident):
        url = f"{Config.WSC_HOST}/REST/NGT/MyVehicle/1.0"
        headers = HondaApi._get_headers({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "hondaHeaderType.version": "2.0",
            "hondaHeaderType.siteId": "00e0e97f0fb543208a918fc946dea334",
            "hondaHeaderType.messageId": str(uuid.uuid4()),
            "hondaHeaderType.systemId": "com.honda.dealer.cv_android",
            "hondaHeaderType.userId": hidas_ident,
            "hondaHeaderType.clientType": "Mobile",
            "hondaHeaderType.collectedTimeStamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
        
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        
        data = resp.json()
        if data.get("status") != "SUCCESS":
            raise Exception(f"Get vehicles failed: {data}")
            
        return data.get("vehicleInfo", [])

    @staticmethod
    def get_cig_token(access_token, hidas_ident, vin):
        url = f"{Config.WSC_HOST}/REST/CIG/services/1.0/token"
        headers = HondaApi._get_headers({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "hondaHeaderType.userId": hidas_ident,
            "hondaHeaderType.hidasId": hidas_ident,
            "hondaHeaderType.version": "1.0",
            "hondaHeaderType.messageId": str(uuid.uuid4()).upper(),
            "hondaHeaderType.clientType": "Mobile",
            "hondaHeaderType.systemId": "com.honda.hondalink.cv_android",
            "hondaHeaderType.siteId": "b407a3025b374f668475e97d2e750816",
            "hondaHeaderType.collectedTimeStamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
        
        resp = requests.post(url, headers=headers, json={"device": vin})
        resp.raise_for_status()
        
        data = resp.json()
        if data.get("status") != "Success":
            raise Exception(f"CIG token failed: {data}")
            
        return {
            "cig_token": data["responseBody"]["token"],
            "cig_signature": data["responseBody"]["tokenSignature"]
        }

    @staticmethod
    def request_dashboard(access_token, vin):
        url = f"{Config.WSC_HOST}/REST/NGT/CIG/dbd/async"
        headers = HondaApi._get_headers({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "hondaHeaderType.version": "1.0",
            "hondaHeaderType.siteId": "18d216af12884813987e6b7f75a005a1",
            "hondaHeaderType.systemId": "com.honda.hondalink.cv_android",
            "hondaHeaderType.clientType": "Mobile",
            "hondaHeaderType.messageId": "I-13",
            "hondaHeaderType.collectedTimeStamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
        
        resp = requests.post(url, headers=headers, json={
            "device": vin,
            "filters": Config.DASHBOARD_FILTERS
        })
        
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("status") == "success":
            return data["responseBody"]["cigServiceRequestId"]
        else:
            raise Exception(f"Dashboard request failed: {data}")

    @staticmethod
    def request_start_climate(access_token, vin, pin, temperature):
        url = f"{Config.WSC_HOST}/REST/NGT/CIG/eng/async/srt"
        headers = HondaApi._get_headers({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "hondaHeaderType.version": "1.0",
            "hondaHeaderType.siteId": "18d216af12884813987e6b7f75a005a1",
            "hondaHeaderType.systemId": "com.honda.hondalink.cv_android",
            "hondaHeaderType.clientType": "Mobile",
            "hondaHeaderType.messageId": "S-1",
            "hondaHeaderType.collectedTimeStamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
        
        resp = requests.post(url, headers=headers, json={
            "device": vin,
            "extend": False,
            "pin": pin,
            "vehicleControl": {
                "acSetting": {
                    "acDefSetting": "autoOn",
                    "acTempVal": str(temperature)
                }
            }
        })
        
        data = resp.json()
        if resp.ok and data.get("status") in ["IN_PROGRESS", "success"]:
            return data["responseBody"]["cigServiceRequestId"]
        else:
            raise Exception(f"Climate start failed: {data}")

    @staticmethod
    def request_stop_climate(access_token, vin, pin, temperature):
        url = f"{Config.WSC_HOST}/REST/NGT/CIG/eng/async/sop"
        headers = HondaApi._get_headers({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "hondaHeaderType.version": "1.0",
            "hondaHeaderType.siteId": "18d216af12884813987e6b7f75a005a1",
            "hondaHeaderType.systemId": "com.honda.hondalink.cv_android",
            "hondaHeaderType.clientType": "Mobile",
            "hondaHeaderType.messageId": "S-1",
            "hondaHeaderType.collectedTimeStamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
        
        resp = requests.post(url, headers=headers, json={
            "device": vin,
            "extend": False,
            "pin": pin,
            "vehicleControl": {
                "acSetting": {
                    "acDefSetting": "autoOff",
                    "acTempVal": str(temperature)
                }
            }
        })
        
        data = resp.json()
        if resp.ok and data.get("status") in ["IN_PROGRESS", "success"]:
            return data["responseBody"]["cigServiceRequestId"]
        else:
            logger.error(f"Stop Climate Failed - Status: {resp.status_code}, Body: {resp.text}")
            raise Exception(f"Climate stop failed: {data}")


    
    @staticmethod
    def request_set_charge_target(access_token, vin, pin, level):
        url = f"{Config.WSC_HOST}/REST/NGT/TargetChargeLevel/1.0"
        headers = HondaApi._get_headers({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "hondaHeaderType.version": "1.0",
            "hondaHeaderType.siteId": "18d216af12884813987e6b7f75a005a1",
            "hondaHeaderType.systemId": "com.honda.hondalink.cv_android",
            "hondaHeaderType.clientType": "Mobile",
            "hondaHeaderType.messageId": "S-1",
            "hondaHeaderType.collectedTimeStamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
        
        resp = requests.post(url, headers=headers, json={
            "device": vin,
            "targetChargeLevel": int(level)
        })
        
        data = resp.json()
        if resp.ok and data.get("status") in ["IN_PROGRESS", "success"]:
            return data.get("responseBody", {}).get("cigServiceRequestId")
        else:
            logger.error(f"Set Charge Target Failed - Status: {resp.status_code}, Body: {resp.text}")
            raise Exception(f"Set charge target failed: {data}")


    


    @staticmethod
    def _generic_remote_command(access_token, vin, pin, command_name, endpoint_suffix):
         url = f"{Config.WSC_HOST}/REST/NGT/CIG/{endpoint_suffix}"
         headers = HondaApi._get_headers({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "hondaHeaderType.version": "1.0",
            "hondaHeaderType.siteId": "18d216af12884813987e6b7f75a005a1",
            "hondaHeaderType.systemId": "com.honda.hondalink.cv_android",
            "hondaHeaderType.clientType": "Mobile",
            "hondaHeaderType.messageId": "S-1",
            "hondaHeaderType.collectedTimeStamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
         
         payload = {
             "device": vin,
             "pin": pin
         }
         
         logger.debug(f"Remote Command Request - URL: {url}, Payload: [REDACTED]")
         resp = requests.post(url, headers=headers, json=payload)
         logger.debug(f"Remote Command Response - Status: {resp.status_code}, Body: {resp.text}")
         data = resp.json()
         
         if resp.ok and data.get("status") in ["IN_PROGRESS", "success"]:
             return data.get("responseBody", {}).get("cigServiceRequestId")
         else:
             raise Exception(f"{command_name} failed: {data}")

    @staticmethod
    def get_climate_status(access_token, vin):
        url = f"{Config.WSC_HOST}/REST/NGT/getClimateStatus/1.0/{vin}"
        headers = HondaApi._get_headers({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "hondaHeaderType.version": "1.0",
            "hondaHeaderType.siteId": "18d216af12884813987e6b7f75a005a1",
            "hondaHeaderType.systemId": "com.honda.hondalink.cv_android",
            "hondaHeaderType.clientType": "Mobile",
            "hondaHeaderType.messageId": str(uuid.uuid4()),
            "hondaHeaderType.collectedTimeStamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
        
        logger.debug(f"Requesting Climate Status: {url}")
        resp = requests.get(url, headers=headers)
        logger.debug(f"Climate Status Response - Status: {resp.status_code}, Body: {resp.text}")
        
        resp.raise_for_status()
        return resp.json()

