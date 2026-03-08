import logging
import threading
import time
from typing import Callable

from .control_status import set_trainer_connected, set_trainer_power

class MockPowerTracker:
    """Simple mock that calls the callback with a static power value periodically."""
    def __init__(
            self, 
            power_callback: Callable[[int], None], 
            connected_callback: Callable[[bool], None], 
            device_address: str, 
            log_level: str, 
            log_format: str
        ):
        self.power_callback = power_callback
        self.connected_callback = connected_callback
        self.device_address = device_address
        self.interval = 1.0
        self._counter = 0
        self._thread = None
        self._stop_event = threading.Event()

        self._logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(log_format)
        handler.setFormatter(formatter)
        
        self._logger.addHandler(handler)
        self._logger.setLevel(log_level.upper())

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
        try:
            while not self._stop_event.wait(self.interval):
                disconnect_interval = 10
                epoch_counter = self._counter % disconnect_interval
                if epoch_counter > disconnect_interval // 2:
                    if epoch_counter == disconnect_interval // 2 + 1:
                        self._logger.debug("Simulated disconnection")
                        self.connected_callback(False)
                        set_trainer_connected(False)
                        set_trainer_power(0)
                else:
                    if epoch_counter == 0:
                        self._logger.debug("Simulated reconnection")
                        self.connected_callback(True)
                        set_trainer_connected(True)
                    power = (self._counter * 15) % 400
                    self._logger.info(f"Mock Power Tracker: {power} W")
                    self.power_callback(power)
                    set_trainer_power(power)
                self._counter += 1
        except Exception:
            self._logger.error("Error in Mock Power Tracker")
