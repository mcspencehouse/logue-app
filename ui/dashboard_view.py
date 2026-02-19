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
        self.main_page = page
        self.auth_service = auth_service
        self.on_logout = on_logout
        self.mqtt_client = None
        self.is_connected = False
        
        # UI Elements
        self.vehicle_name = self.auth_service.get_vehicle_name()
        self.battery_text = ft.Text("-- %", size=48, weight="bold", color=ft.Colors.WHITE)
        self.range_text = ft.Text("-- miles", size=24, color=ft.Colors.WHITE)
        self.charge_status_text = ft.Text("--", size=16, weight="bold", color=ft.Colors.GREEN_400)
        self.charge_details_text = ft.Text("--", size=13, weight="w500", color=ft.Colors.BLUE_GREY_200)
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
        # Hero Section (Battery & Range) - Redesigned
        
        # Ring Progress for Battery
        self.battery_ring = ft.ProgressRing(
            value=0.0, 
            stroke_width=20, 
            color=ft.Colors.CYAN_400, 
            bgcolor=ft.Colors.WHITE_10,
            width=250,
            height=250
        )
        
        # Center Content for Ring
        ring_content = ft.Column(
            controls=[
                ft.Icon(ft.icons.Icons.BOLT, color=ft.Colors.CYAN_400, size=30),
                self.battery_text,
                self.range_text,
                ft.Text("RANGE", size=12, color=ft.Colors.CYAN_100, weight="bold"),
                ft.IconButton(
                    icon=ft.icons.Icons.SETTINGS, 
                    icon_color=ft.Colors.WHITE_54, 
                    icon_size=20, 
                    tooltip="Set Charge Limit",
                    on_click=self.open_charge_settings
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0
        )

        # Main Battery Indicator Stack
        battery_indicator = ft.Stack(
            controls=[
                # Glow effect container
                ft.Container(
                    width=250, height=250,
                    border_radius=125,
                    shadow=ft.BoxShadow(
                        spread_radius=0,
                        blur_radius=50,
                        color=ft.Colors.CYAN_900,
                        offset=ft.Offset(0, 0),
                    ),
                ),
                self.battery_ring,
                ft.Container(
                    content=ring_content,
                    alignment=ft.Alignment(0, 0),
                    width=250, 
                    height=250
                )
            ],
            alignment=ft.Alignment(0, 0)
        )

        # Header Row
        header_row = ft.Row(
            controls=[
                ft.Text(self.vehicle_name, size=20, weight="bold", color=ft.Colors.CYAN_200, font_family="Roboto Mono"),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.icons.Icons.REFRESH,
                    icon_color=ft.Colors.WHITE_54,
                    tooltip="Refresh Data",
                    on_click=self.refresh_data
                ),
                ft.IconButton(
                    icon=ft.icons.Icons.LOGOUT, # Styled logout
                    icon_color=ft.Colors.WHITE_54,
                    tooltip="Logout",
                    on_click=self.handle_logout
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        # Charging Status Card (Mockup Style)
        # Gradient border effect using Container with gradient background and padding
        self.charging_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("CHARGING STATUS", size=12, weight="bold", color=ft.Colors.WHITE_70),
                    ft.Container(expand=True),
                    ft.Icon(ft.icons.Icons.BOLT, col={"xs":0, "sm": 0}, color=ft.Colors.GREEN_400) # Hidden bolt, maybe use for active status
                ]),
                ft.Container(height=5),
                ft.Row([
                    self.charge_status_text,
                    ft.Container(expand=True),
                    # Graphic for charging curve could go here, simplified for now
                    ft.Icon(ft.icons.Icons.GRAPHIC_EQ, color=ft.Colors.GREEN_400, size=30, opacity=0.5) 
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(color=ft.Colors.WHITE_10, height=20),
                ft.Row([
                    self.charge_details_text
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ]),
            padding=20,
            border_radius=15,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=[ft.Colors.WHITE_10, ft.Colors.WHITE_10]
            ),
            border=ft.Border.all(1, ft.Colors.GREEN_400), # Green border to match mockup "glow"
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=20,
                color=ft.Colors.GREEN_900,
                offset=ft.Offset(0, 0),
            )
        )

        # Climate Control Section
        # Climate Control Section
        self.controls_view = ControlsView(page, self.auth_service, self.mqtt_client, on_refresh=self.refresh_data)

        # Vehicle Image / Tire Pressure Section
        # This mirrors the bottom of the mockup
        self.tire_section_container = ft.Container(
            content=ft.Column([
                ft.Text("TIRE PRESSURE", size=12, weight="bold", color=ft.Colors.WHITE_70),
                ft.Container(height=10),
                # Use a specific layout for tires: 
                # L Top   R Top
                #    [CAR]
                # L Bot   R Bot
                # For now, sticking to the Grid but styling it better
                self.tires_grid
            ]),
            padding=20,
            border_radius=15,
            bgcolor=ft.Colors.WHITE_10,
            border=ft.Border.all(1, ft.Colors.WHITE_10)
        )

        # Assemble Main Layout
        self.hero_section = ft.Container(
            content=ft.Column([
                header_row,
                ft.Container(height=20),
                battery_indicator,
                ft.Container(height=30),
                self.charging_card,
                ft.Container(height=10),
                # Climate Control is injected via ControlsView
                self.controls_view, 
                ft.Container(height=10),
                self.tire_section_container,
                ft.Container(height=10),
                ft.Row([
                    self.status_text,
                    self.last_updated
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.only(top=50, left=20, right=20, bottom=20),
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_CENTER,
                end=ft.Alignment.BOTTOM_CENTER,
                colors=["#1a1b1e", "#000000"]
            )
        )
        
        # Main Layout with ListView
        self.list_view = ft.ListView(
            expand=True,
            padding=0,
            controls=[
                self.hero_section
            ]
        )

        self.content = self.list_view

    def did_mount(self):
        # Start connection in background
        self.page.run_task(self.connect_and_subscribe)
        # Start auto-refresh
        self.running = True
        self.page.run_task(self.auto_refresh_loop)

    def auto_refresh_loop(self):
        import asyncio
        while self.running:
            # Wait 60 seconds
            import time
            time.sleep(60) 
            # ideally use asyncio.sleep but run_task might be threaded or async. 
            # If run_task expects a coroutine, we should use await asyncio.sleep
            # Let's assume it supports async since connect_and_subscribe is async.
            # But wait, did_mount is sync. 
            # Correction: Flet run_task handles both. Let's make this async to be safe and non-blocking.
            if self.running and self.is_connected:
                # We need to call refresh_data which is async.
                # Since we are likely in a threaded wrapper or async task, we need to be careful.
                # self.refresh_data accepts an event 'e', we can pass None.
                # However, calling async from sync or vice-versa...
                # Let's re-write this whole method to be async.
                pass

    async def auto_refresh_loop(self):
        while self.running:
            await asyncio.sleep(60)
            if self.running:
                print("DEBUG: Auto-refresh triggered")
                await self.refresh_data(None)

    def will_unmount(self):
        self.running = False
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
            topic_dashboard = f"$aws/things/thing_{vin}/shadow/name/DASHBOARD_ASYNC/update"
            self.mqtt_client.subscribe(topic_dashboard)
            
            # Subscribe to Engine Status (for immediate command feedback)
            topic_engine = f"$aws/things/thing_{vin}/shadow/name/ENGINE_START_STOP_ASYNC/update"
            self.mqtt_client.subscribe(topic_engine)
            
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
            elif "ENGINE_START_STOP_ASYNC" in topic:
                print(f"DEBUG: Engine Status Update: {payload}")
                # Potentially update status/SNACKBAR here
                
        except Exception as e:
            print(f"Error parsing MQTT message: {e}")

    async def _do_refresh(self):
        try:
            if not self.is_connected:
                pass
            
            # Use captured loop or get new one
            loop = getattr(self, 'loop', asyncio.get_running_loop())
            
            def request_task():
                # Dashboard async request
                HondaApi.request_dashboard(
                    self.auth_service.access_token,
                    self.auth_service.selected_vin
                )
                
                # Fetch Climate Status (Sync/Direct)
                try:
                    climate_data = HondaApi.get_climate_status(
                        self.auth_service.access_token,
                        self.auth_service.selected_vin
                    )
                    # We can update climate status directly here or pass it to a handler
                    # Since we are in a thread, we should schedule a UI update
                    if climate_data:
                         # Schedule UI update for climate
                         def update_climate_ui():
                             self.controls_view.update_climate_status(climate_data)
                         
                         if getattr(self, 'loop', None):
                             self.loop.call_soon_threadsafe(update_climate_ui)
                             
                except Exception as e:
                    print(f"Climate Status Error: {e}")

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
            # Update Progress Ring (0.0 to 1.0)
            try:
                self.battery_ring.value = float(battery) / 100.0
            except:
                self.battery_ring.value = 0.0
        if range_val is not None:
            self.range_text.value = f"{range_val} miles"
            
        # Update Target Charge Level if available (optional display)
    def open_charge_settings(self, e):
        # Default value
        current_target = 80
        
        def on_slider_change(e):
            label.value = f"{int(e.control.value)}%"
            label.update()
            
        slider = ft.Slider(min=50, max=100, divisions=10, value=current_target, label="{value}%", on_change=on_slider_change)
        label = ft.Text(f"{current_target}%", size=20, weight="bold")
        
        def close_dlg(e):
            dlg.open = False
            self.main_page.update()
            
        def save_target(e):
            target = int(slider.value)
            close_dlg(e)
            
            # Helper to run async API call
            async def run_update():
                snack = ft.SnackBar(ft.Text(f"Setting charge limit to {target}%..."))
                self.main_page.overlay.append(snack)
                snack.open = True
                self.main_page.update()
                
                try:
                    def api_call():
                         return HondaApi.request_set_charge_target(
                            self.auth_service.access_token,
                            self.auth_service.selected_vin,
                            None, # PIN not strictly required for this specific call in some regions, or we might need to prompt
                            target
                        )
                    
                    # Run in executor
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, api_call)
                    
                    snack.open = False
                    success_snack = ft.SnackBar(ft.Text("Charge limit updated!"), bgcolor="green")
                    self.main_page.overlay.append(success_snack)
                    success_snack.open = True
                    self.main_page.update()
                    
                    # Refresh data
                    await self._do_refresh()
                    
                except Exception as ex:
                    snack.open = False
                    err_snack = ft.SnackBar(ft.Text(f"Failed to update: {ex}"), bgcolor="red")
                    self.main_page.overlay.append(err_snack)
                    err_snack.open = True
                    self.main_page.update()

            # Execute async task
            # self.page.run_task(run_update) # page.run_task not available, use create_task
            loop = asyncio.get_running_loop()
            loop.create_task(run_update())

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Set Charge Limit"),
            content=ft.Column([
                ft.Text("Select target charge percentage:"),
                ft.Row([slider, label], alignment=ft.MainAxisAlignment.CENTER),
            ], height=100, tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.TextButton("Update", on_click=save_target),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.main_page.overlay.append(dlg)
        dlg.open = True
        self.main_page.update()

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
            # Update Progress Ring (0.0 to 1.0)
            try:
                self.battery_ring.value = float(battery) / 100.0
            except:
                self.battery_ring.value = 0.0
        if range_val is not None:
            self.range_text.value = f"{range_val} miles"
            
        if range_val is not None:
            self.range_text.value = f"{range_val} miles"
            
        # Update Target Charge Level if available (optional display)
        # target_level = charge_mode.get("generalAwayTargetChargeLevel", {}).get("value")

        # Charging status & type

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
             
        self.charge_status_text.value = " ".join(status_parts) if status_parts else "Not Plugged In"

        # Update Charging Card Styling
        # Default to inactive (Grey)
        card_border_color = ft.Colors.GREY_800
        card_shadow_color = ft.Colors.TRANSPARENT
        text_color = ft.Colors.GREY_400
        icon_color = ft.Colors.GREY_700
        
        is_plugged_in = plug_status in ["plugged", "CONNECTED", "connected"] or \
                        (charge_status and charge_status.lower() in ["charging", "plugged", "connected"])
        
        if is_plugged_in:
            card_border_color = ft.Colors.GREEN_400
            card_shadow_color = ft.Colors.GREEN_900
            text_color = ft.Colors.GREEN_400
            icon_color = ft.Colors.GREEN_400
        
        # Update styling elements
        self.charging_card.border = ft.Border.all(1, card_border_color)
        self.charging_card.shadow.color = card_shadow_color
        self.charge_status_text.color = text_color
        # Update icon in charging card (first icon in column -> row -> icon)
        try:
             # structure: Container -> Column -> Row -> [Text, Container, Icon]
             self.charging_card.content.controls[0].controls[2].color = icon_color
             # structure: Container -> Column -> Row (2nd) -> [Text, Container, Icon]
             self.charging_card.content.controls[2].controls[2].color = icon_color
        except Exception as e:
            print(f"Error updating charging card icons: {e}")

        self.charging_card.update()

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
        
        # Climate Status
        # Path: evStatus -> cabinPreconditioningTempCustomSetting (maybe?) 
        # OR getChargeMode -> cabinPrecondRequest (Found in dump: "OFF")
        climate_status = "Unknown"
        if "getChargeMode" in rb:
             val = rb["getChargeMode"].get("cabinPrecondRequest", {}).get("value")
             if val:
                 climate_status = val
        
        self.controls_view.update_climate_status(climate_status)

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

