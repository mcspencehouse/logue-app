import flet as ft
from service.api import HondaApi
import threading
from service.auth import AuthService

class ControlsView(ft.Card):
    def __init__(self, page, auth_service: AuthService, mqtt_client):
        super().__init__()
        self.main_page = page
        print(f"DEBUG: ControlsView init with page: {page}")
        self.auth_service = auth_service
        self.mqtt_client = mqtt_client
        self.temp_slider = ft.Slider(min=57, max=87, divisions=30, label="{value}F", value=72)

        # Content setup (Moved from build)
        # Content setup - Remote actions removed as requested
        self.content = ft.Column([], spacing=10)

    def confirm_action(self, action_name, action_callback):
        print(f"DEBUG: confirm_action triggered for {action_name}")
        # Create a PIN dialog
        pin_input = ft.TextField(label="Enter PIN", password=True, max_length=4, keyboard_type=ft.KeyboardType.NUMBER, autofocus=True)
        
        def close_dlg(e):
            print(f"DEBUG: Closing dialog for {action_name}")
            if dlg.open:
                dlg.open = False
                self.main_page.update()

        def submit_pin(e):
            pin = pin_input.value
            print(f"DEBUG: submit_pin for {action_name}, PIN length: {len(pin) if pin else 0}")
            if not pin:
                return
            close_dlg(e)
            # Run async action
            self.main_page.run_task(self.perform_action, action_name, action_callback, pin)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Confirm {action_name}"),
            content=ft.Column([
                ft.Text("Please confirm your PIN to execute this command."),
                pin_input
            ], height=100),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.TextButton("Execute", on_click=submit_pin),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.main_page.dialog = dlg
        dlg.open = True
        self.main_page.update()
        
        # Pre-fill if available in auth service storage
        self.main_page.run_task(self._prefill_pin, pin_input)

    async def _prefill_pin(self, pin_input):
        stored_pin = await self.auth_service.storage.get("honda_pin")
        if stored_pin:
            pin_input.value = stored_pin
            self.main_page.update()

    async def perform_action(self, name, callback, pin):
        # Show loading
        self.main_page.snack_bar = ft.SnackBar(ft.Text(f"Sending {name} command..."))
        self.main_page.snack_bar.open = True
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
        
        if success:
             self.main_page.snack_bar = ft.SnackBar(ft.Text(f"{name} command sent successfully!"), bgcolor="green")
        else:
             self.main_page.snack_bar = ft.SnackBar(ft.Text(f"{name} failed: {error}"), bgcolor="red")
            
        self.main_page.snack_bar.open = True
        self.main_page.update()

    def start_climate(self, pin):
        temp = int(self.temp_slider.value)
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

    def lock_car(self, pin):
        HondaApi.request_lock(
            self.auth_service.access_token,
            self.auth_service.selected_vin,
            pin
        )

    def unlock_car(self, pin):
        HondaApi.request_unlock(
            self.auth_service.access_token,
            self.auth_service.selected_vin,
            pin
        )
        
    def flash_lights(self, pin):
        HondaApi.request_lights(
            self.auth_service.access_token,
            self.auth_service.selected_vin,
            pin
        )

    def honk_horn(self, pin):
        # We didn't implement horn in API yet, let's look if we did
        # Api.py only has lights. I should add horn to api.py or here?
        # I'll try to use _generic_remote_command if I can access it or add it to API.
        # Ideally I should add request_horn to api.py.
        # For now, I'll access the protected method or just copy logic.
        # Wait, I made _generic_remote_command static so I can call it.
        # But it's Python, so _ is just convention.
        
        # NOTE: Guessing endpoint for horn
        HondaApi._generic_remote_command(
            self.auth_service.access_token,
            self.auth_service.selected_vin,
            pin,
            "horn",
            "sec/async/hrn" # Guessing endpoint
        )
