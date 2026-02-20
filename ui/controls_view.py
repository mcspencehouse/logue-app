import flet as ft
from service.api import HondaApi
import threading
from service.auth import AuthService

class CounterControl(ft.Row):
    def __init__(self, value, min_value, max_value, step, unit, on_change=None):
        super().__init__()
        self.current_value = value
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.unit = unit
        self.on_change = on_change
        self.alignment = ft.MainAxisAlignment.CENTER
        self.vertical_alignment = ft.CrossAxisAlignment.CENTER
        self.spacing = 20
        
        self.txt_value = ft.Text(f"{self.current_value}{self.unit}", size=30, weight="bold", color=ft.Colors.WHITE)
        
        self.btn_minus = ft.IconButton(icon=ft.icons.Icons.REMOVE_CIRCLE_OUTLINE, icon_color=ft.Colors.WHITE_54, icon_size=30, on_click=self.minus_click)
        self.btn_plus = ft.IconButton(icon=ft.icons.Icons.ADD_CIRCLE_OUTLINE, icon_color=ft.Colors.WHITE_54, icon_size=30, on_click=self.plus_click)
        
        self.controls = [self.btn_minus, self.txt_value, self.btn_plus]
        
    def minus_click(self, e):
        if self.current_value > self.min_value:
            self.current_value -= self.step
            self.update_display()

    def plus_click(self, e):
        if self.current_value < self.max_value:
            self.current_value += self.step
            self.update_display()
            
    def update_display(self):
        self.txt_value.value = f"{self.current_value}{self.unit}"
        self.txt_value.update()
        if self.on_change:
            self.on_change(self.current_value)

    @property
    def value(self):
        return self.current_value

