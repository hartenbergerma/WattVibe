import asyncio
import logging
import threading
from typing import Callable, Tuple
from bleak import BleakClient, BleakScanner, BLEDevice

from .control_status import set_trainer_connected, set_trainer_power

FTMS_BIKE_DATA_UUID = "00002ad2-0000-1000-8000-00805f9b34fb"

def parse_ftsm_bike_data(data: bytes) -> Tuple[float, float, int]:
    speed_raw = int.from_bytes(data[2:4], 'little')
    cadence_raw = int.from_bytes(data[4:6], 'little')
    power_raw = int.from_bytes(data[6:8], 'little', signed=True)
    
    speed = speed_raw / 100.0
    cadence = cadence_raw * 0.5
    power = power_raw
    
    logging.debug(f"Parsed data - Speed: {speed} km/h, Cadence: {cadence} rpm, Power: {power} W")
    return speed, cadence, power

class PowerTracker:
    def __init__(
            self, 
            power_callback: Callable[[int], None] = None,
            connected_callback: Callable[[bool], None] = None,
            device_address: str = None, 
            log_level: str = "INFO",
            log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ):
        self.power_callback = power_callback
        self.connected_callback = connected_callback
        self.device_address = device_address
        self._thread = None
        self._loop = None
        self._stop_event = None
        
        self._logger = logging.getLogger(__name__)
        handler = logging.StreamHandler() # oder FileHandler
        formatter = logging.Formatter(log_format)
        handler.setFormatter(formatter)
        
        self._logger.addHandler(handler)
        self._logger.setLevel(log_level.upper())

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._thread_main, daemon=True)
        self._thread.start()

    def stop(self):
        if self._loop and self._stop_event:
            # Signalisiert dem async-Loop sofort aufzuhören
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread:
            self._thread.join(timeout=2.0)

    async def _connect(self) -> BLEDevice:
        """Sucht das Gerät, solange bis es gefunden wird oder der Stop-Event feuert."""
        logging.debug("Searching for device...")
        while not self._stop_event.is_set():
            try:
                device = await BleakScanner.find_device_by_address(self.device_address, timeout=5.0)
                if device:
                    self._logger.info(f"Found device: {device.address}")
                    # kurze Pause, um Scanner-Ressourcen freizugeben
                    await asyncio.sleep(1.0) 
                    return device
            except Exception as e:
                self._logger.error(f"Scanner error: {e}")
            
            await asyncio.sleep(1.0)
        return None

    async def _listen(self, device: BLEDevice):
        try:
            async with BleakClient(device) as client:
                if self.connected_callback:
                    self.connected_callback(True)
                self._logger.debug(f"Connected to {device.address}")
                await client.start_notify(FTMS_BIKE_DATA_UUID, self._notification_handler)
                
                # Warten bis Disconnect oder Stop
                while client.is_connected and not self._stop_event.is_set():
                    await asyncio.sleep(0.5)
                
                if client.is_connected:
                    await client.disconnect()
        except Exception as e:
            self._logger.error(f"Connection error: {e}")

    async def _run_loop(self):
        self._stop_event = asyncio.Event()
        while not self._stop_event.is_set():
            device = await self._connect()
            if device and not self._stop_event.is_set():
                await self._listen(device)
                self._logger.info("Device got disconnected")
            if self.connected_callback:
                self.connected_callback(False)
            set_trainer_connected(False)
            set_trainer_power(0)
            if not self._stop_event.is_set():
                await asyncio.sleep(2.0) # Pause vor Reconnect

    def _notification_handler(self, sender, data: bytes):
        try:
            _, _, power = parse_ftsm_bike_data(data)
            
            if power is not None and self.power_callback:
                set_trainer_power(power)
                self._logger.debug(f"Calling callback with power: {power}")
                if self._loop:
                    self._loop.call_soon_threadsafe(self.power_callback, power)
        except Exception as e:
            self._logger.error(f"Handler error: {e}")

    def _thread_main(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run_loop())
        finally:
            self._loop.close()


if __name__ == "__main__":
    # Simple test runner when executing this module directly
    def print_power(p):
        print(f"Callback got power: {p}")

    def print_connected(connected: bool):
        print(f"New connection state: {connected}")

    tracker = PowerTracker(
        power_callback=print_power,
        connected_callback=print_connected,
        device_address="DD:FB:7B:77:1F:EF"
    )
    tracker.start()
    print("Press Ctrl+C to stop")
    try:
        while True:
            threading.Event().wait(1.0)
    except KeyboardInterrupt:
        tracker.stop()
        print("Stopped.")



