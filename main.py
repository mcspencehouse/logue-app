import flet as ft
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

from service.auth import AuthService
from ui.login_view import LoginView
from ui.dashboard_view import DashboardView

async def main(page: ft.Page):
    page.title = "Logue"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = ft.Colors.BLACK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    # Initialize Secure Storage
    storage = page.shared_preferences
    
    auth_service = AuthService(page, storage)
    
    async def on_login_success():
        page.clean()
        page.add(ft.Text("Login Successful! Loading Dashboard...", size=20))
        page.update()
        
        dashboard = DashboardView(page, auth_service, on_logout=on_logout)
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.START
        page.add(dashboard)
        page.update()

    async def on_logout():
        await auth_service.logout()
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.START
        login_view = LoginView(page, auth_service, on_login_success)
        page.add(login_view)
        page.update()

    # Create loading view
    loading_ring = ft.ProgressRing()
    loading_text = ft.Text("Checking login status...", size=16)
    loading_view = ft.Column(
        [loading_ring, loading_text],
        horizontal_alignment="center",
        alignment="center"
    )
    
    page.add(loading_view)
    page.update()

    # Check for stored credentials
    username, password, vin, pin = await auth_service.load_credentials()
    
    if username and password:
        loading_text.value = f"Welcome back, {username}. Logging in..."
        page.update()
        
        # Run login in thread to avoid blocking UI
        import asyncio
        loop = asyncio.get_running_loop()
        success, message = await loop.run_in_executor(None, lambda: auth_service.login(username, password, vin=vin))
        
        if success:
            await on_login_success()
            return

    # Fallback to LoginView
    page.clean()
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.START
    login_view = LoginView(page, auth_service, on_login_success)
    page.add(login_view)
    page.update()
if __name__ == "__main__":
    ft.run(main)
