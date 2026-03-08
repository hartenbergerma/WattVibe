import threading
import time
from typing import Callable

from control_status import set_trainer_connected, set_trainer_power

class MockPowerTracker:
    """Simple mock that calls the callback with a static power value periodically."""
    def __init__(self, callback: Callable[[int], None], device_address: str):
        self.callback = callback
        self.device_address = device_address
        self.interval = 1.0
        self._counter = 0
        self._thread = None
        self._stop_event = threading.Event()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self):
        # Immediately send one reading, then periodically
        set_trainer_connected(True)
        try:
            while not self._stop_event.wait(self.interval):
                power = (self._counter * 20) % 400
                print(f"Mock Power Tracker: {power} W")
                self.callback(power)
                set_trainer_power(power)
                self._counter += 1
        except Exception:
            pass
