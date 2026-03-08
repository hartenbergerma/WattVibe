from threading import Lock, Event
from typing import Tuple, TYPE_CHECKING
from copy import deepcopy
import time

if TYPE_CHECKING:
    from color_control import LightController

# Globales Stop-Event
stop_event = Event()

# Simple thread-safe status store for the web UI
_status = {
    "hub_reachable": False,
    "light_working": False,
    "trainer_connected": False,
    "trainer_power": 0,
    "light_color": (0.0, 0.0),
}
_lock = Lock()

def start_status_checks(controller: "LightController"):
    """
    Läuft in einem Thread und prüft regelmäßig den Status.
    Bricht ab, sobald stop_event.set() aufgerufen wird.
    """
    print("Status-Checker gestartet...")
    while not stop_event.is_set():
        with _lock:
            _status["hub_reachable"] = controller.get_hub_status()
            _status["light_working"] = controller.get_light_status()
            _status["light_color"] = controller.get_light_color()
        
        # Wartet 5 Sekunden ODER bis das Event gesetzt wird
        stop_event.wait(timeout=5)
    print("Status-Checker beendet.")

def stop_status_checks():
    """Signalisiert dem Thread, dass er stoppen soll."""
    stop_event.set()

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