from threading import Thread
import signal
import argparse

from .color_control import LightController
from .web_ui import run_web_server
from .control_status import status_checker


# --- KONFIGURATION ---
FTP = 300  # Setze hier deine aktuelle FTP in Watt
HUB_IP = "192.168.x.x"
HUB_TOKEN = "DEIN_TOKEN"
LIGHT_NAME = "Trainer"
WEB_PORT = 5001

def start():
    parser = argparse.ArgumentParser(description='Start power tracker and web UI')
    parser.add_argument('--mock', action='store_true', help='Use mock power tracker with static power')
    args = parser.parse_args()

    if args.mock:
        from .mock_power_tracker import MockPowerTracker as ChosenTracker
        from .mock_color_control import MockHub as Hub
    else:
        from .power_tracker import PowerTracker as ChosenTracker
        from dirigera import Hub

    hub = Hub(token=HUB_TOKEN, ip_address=HUB_IP)
    controller = LightController(hub, LIGHT_NAME, FTP)

    tracker = ChosenTracker(
        controller.update_light_color,
        device_address="DD:FB:7B:77:1F:EF")

    tracker.start()

    # Start status tracker thread
    status_thread = Thread(target=status_checker, args=(controller,))
    status_thread.start()

    # Start web server in background thread
    web_thread = Thread(target=run_web_server, args=(WEB_PORT,), daemon=True)
    web_thread.start()

    print(f"Power tracker started. Web UI available on port {WEB_PORT}. Press Ctrl+C to exit.")
    try:
        signal.pause()
    except KeyboardInterrupt:
        pass
    finally:
        tracker.stop()
        status_thread.join(timeout=2.0)
        web_thread.join(timeout=2.0)
        print("Stopped.")


if __name__ == "__main__":
    start()
