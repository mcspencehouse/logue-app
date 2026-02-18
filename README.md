# Logue

Logue is a mobile-first companion application for Honda EV owners (specifically tested with the Honda Prologue). It provides real-time dashboard data and offers a streamlined, Flet-based alternative to official apps.

## Credits & Inspiration
This project stands on the shoulders of giants:
- **[honstar-mqtt](https://github.com/tsightler/honstar-mqtt)**: A critical resource for understanding the Honda/Acura API and MQTT integration via AWS IoT Core.
- **[Relink](https://get-relink.app/)**: An iOS app by reddit user **ThierryBuc** that served as as inspiration for this project.


## Features

### Real-Time Dashboard
- **Battery & Range**: Instant visibility into State of Charge (SoC) and remaining EV range.
- **Charging Status**: Detailed information on plug status, charging voltage (120V/240V), and charge completion ETA.
- **Tire Pressures**: Real-time PSI monitoring for all four tires.
- **Odometer**: Current vehicle mileage tracking.

### Remote Controls (Work in Progress ⚠️)
*Please note: Remote control features are currently under development and not yet available in the public build.*
- **Climate Control**: Start/stop charging and set preferred cabin temperature.
- **Vehicle Security**: Remote lock and unlock functionality.
- **Convenience**: Flash lights and honk horn for vehicle location.
- **Secure PIN Access**: Remote commands are protected by your vehicle's PIN.

## Tech Stack
- **Framework**: [Flet](https://flet.dev/) (Flutter for Python)
- **Communication**: MQTT (AWS IoT Core) for real-time updates
- **Backend API**: Integration with Honda/Acura Identity and Web Services

## Getting Started

### Prerequisites
- Python 3.9+
- A valid HondaLink / AcuraLink account

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/logue-app.git
   cd logue-app
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Create a `.env` file in the root directory with the following:
   ```env
   HONDA_CLIENT_SECRET=your_client_secret
   ENCRYPTION_KEY=your_encryption_key
   ```

4. **Run the application**:
   ```bash
   flet run main.py
   ```

## Development Note

This project was developed using a "vibe coding" approach—leveraging advanced AI pair programming to rapidly iterate and implement complex vehicle integration logic. While AI-assisted, the focus remains on technical reliability and a clean user experience.

## Build and Versioning

The app is configured via `pyproject.toml` and `flet.yaml` for Android compilation. For APK generation, ensure you have the Flet CLI installed.

---
*Disclaimer: This app is not affiliated with American Honda Motor Co., Inc. Use remote commands responsibly.*
