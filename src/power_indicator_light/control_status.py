from threading import Lock
from typing import Tuple, TYPE_CHECKING
from copy import deepcopy
import time

if TYPE_CHECKING:
    from color_control import LightController

# Simple thread-safe status store for the web UI
_status = {
    "hub_reachable": False,
    "light_working": False,
    "trainer_connected": False,
    "trainer_power": 0,
    "light_color": (0.0, 0.0),
}
_lock = Lock()

def status_checker(controller: "LightController"):
    while True:
        # Hier kannst du den Status des Hubs und der Lichter überprüfen
        with _lock:
            _status["hub_reachable"] = controller.get_hub_status()
            _status["light_working"] = controller.get_light_status()
            _status["light_color"] = controller.get_light_color()
        time.sleep(5)  # Überprüfe alle 5 Sekunden

def set_trainer_connected(val: bool):
    with _lock:
        _status["trainer_connected"] = bool(val)

def set_trainer_power(value: float):
    with _lock:
        _status["trainer_power"] = value

def set_light_color(hue: float, saturation: float):
    with _lock:
        _status["light_color"] = (hue, saturation)


def get_status():
    with _lock:
        return deepcopy(_status)