class ControlsView(ft.Column): # Changed from Card to Column for transparency
    def __init__(self, page, auth_service: AuthService, mqtt_client, on_refresh=None):
        super().__init__()
        self.main_page = page
        self.auth_service = auth_service
        self.mqtt_client = mqtt_client
        self.on_refresh = on_refresh
        self.current_climate_status = "OFF"
        self.spacing = 15
        
        # Modern Counter Controls
        self.temp_control = CounterControl(value=72, min_value=57, max_value=87, step=1, unit="°F")
        
        # Helper to create styled action buttons


        # Climate Controls Section
        climate_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.Icons.THERMOSTAT, color=ft.Colors.CYAN_200),
                    ft.Text("CLIMATE CONTROL", size=12, weight="bold", color=ft.Colors.WHITE_70)
                ]),
                ft.Container(height=10),
                self.temp_control,
                ft.Container(height=10),
                ft.Row([
                    self._create_action_button("ON", ft.icons.Icons.POWER_SETTINGS_NEW, ft.Colors.CYAN_400, self._handle_start_click),
                    self._create_action_button("OFF", ft.icons.Icons.POWER_OFF, ft.Colors.RED_900, self._handle_stop_click)
                ], spacing=10)
            ]),
            padding=20,
            border_radius=15,
            bgcolor=ft.Colors.WHITE_10,
            border=ft.Border.all(1, ft.Colors.WHITE_10)
        )

        # Vehicle Remote Controls Section
        remote_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.Icons.SMARTPHONE, color=ft.Colors.AMBER_300),
                    ft.Text("REMOTE COMMANDS", size=12, weight="bold", color=ft.Colors.WHITE_70)
                ]),
                ft.Container(height=10),
                ft.Row([
                    self._create_action_button("LOCK", ft.icons.Icons.LOCK, ft.Colors.ORANGE_800, self._handle_lock_click),
                    self._create_action_button("UNLOCK", ft.icons.Icons.LOCK_OPEN, ft.Colors.GREEN_700, self._handle_unlock_click),
                ], spacing=10),
                ft.Container(height=10),
                ft.Row([
                    self._create_action_button("LIGHTS", ft.icons.Icons.LIGHTBULB_CIRCLE, ft.Colors.AMBER_600, self._handle_lights_click),
                    self._create_action_button("HORN", ft.icons.Icons.CAMPAIGN, ft.Colors.RED_700, self._handle_horn_click)
                ], spacing=10)
            ]),
            padding=20,
            border_radius=15,
            bgcolor=ft.Colors.WHITE_10,
            border=ft.Border.all(1, ft.Colors.WHITE_10)
        )



        self.controls = [
            remote_section,
            climate_section
        ]

    def _create_action_button(self, text, icon, color, on_click):
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, color=ft.Colors.WHITE),
                ft.Text(text, weight="bold", color=ft.Colors.WHITE)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
            on_click=on_click,
            bgcolor=color,
            padding=15,
            border_radius=10,
            expand=True,
            ink=True
        )

    def _show_confirm_dialog(self, action_name, action_callback, require_pin=True):
        
        content_controls = [ft.Text("Please confirm to execute this command.")]
        pin_input = None

        if require_pin:
            pin_input = ft.TextField(label="Enter PIN", password=True, max_length=4, keyboard_type=ft.KeyboardType.NUMBER, autofocus=True)
            content_controls.append(pin_input)
        
        def close_dlg(e):
            print(f"DEBUG: Closing dialog for {action_name}")
            dlg.open = False
            self.main_page.update()
            # self.main_page.overlay.remove(dlg) # Optional cleanup, likely safe to leave or remove later

        def submit_action(e):
            pin = pin_input.value if pin_input else None
            print(f"DEBUG: submit_action for {action_name}, PIN present: {bool(pin)}")
            
            if require_pin and not pin:
                return
                
            close_dlg(e)
            # Run async action
            target = self._get_target_status(action_name)
            self.main_page.run_task(self.perform_action, action_name, action_callback, pin, target)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Confirm {action_name}"),
            content=ft.Column(content_controls, height=100 if require_pin else 50),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.TextButton("Execute", on_click=submit_action),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # Use overlay as fallback since page.open/page.dialog are missing
        self.main_page.overlay.append(dlg)
        dlg.open = True
        self.main_page.update()
        
        # Pre-fill if available in auth service storage
        if require_pin:
            self.main_page.run_task(self._prefill_pin, pin_input)

    # Helper to deduce target status
    def _get_target_status(self, action_name):
        if "Start" in action_name: return "ON"
        if "Stop" in action_name: return "OFF"
        return None

    async def _prefill_pin(self, pin_input):
        stored_pin = await self.auth_service.storage.get("honda_pin")
        if stored_pin:
            pin_input.value = stored_pin
            self.main_page.update()

    async def perform_action(self, name, callback, pin, target_status=None):
        # Show loading
        loading_snack = ft.SnackBar(ft.Text(f"Sending {name} command..."), duration=30000) # Long duration until replaced
        self.main_page.overlay.append(loading_snack)
        loading_snack.open = True
        self.main_page.update()
        
        # Run blocking API call in executor to avoid freezing UI
        # HondaApi uses requests which is blocking.
        # Check if callback is async. It's currently sync.
        
        def thread_target():
             try:
                # Ensure we have VIN and Token
                if not self.auth_service.access_token:
                    raise Exception("Not authenticated")
                callback(pin)
                return True, None
             except Exception as e:
                print(f"DEBUG: perform_action error: {e}")
                return False, str(e)
                
        # Run in thread
        import asyncio
        loop = asyncio.get_running_loop()
        success, error = await loop.run_in_executor(None, thread_target)
        
        # Close loading snackbar
        loading_snack.open = False
        
        if success:
             snack = ft.SnackBar(ft.Text(f"{name} command sent successfully!"), bgcolor="green")
             # Start aggressive polling to update status
             if self.on_refresh:
                 self.main_page.run_task(self.start_polling, target_status)
        else:
             snack = ft.SnackBar(ft.Text(f"{name} failed: {error}"), bgcolor="red")
            
        # self.main_page.snack_bar = snack
        # self.main_page.snack_bar.open = True
        self.main_page.overlay.append(snack)
        snack.open = True
        self.main_page.update()

    async def start_polling(self, target_status=None):
        import asyncio
        print(f"DEBUG: Starting aggressive polling. Target: {target_status}, Current: {self.current_climate_status}")
        # Poll every 5 seconds for 60 seconds
        for i in range(12):
            # Check if we reached target before waiting
            if target_status and self.current_climate_status == target_status:
                print(f"DEBUG: Target status '{target_status}' reached. Stopping polling.")
                break

            await asyncio.sleep(5)
            
            # Check after waiting (and before refreshing again, though we usually refresh to get new status)
            # Actually we refresh then check. But since this is a loop:
            # Wait -> Refresh -> Check (in next iteration or here?)
            # The refresh updates 'current_climate_status' via 'update_climate_status' method.
            # So we check *after* refresh.
            
            print(f"DEBUG: Polling attempt {i+1}/12")
            if self.on_refresh:
                await self.on_refresh(None)
            
            # Allow a small delay for the refresh to process and update state?
            # Since on_refresh is awaited and calls update_climate_status synchronously (likely), 
            # we should be up to date here.
            
            if target_status and self.current_climate_status == target_status:
                print(f"DEBUG: Target status '{target_status}' reached. Stopping polling.")
                break

    def _handle_start_click(self, e):
        self._show_confirm_dialog("Start Climate", self.start_climate)

    def _handle_stop_click(self, e):
        self._show_confirm_dialog("Stop Climate", self.stop_climate)

    def _handle_lights_click(self, e):
        self._show_confirm_dialog("Flash Lights", self.flash_lights)

    def _handle_horn_click(self, e):
        self._show_confirm_dialog("Sound Horn", self.sound_horn)

    def _handle_lock_click(self, e):
        self._show_confirm_dialog("Lock Doors", self.lock_doors)

    def _handle_unlock_click(self, e):
        self._show_confirm_dialog("Unlock Doors", self.unlock_doors)

    def start_climate(self, pin):
        temp = int(self.temp_control.value)
        return HondaApi.request_start_climate(
            self.auth_service.access_token,
            self.auth_service.selected_vin,
            pin,
            temp
        )

    def stop_climate(self, pin):
        return HondaApi.request_stop_climate(
            self.auth_service.access_token,
            self.auth_service.selected_vin,
            pin,
            72 # Dummy temp
        )

    def flash_lights(self, pin):
        return HondaApi.request_light_horn(
            self.auth_service.access_token,
            self.auth_service.selected_vin,
            pin,
            "lgt"
        )

    def sound_horn(self, pin):
        return HondaApi.request_light_horn(
            self.auth_service.access_token,
            self.auth_service.selected_vin,
            pin,
            "hrn"
        )

    def lock_doors(self, pin):
        return HondaApi.request_door_lock(
            self.auth_service.access_token,
            self.auth_service.selected_vin,
            pin,
            "alk"
        )

    def unlock_doors(self, pin):
        return HondaApi.request_door_lock(
            self.auth_service.access_token,
            self.auth_service.selected_vin,
            pin,
            "dulk"
        )

    # Removed non-functional buttons logic

    def update_climate_status(self, data):

        
        status_text = "OFF"
        is_on = False
        
        try:
             # Case 1: Direct dictionary with 'climateStatus' (Observed in logs)
             # {'vin': '...', 'climateStatus': 'OFF', ...}
             if isinstance(data, dict):
                 climate_status = data.get("climateStatus")
                 if climate_status:
                     if climate_status.upper() != "OFF":
                         status_text = climate_status.upper()
                         is_on = True
                     else:
                         status_text = "OFF"
                         is_on = False
                 
                 # Fallback: check nested success/started (Legacy/Hypothetical)
                 elif data.get("status") == "success":
                     # No specific parsing for this yet as we haven't seen it for this endpoint
                     pass

             # Case 2: Simple string
             elif isinstance(data, str):
                 if data.upper() != "OFF":
                     status_text = data.upper()
                     is_on = True

        except Exception as e:
            print(f"Error parsing climate status: {e}")
        
        # Update internal state
        self.current_climate_status = status_text

        # Update UI in Climate Section
        try:
            # Safely find the header row
            if not self.controls:
                print("DEBUG: No controls in ControlsView")
                return

            climate_container = self.controls[0]
            if not isinstance(climate_container, ft.Container):
                print("DEBUG: First control is not Container")
                return
                
            climate_column = climate_container.content
            if not isinstance(climate_column, ft.Column):
                print("DEBUG: Container content is not Column")
                return
                
            # Finding header row (should be first control in column)
            header_row = None
            if climate_column.controls:
                header_row = climate_column.controls[0]
            
            if not isinstance(header_row, ft.Row):
                print("DEBUG: First item in Column is not Row")
                return

            # Update elements
            icon = header_row.controls[0]
            title_text = header_row.controls[1]
            
            if is_on:
                title_text.value = f"CLIMATE CONTROL: {status_text}"
                title_text.color = ft.Colors.GREEN_400
                icon.color = ft.Colors.GREEN_400
            else:
                 title_text.value = "CLIMATE CONTROL: OFF"
                 title_text.color = ft.Colors.WHITE_70
                 icon.color = ft.Colors.CYAN_200
            
            title_text.update()
            icon.update()
            
        except Exception as e:
            print(f"Error updating climate UI: {e}")

