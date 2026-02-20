# Logue

Logue is a mobile-first companion application for Honda EV owners (specifically tested with the Honda Prologue). It provides real-time dashboard data and offers a streamlined, Flet-based alternative to official apps.

## Credits & Inspiration
This project stands on the shoulders of giants:
- **[honstar-mqtt](https://github.com/tsightler/honstar-mqtt)**: A critical resource for understanding the Honda/Acura API and MQTT integration via AWS IoT Core.
- **[Relink](https://get-relink.app/)**: An iOS app by reddit user **ThierryBuc** that served as as inspiration for this project.


## Features

### Real-Time Dashboard
- **Battery & Range**: Instant visibility into State of Charge (SoC) and remaining EV range.
- **Charging Status**: Detailed information on plug status, complete charging power data (e.g., 120V at 12A), and charge completion ETA formatted in 12-hour AM/PM time.
- **Tire Pressures**: Real-time PSI monitoring for all four tires.
- **Odometer**: Current vehicle mileage tracking.

### Remote Controls
- **Climate Control**: Start/stop climate control and view current status.
- **Vehicle Security**: Remote lock and unlock functionality.
- **Lights & Horn**: Trigger vehicle lights and horn remotely.
- **Secure PIN Access**: Remote commands are protected by your vehicle's PIN.

## Tech Stack
- **Framework**: [Flet](https://flet.dev/) (Flutter for Python)
- **Communication**: MQTT (AWS IoT Core) for real-time updates
- **Backend API**: Integration with Honda/Acura Identity and Web Services

## Installation & Setup

### Option 1: Install the Android APK (Recommended)
The easiest way to get Logue on your device is to download the latest release:
1.  Navigate to the **[Releases](https://github.com/mcspencehouse/logue-app/releases)** page of this repository.
2.  Download the `logue-X.X.X.apk` file to your Android device.
3.  Open the file and follow the prompts to install. 
    *Note: You may need to enable "Install from unknown sources" in your device settings.*

### Option 2: Building from Source (Advanced)
If you prefer to run the app in development mode or build your own APK:

#### Prerequisites
- Python 3.9+
- [Flet CLI](https://flet.dev/docs/guides/python/deploying-apps/android/) (if building for Android)

#### Setup
1. **Clone the repository**:
   ```bash
   git clone https://github.com/mcspencehouse/logue-app.git
   cd logue-app
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run locally**:
   ```bash
   flet run main.py
   ```
   *Note: On first run, the app will automatically generate a secure `ENCRYPTION_KEY` and default configuration in a `.env` file.*

4. **Build your own APK**:
   ```bash
   flet build apk
   ```

## Security & Privacy

**Logue is designed with a "Privacy First" architecture:**

- **Zero External Tracking**: This application does not send your data, login credentials, or vehicle information to any third-party infrastructure. All communication is directly between the app and the official Honda/Acura API.
- **Local Credential Storage**: Your HondaLink credentials and vehicle PIN are stored exclusively on your device. We use Android's native `SharedPreferences` for storage.
- **Encryption**: Sensitive data (passwords, PINs) are encrypted using **Fernet (AES-128)** symmetric encryption before being saved locally. 
- **Environment Security**: The encryption key is sourced from your local `.env` file, ensuring that your data remains unreadable even if the storage files are accessed on the device.

> **Note on Client Secrets**: This application uses a default Honda client ID/secret to emulate the official mobile app. While this is standard for third-party clients, advanced users may wish to provide their own credentials in the `.env` file.

## Development Note

This project was developed using a "vibe coding" approach—leveraging advanced AI pair programming to rapidly iterate and implement complex vehicle integration logic. While AI-assisted, the focus remains on technical reliability and a clean user experience.

## Build and Versioning

The app is configured via `pyproject.toml` and `flet.yaml` for Android compilation. For APK generation, ensure you have the Flet CLI installed.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Disclaimer: This app is not affiliated with American Honda Motor Co., Inc. Use remote commands responsibly.*
