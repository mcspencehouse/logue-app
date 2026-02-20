from service.api import HondaApi
import json
import os
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, page, storage):
        self.page = page
        self.storage = storage # SharedPreferences control
        self.access_token = None
        self.hidas_ident = None
        self.user_info = None
        self.vehicles = []
        self.selected_vin = None
        
        # Initialize encryption
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if encryption_key:
            self.fernet = Fernet(encryption_key.encode())
        else:
            self.fernet = None
            logger.warning("No ENCRYPTION_KEY found. Credentials will be stored in plain text.")
        
    async def load_credentials(self):
        """Load credentials and decrypt sensitive fields"""
        username = await self.storage.get("honda_username")
        password_enc = await self.storage.get("honda_password")
        vin = await self.storage.get("honda_vin")
        pin_enc = await self.storage.get("honda_pin")
        
        password = self._decrypt(password_enc)
        pin = self._decrypt(pin_enc)
        
        return username, password, vin, pin

    async def save_credentials(self, username, password, vin, pin=None):
        """Save credentials and encrypt sensitive fields"""
        if username: await self.storage.set("honda_username", username)
        if password: 
            await self.storage.set("honda_password", self._encrypt(password))
        if vin: await self.storage.set("honda_vin", vin)
        if pin is not None: 
            await self.storage.set("honda_pin", self._encrypt(pin))

    async def logout(self):
        """Clear all stored credentials"""
        await self.storage.remove("honda_username")
        await self.storage.remove("honda_password")
        await self.storage.remove("honda_vin")
        await self.storage.remove("honda_pin")
        self.access_token = None
        self.hidas_ident = None
        self.user_info = None
        self.vehicles = []
        self.selected_vin = None

    def _encrypt(self, value):
        if not value or not self.fernet:
            return value
        return self.fernet.encrypt(value.encode()).decode()

    def _decrypt(self, value):
        if not value or not self.fernet:
            return value
        try:
            return self.fernet.decrypt(value.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None

    def login(self, username, password, vin=None):
        """Perform full login flow"""
        try:
            # 1. Register Client (gets reg key)
            client_reg_key = HondaApi.register_client()
            
            # 2. Generate Token
            auth_data = HondaApi.generate_token(client_reg_key, username, password)
            self.access_token = auth_data["access_token"]
            self.hidas_ident = auth_data["hidas_ident"]
            self.user_info = auth_data["user"]
            
            # 3. Get Vehicles
            self.vehicles = HondaApi.get_vehicles(self.access_token, self.hidas_ident)
            
            if not self.vehicles:
                raise Exception("No vehicles found on this account")
                
            # Default to first VIN if not specified or not found
            self.selected_vin = self.vehicles[0]["VIN"]
            if vin:
                for v in self.vehicles:
                    if v.get("VIN") == vin:
                        self.selected_vin = vin
                        break
            
            return True, "Login successful"
        except Exception as e:
            return False, str(e)

    def get_vehicle_name(self):
        if self.vehicles:
            for v in self.vehicles:
                if v.get('VIN') == self.selected_vin:
                    return f"{v.get('ModelYear')} {v.get('DivisionName')} {v.get('ModelCode')}"
            # Fallback to first if selected_vin is not found for some reason
            v = self.vehicles[0]
            return f"{v.get('ModelYear')} {v.get('DivisionName')} {v.get('ModelCode')}"
        return "Unknown Vehicle"
