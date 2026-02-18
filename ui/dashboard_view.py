import flet as ft
from service.auth import AuthService
from service.mqtt_client import AwsMqttClient
from service.api import HondaApi
from ui.controls_view import ControlsView
import threading
import json
import time

import asyncio

class DashboardView(ft.Container):
    def __init__(self, page, auth_service: AuthService, on_logout):
        super().__init__(expand=True)
        self.auth_service = auth_service
        self.on_logout = on_logout
        self.mqtt_client = None
        self.is_connected = False
        
        # UI Elements
        self.vehicle_name = self.auth_service.get_vehicle_name()
        self.battery_text = ft.Text("-- %", size=48, weight="bold", color=ft.Colors.WHITE)
        self.range_text = ft.Text("-- miles", size=24, color=ft.Colors.WHITE)
        self.charge_status_text = ft.Text("--", size=16, weight="w500", color=ft.Colors.CYAN_100)
        self.charge_details_text = ft.Text("--", size=14, italic=True, color=ft.Colors.CYAN_100)
        self.odometer_text = ft.Text("-- miles", size=18, weight="w600")
        self.status_text = ft.Text("Connecting...", italic=True, size=12, color="secondary")
        self.last_updated = ft.Text("Last Updated: Never", size=12, color="secondary")

        # Tire Pressure UI (Modernized)
        self.tire_pressures = {
            "frontLeft": ft.Text("-- PSI", weight="bold"),
            "frontRight": ft.Text("-- PSI", weight="bold"),
            "rearLeft": ft.Text("-- PSI", weight="bold"),
            "rearRight": ft.Text("-- PSI", weight="bold")
        }
        
        def tire_card(label, control):
            return ft.Container(
                content=ft.Column([
                    ft.Text(label, size=12, color="secondary"),
                    control
                ], horizontal_alignment="center", spacing=2),
                padding=10,
                border=ft.Border.all(1, ft.Colors.WHITE_10),
                border_radius=10,
                expand=True
            )

        self.tires_grid = ft.Column([
            ft.Row([
                tire_card("Front Left", self.tire_pressures["frontLeft"]),
                tire_card("Front Right", self.tire_pressures["frontRight"]),
            ], spacing=10),
            ft.Row([
                tire_card("Rear Left", self.tire_pressures["rearLeft"]),
                tire_card("Rear Right", self.tire_pressures["rearRight"]),
            ], spacing=10),
        ], spacing=10)

        # Hero Section (Battery & Range)
        self.hero_section = ft.Container(
            content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Text(self.vehicle_name, size=24, weight="bold", color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER),
                ft.Container(height=10),
                ft.Row([
                    ft.IconButton(
                        icon=ft.icons.Icons.REFRESH,
                        icon_color=ft.Colors.CYAN_200,
                        tooltip="Refresh Data",
                        on_click=self.refresh_data
                    ),
                    ft.IconButton(
                        icon=ft.icons.Icons.LOGOUT,
                        icon_color=ft.Colors.RED_400,
                        tooltip="Logout",
                        on_click=self.handle_logout
                    ),
                    ft.Icon(ft.icons.Icons.ELECTRIC_CAR, color=ft.Colors.CYAN_200, size=28)
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=20),
                ft.Column([
                    ft.Row([
                        self.battery_text,
                        ft.Icon(ft.icons.Icons.BATTERY_CHARGING_FULL, color=ft.Colors.GREEN_400, size=40)
                    ], alignment="center", spacing=10),
                    self.range_text,
                ], horizontal_alignment="center"),
                ft.Container(height=10),
                ft.Column([
                    self.charge_status_text,
                    self.charge_details_text,
                ], horizontal_alignment="center", spacing=2),
            ]),
            padding=ft.Padding.only(top=50, left=30, right=30, bottom=30),
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=[ft.Colors.BLUE_900, ft.Colors.BLUE_800, ft.Colors.INDIGO_900],
            ),
            border_radius=ft.BorderRadius.only(bottom_left=30, bottom_right=30),
            margin=ft.Margin.only(bottom=10)
        )

        self.controls_view = ControlsView(page, self.auth_service, self.mqtt_client)
        
        # Main Layout with ListView and RefreshIndicator
        self.list_view = ft.ListView(
            expand=True,
            spacing=10,
            padding=ft.Padding.only(bottom=20),
            controls=[
                self.hero_section,
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=20),
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.icons.Icons.SPEED, size=20, color="secondary"),
                            ft.Text("Odometer", size=14, color="secondary"),
                            ft.Container(expand=True),
                            self.odometer_text
                        ], alignment="center"),
                        ft.Divider(color=ft.Colors.WHITE_10),
                        ft.Text("Tire Pressures", size=16, weight="bold"),
                        self.tires_grid,
                        ft.Container(height=10),
                        self.controls_view,
                        ft.Container(height=10),
                        ft.Row([
                            ft.Column([
                                self.status_text,
                                self.last_updated
                            ], horizontal_alignment="center", spacing=2)
                        ], alignment=ft.MainAxisAlignment.CENTER)
                    ])
                )
            ]
        )

        self.content = self.list_view

    def did_mount(self):
        # Start connection in background
        self.page.run_task(self.connect_and_subscribe)

    def will_unmount(self):
        if self.mqtt_client:
            self.mqtt_client.disconnect()

    async def connect_and_subscribe(self):
        try:
            self.loop = asyncio.get_running_loop()
            self.status_text.value = "Authenticating MQTT..."
            self.update()
            
            # Get CIG Token (Blocking)
            def get_creds_task():
                return HondaApi.get_cig_token(
                    self.auth_service.access_token,
                    self.auth_service.hidas_ident,
                    self.auth_service.selected_vin
                )
            
            creds = await self.loop.run_in_executor(None, get_creds_task)
            
            # Connect MQTT
            self.status_text.value = "Connecting to AWS IoT..."
            self.update()
            
            # MQTT Init (Blocking-ish)
            def mqtt_connect_task():
                client = AwsMqttClient(
                    self.auth_service.selected_vin,
                    creds["cig_token"],
                    creds["cig_signature"],
                    self.on_mqtt_message
                )
                client.connect()
                return client

            self.mqtt_client = await self.loop.run_in_executor(None, mqtt_connect_task)
            self.is_connected = True
            
            # Update controls view with the now-active mqtt client
            self.controls_view.mqtt_client = self.mqtt_client
            
            # Subscribe to Dashboard
            vin = self.auth_service.selected_vin
            topic = f"$aws/things/thing_{vin}/shadow/name/DASHBOARD_ASYNC/update"
            self.mqtt_client.subscribe(topic)
            
            self.status_text.value = "Connected. Waiting for data..."
            self.update()
            
            # Request initial data
            await self.refresh_data(None)
            
        except Exception as e:
            self.status_text.value = f"Connection Error: {e}"
            self.update()

    def on_mqtt_message(self, topic, payload):
        try:
            data = json.loads(payload)
            # Check if it's the dashboard update
            if "DASHBOARD_ASYNC" in topic:
                self.update_dashboard_ui(data)
                
        except Exception as e:
            print(f"Error parsing MQTT message: {e}")

    async def _do_refresh(self):
        try:
            if not self.is_connected:
                pass
            
            # Use captured loop or get new one
            loop = getattr(self, 'loop', asyncio.get_running_loop())
            
            def request_task():
                HondaApi.request_dashboard(
                    self.auth_service.access_token,
                    self.auth_service.selected_vin
                )
            
            await loop.run_in_executor(None, request_task)
            
        except Exception as e:
            print(f"Refresh failed: {e}")

    async def refresh_data(self, e):
        self.status_text.value = "Requesting update..."
        self.update()
        await self._do_refresh()

    async def handle_logout(self, e):
        if self.mqtt_client:
            self.mqtt_client.disconnect()
        if self.on_logout:
            await self.on_logout()
        
    def update_dashboard_ui(self, data):
        reported = data.get("state", {}).get("reported", {})
        
        # Data is inside reported -> responseBody
        rb = reported.get("responseBody", {})
        
        ev_status = rb.get("evStatus", {})
        odometer_data = rb.get("odometer", {})
        tire_status = rb.get("tireStatus", {})
        charge_mode = rb.get("getChargeMode", {})
        charge_time = rb.get("hvBatteryChargeCompleteTime", {})
        
        # Battery & Range
        battery = ev_status.get("soc")
        range_val = ev_status.get("evRange")
        charge_status = ev_status.get("chargeStatus")
        plug_status = ev_status.get("plugStatus")
        
        if battery is not None:
            self.battery_text.value = f"{battery}%"
        if range_val is not None:
            self.range_text.value = f"{range_val} miles"

        # Charging status & type
        status_parts = []
        if charge_status:
            # Normalize charge status text
            cs_lower = charge_status.lower()
            if cs_lower == "charging":
                status_parts.append("Charging")
            elif cs_lower in ["plugged", "connected"]:
                status_parts.append("Plugged In")
            else:
                status_parts.append(charge_status.capitalize())

        if plug_status in ["plugged", "CONNECTED", "connected"]:
             if "Plugged In" not in status_parts:
                 status_parts.append("(Plugged In)")
        
        # Determine charging type/voltage
        charge_mode_val = ev_status.get("chargeMode")
        power_level = rb.get("chargerPowerLevel", {}).get("value")
        charge_type_raw = charge_mode.get("chargeModeType", {}).get("value")
        
        display_type = None
        if power_level and power_level.isdigit() and int(power_level) > 0:
            display_type = f"{power_level}V"
        elif charge_mode_val and charge_mode_val.isdigit() and int(charge_mode_val) > 0:
            display_type = f"{charge_mode_val}V"
        elif charge_type_raw and charge_type_raw != "CHARGE_NOW":
            display_type = charge_type_raw
             
        if display_type:
             status_parts.append(f"via {display_type}")
             
        self.charge_status_text.value = " ".join(status_parts) if status_parts else "Not Charging"

        # Target and ETA
        target_level = charge_mode.get("generalAwayTargetChargeLevel", {}).get("value")
        eta_day = charge_time.get("hvBatteryChargeCompleteDay", {}).get("value")
        eta_hour = charge_time.get("hvBatteryChargeCompleteHour", {}).get("value")
        eta_min = charge_time.get("hvBatteryChargeCompleteMinute", {}).get("value")

        details = []
        if target_level:
            details.append(f"Target: {target_level}%")
        if eta_day and eta_hour is not None and eta_min is not None:
            try:
                h = int(eta_hour)
                ampm = "AM" if h < 12 else "PM"
                h12 = h % 12
                if h12 == 0:
                    h12 = 12
                details.append(f"ETA: {eta_day} {h12}:{str(eta_min).zfill(2)} {ampm}")
            except:
                details.append(f"ETA: {eta_day} {eta_hour}:{str(eta_min).zfill(2)}")
        
        self.charge_details_text.value = " • ".join(details) if details else ""

        # Odometer
        odometer = odometer_data.get("value")
        if odometer is not None:
            self.odometer_text.value = f"{odometer} miles"
            
        # Tire Pressures
        def kpa_to_psi(kpa):
            try:
                return round(float(kpa) * 0.145038, 1)
            except:
                return "--"

        for pos, text_control in self.tire_pressures.items():
            pressure_kpa = tire_status.get(pos, {}).get("pressureData", {}).get("value")
            if pressure_kpa:
                text_control.value = f"{kpa_to_psi(pressure_kpa)} PSI"
                # Color based on pressure (simple heuristic)
                psi = kpa_to_psi(pressure_kpa)
                if isinstance(psi, float):
                    text_control.color = "red" if psi < 30 or psi > 45 else None
        
        self.status_text.value = "Data Received"
        self.last_updated.value = f"Last Updated: {time.strftime('%I:%M:%S %p')}"
        
        # Update UI safely
        if hasattr(self, 'loop'):
            import inspect
            async def ui_update_task():
                res = self.update()
                if inspect.isawaitable(res):
                    await res
            
            asyncio.run_coroutine_threadsafe(ui_update_task(), self.loop)
        else:
            self.update()

