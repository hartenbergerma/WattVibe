from threading import Thread
import signal
import argparse

from .color_control import LightController
from .web_ui import WebServer
from .control_status import start_status_checks, stop_status_checks

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    ftp: int = Field(default=300, description="Aktuelle FTP in Watt")
    hub_ip: str = Field(..., alias="HUB_IP")
    hub_token: str = Field(..., alias="HUB_TOKEN")
    light_name: str = Field(default="Trainer", alias="LIGHT_NAME", description="Name des Lichts in der Dirigera App")
    web_port: int = Field(default=5001, alias="WEB_PORT", description="Port für die Web UI")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", alias="LOG_FORMAT")

    # Konfiguration für das Laden der .env Datei
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

def start():
    parser = argparse.ArgumentParser(description='Start power tracker and web UI')
    parser.add_argument('--mock', action='store_true', help='Use mock power tracker with static power')
    args = parser.parse_args()

    settings = Settings()

    if args.mock:
        from .mock_power_tracker import MockPowerTracker as ChosenTracker
        from .mock_color_control import MockHub as Hub
    else:
        from .power_tracker import PowerTracker as ChosenTracker
        from dirigera import Hub

    hub = Hub(token=settings.hub_token, ip_address=settings.hub_ip)
    controller = LightController(
        hub, 
        settings.light_name, 
        settings.ftp,   
        settings.log_level,
        settings.log_format
    )

    tracker = ChosenTracker(
        power_callback=controller.update_light_color,
        connected_callback=controller.update_connection_status,
        device_address="DD:FB:7B:77:1F:EF",
        log_level=settings.log_level,
        log_format=settings.log_format
    )

    tracker.start()

    # Start status tracker thread
    status_thread = Thread(target=start_status_checks, args=(controller,))
    status_thread.start()

    # Start web server in background thread
    web_server = WebServer(settings.web_port)
    web_server.start()

    print(f"Power tracker started. Web UI available on port {settings.web_port}. Press Ctrl+C to exit.")
    try:
        signal.pause()
    except KeyboardInterrupt:
        stop_status_checks()
        web_server.shutdown()
        tracker.stop()
        status_thread.join()
        print("Stopped.")


if __name__ == "__main__":
    start()
