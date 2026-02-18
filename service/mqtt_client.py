import paho.mqtt.client as mqtt
import ssl
import json
import time
import threading
from service.config import Config

class AwsMqttClient:
    def __init__(self, vin, cig_token, cig_signature, on_message_callback):
        self.vin = vin
        self.cig_token = cig_token
        self.cig_signature = cig_signature
        self.on_message_callback = on_message_callback
        
        # Unique Client ID
        client_id = f"paho{int(time.time() * 1000)}"
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id, transport="websockets")
        self.client.username_pw_set(username=None, password=None)
        
        # TLS required for AWS IoT
        self.client.tls_set(cert_reqs=ssl.CERT_NONE)
        
        # Set Custom Headers for Authentication
        headers = {
            "User-Agent": "?SDK=Android&Version=2.75.0",
            "X-Amz-CustomAuthorizer-Signature": cig_signature,
            "prod_key": cig_token,
            "X-Amz-CustomAuthorizer-Name": Config.MQTT_AUTHORIZER_NAME,
        }
        
        # Path must be /mqtt for AWS IoT WebSockets
        self.client.ws_set_options(path="/mqtt", headers=headers)
        
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        self.connected_event = threading.Event()
        self.connection_error = None

    def connect(self):
        try:
            # Config.MQTT_HOST is the endpoint
            print(f"Connecting to {Config.MQTT_HOST}...")
            self.client.connect(Config.MQTT_HOST, 443, 60)
            self.client.loop_start()
            
            # Wait for connection
            if not self.connected_event.wait(timeout=15):
                self.client.loop_stop()
                raise Exception("AWS IoT MQTT connection timed out")
                
            if self.connection_error:
                 raise Exception(self.connection_error)
                 
            return True
        except Exception as e:
            print(f"MQTT Connect failed: {e}")
            raise e

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def subscribe(self, topic):
        print(f"Subscribing to {topic}")
        self.client.subscribe(topic, qos=1)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("AWS IoT MQTT connected")
            self.connected_event.set()
        else:
            self.connection_error = f"Connection failed with code {rc}"
            self.connected_event.set() # Release wait so we can raise error

    def _on_disconnect(self, client, userdata, rc):
        print(f"AWS IoT MQTT disconnected: {rc}")

    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode()
        # print(f"Received message on {msg.topic}: {payload}")
        if self.on_message_callback:
            self.on_message_callback(msg.topic, payload)
