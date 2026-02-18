import flet as ft
from service.auth import AuthService

class LoginView(ft.Container):
    def __init__(self, page, auth_service: AuthService, on_login_success):
        super().__init__()
        # self.page = page  <-- This property is read-only in Flet Controls
        self.auth_service = auth_service
        self.on_login_success = on_login_success
        
        # self.auth_service.load_credentials() # Moved to did_mount
        
        self.username_input = ft.TextField(label="Username")
        self.password_input = ft.TextField(label="Password", password=True, can_reveal_password=True)
        self.vin_input = ft.TextField(label="VIN (Optional)", hint_text="Leave empty to auto-select first vehicle")
        
        self.error_text = ft.Text(color="red")
        self.login_button = ft.FilledButton("Login", on_click=self.handle_login)
        self.progress_ring = ft.ProgressRing(visible=False)

        # Content setup (Moved from build)
        self.content = ft.Column(
            controls=[
                ft.Text("HondaStink Login", size=30, weight="bold"),
                self.username_input,
                self.password_input,
                self.vin_input,
                ft.Row([self.login_button, self.progress_ring], alignment="center"),
                self.error_text
            ],
            horizontal_alignment="center",
            spacing=20
        )
        self.padding = 50
        self.alignment = ft.Alignment(0, 0)

    def did_mount(self):
        # Load credentials asynchronously
        self.page.run_task(self.load_creds)

    async def load_creds(self):
        username, password, vin, pin = await self.auth_service.load_credentials()
        self.username_input.value = username or ""
        self.password_input.value = password or ""
        self.vin_input.value = vin or ""
        self.update()

    def handle_login(self, e):
        self.page.run_task(self._do_login)

    async def _do_login(self):
        self.error_text.value = ""
        self.login_button.disabled = True
        self.progress_ring.visible = True
        self.update()
        
        username = self.username_input.value
        password = self.password_input.value
        vin = self.vin_input.value
        
        if not username or not password:
            self.error_text.value = "Username and Password are required"
            self.login_button.disabled = False
            self.progress_ring.visible = False
            self.update()
            return

        # Login is synchronous (requests), so we run it in an executor to avoid blocking the UI
        import asyncio
        loop = asyncio.get_running_loop()
        
        def login_task():
            return self.auth_service.login(username, password, vin)
            
        success, message = await loop.run_in_executor(None, login_task)
        
        if success:
            # Check if VIN provided matches found vehicles, else use first
            if vin:
               # basic check
               found = False
               for v in self.auth_service.vehicles:
                   if v.get('VIN') == vin:
                       self.auth_service.selected_vin = vin
                       found = True
                       break
               if not found:
                   message = f"Warning: VIN {vin} not found, using {self.auth_service.selected_vin}"
                   # Update the input to reflect reality
                   vin = self.auth_service.selected_vin

            # Save credentials (PIN is no longer used but kept in storage contract)
            await self.auth_service.save_credentials(username, password, self.auth_service.selected_vin, None)
            
            await self.on_login_success()
        else:
            self.error_text.value = f"Login Failed: {message}"
            self.login_button.disabled = False
            self.progress_ring.visible = False
            self.update()
