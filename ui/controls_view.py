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
        
        self.txt_value = ft.Text(f"{self.current_value}{self.unit}", size=40, weight=ft.FontWeight.BOLD)
        
        self.btn_minus = ft.IconButton(icon=ft.icons.Icons.REMOVE, icon_size=30, on_click=self.minus_click)
        self.btn_plus = ft.IconButton(icon=ft.icons.Icons.ADD, icon_size=30, on_click=self.plus_click)
        
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

class ControlsView(ft.Card):
    def __init__(self, page, auth_service: AuthService, mqtt_client):
        super().__init__()
        self.main_page = page
        print(f"DEBUG: ControlsView init with page: {page}")
        self.auth_service = auth_service
        self.mqtt_client = mqtt_client
        
        # Modern Counter Controls
        self.temp_control = CounterControl(value=72, min_value=57, max_value=87, step=1, unit="°F")
        self.charge_control = CounterControl(value=80, min_value=50, max_value=100, step=10, unit="%") 
        
        # self.climate_status_text = ft.Text("Status: --", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_400)

        # Climate Controls
        climate_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Climate Control", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(height=10), # Spacer
                    self.temp_control,
                    ft.Container(height=10), # Spacer
                    ft.Row([
                        ft.ElevatedButton("Start Climate", icon="thermostat", on_click=lambda _: self.confirm_action("Start Climate", self.start_climate)),
                        ft.ElevatedButton("Stop Climate", icon="power_settings_new", on_click=lambda _: self.confirm_action("Stop Climate", self.stop_climate))
                    ], alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=5),
                padding=20
            )
        )

        # Charge Control
        charge_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Charging", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(height=10), # Spacer
                    ft.Text("Max Charge Target"),
                    self.charge_control,
                    ft.Container(height=10), # Spacer
                    ft.ElevatedButton("Set Charge Limit", icon="battery_charging_full", on_click=lambda _: self.confirm_action("Set Charge Limit", self.set_charge_target, require_pin=False))
                ], spacing=5),
                padding=20
            )
        )

        self.content = ft.Column([
            climate_card,
            # remote_card,
            charge_card
        ], spacing=10, scroll=ft.ScrollMode.AUTO)

    def confirm_action(self, action_name, action_callback, require_pin=True):
        print(f"DEBUG: confirm_action triggered for {action_name}")
        
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
            self.main_page.run_task(self.perform_action, action_name, action_callback, pin)

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

    async def _prefill_pin(self, pin_input):
        stored_pin = await self.auth_service.storage.get("honda_pin")
        if stored_pin:
            pin_input.value = stored_pin
            self.main_page.update()

    async def perform_action(self, name, callback, pin):
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
        else:
             snack = ft.SnackBar(ft.Text(f"{name} failed: {error}"), bgcolor="red")
            
        # self.main_page.snack_bar = snack
        # self.main_page.snack_bar.open = True
        self.main_page.overlay.append(snack)
        snack.open = True
        self.main_page.update()

    def start_climate(self, pin):
        temp = int(self.temp_control.value)
        # TODO: integrate with MQTT client to listen for success?
        # For now just fire and forget the HTTP request as per `api.py`
        # Ideally we wait for MQTT confirmation like in Node.js version.
        # But for basics, this works. Api.request_start_climate returns request ID.
        res = HondaApi.request_start_climate(
            self.auth_service.access_token,
            self.auth_service.selected_vin,
            pin,
            temp
        )

    def stop_climate(self, pin):
        res = HondaApi.request_stop_climate(
            self.auth_service.access_token,
            self.auth_service.selected_vin,
            pin,
            72 # Dummy temp
        )

    # Removed non-functional buttons logic

    def set_charge_target(self, pin):
        target = int(self.charge_control.value)
        HondaApi.request_set_charge_target(
            self.auth_service.access_token,
            self.auth_service.selected_vin,
            pin,
            target
        )

    def update_climate_status(self, status):
        pass
        # self.climate_status_text.value = f"Status: {status}"
        # if status.upper() == "ON":
        #     self.climate_status_text.color = ft.Colors.GREEN_400
        # elif status.upper() == "OFF":
        #      self.climate_status_text.color = ft.Colors.GREY_400
        # else:
        #      self.climate_status_text.color = ft.Colors.ORANGE_400
        # self.climate_status_text.update()
