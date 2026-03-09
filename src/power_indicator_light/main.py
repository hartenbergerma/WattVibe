import threading
import signal
import time
import argparse
from .color_control import LightController
from .web_ui import WebServer
from .control_status import start_status_checks, stop_status_checks, reset_status

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    ftp: int = Field(default=300, description="Aktuelle FTP in Watt")
    trainer_address: str = Field(..., description="Bluetooth-Adresse des Trainers")
    hub_ip: str = Field(..., alias="HUB_IP")
    hub_token: str = Field(..., alias="HUB_TOKEN")
    light_name: str = Field(default="Trainer", alias="LIGHT_NAME", description="Name des Lichts in der Dirigera App")
    web_port: int = Field(default=5001, alias="WEB_PORT", description="Port für die Web UI")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", alias="LOG_FORMAT")

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )


class SystemManager:
    def __init__(self, settings, args):
        self.settings = settings
        self.args = args
        self.tracker = None
        self.status_thread = None
        self.controller = None
        self.lock = threading.Lock() # Prevent race conditions during restart

    def start_workers(self):
        with self.lock:
            # Import based on args
            if self.args.mock:
                from .mock_power_tracker import MockPowerTracker as ChosenTracker
                from .mock_color_control import MockHub as Hub
            else:
                from .power_tracker import PowerTracker as ChosenTracker
                from dirigera import Hub

            hub = Hub(token=self.settings.hub_token, ip_address=self.settings.hub_ip)
            
            self.controller = LightController(
                hub, 
                self.settings.light_name, 
                self.settings.ftp,   
                self.settings.log_level,
                self.settings.log_format
            )

            self.tracker = ChosenTracker(
                power_callback=self.controller.update_light_color,
                connected_callback=self.controller.update_connection_status,
                device_address=self.settings.trainer_address,
                log_level=self.settings.log_level,
                log_format=self.settings.log_format
            )

            self.tracker.start()
            self.status_thread = threading.Thread(target=start_status_checks, args=(self.controller,))
            self.status_thread.start()
            print("Workers initialized.")

    def stop_workers(self):
        with self.lock:
            if self.tracker:
                self.tracker.stop()
            stop_status_checks()
            if self.status_thread:
                self.status_thread.join()
            print("Workers stopped.")

    def restart(self):
        print("Restarting workers...")
        self.stop_workers()
        reset_status()
        time.sleep(1)
        self.settings = Settings() 
        self.start_workers()

def start():
    parser = argparse.ArgumentParser(description='Start power tracker and web UI')
    parser.add_argument('--mock', action='store_true', help='Use mock power tracker with static power')
    args = parser.parse_args()

    settings = Settings()
    
    manager = SystemManager(settings, args)
    manager.start_workers()

    web_server = WebServer(settings.web_port, restart_callback=manager.restart)
    web_server.start()

    try:
        signal.pause()
    except KeyboardInterrupt:
        manager.stop_workers()
        web_server.shutdown()


if __name__ == "__main__":
    start()
