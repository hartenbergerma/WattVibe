import math
import logging
from dataclasses import dataclass
from typing import Tuple, List, Optional

class MockAttributes:
    def __init__(self, name: str):
        self.custom_name = name
        self.is_on = True
        self.light_level = 50
        self.color_temperature = 2700
        self.color_hue = 50.0
        self.color_saturation = 0.5
        self.color_mode = "temperature"

class MockLight:
    def __init__(self, name: str,log_level: str = "INFO", log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"):
        self.attributes = MockAttributes(name)
        self.reachable = True

        self._logger = logging.getLogger(__name__)
        handler = logging.StreamHandler() # oder FileHandler
        formatter = logging.Formatter(log_format)
        handler.setFormatter(formatter)
        
        self._logger.addHandler(handler)
        self._logger.setLevel(log_level.upper())

    def is_reachable(self) -> bool:
        return self.reachable

    def set_light(self, on: bool):
        self.attributes.is_on = on
        self._logger.info(f"[Mock] Light {'ON' if on else 'OFF'}")

    def set_light_level(self, level: int):
        self.attributes.light_level = level
        self._logger.info(f"[Mock] Light level set to {level}")

    def set_color_temperature(self, temp: int):
        self.attributes.color_temperature = temp
        self.attributes.color_mode = "temperature"
        self._logger.info(f"[Mock] Color temp set to {temp}K")

    def set_light_color(self, hue: float, saturation: float):
        self.attributes.color_hue = hue
        self.attributes.color_saturation = saturation
        self.attributes.color_mode = "color"
        self._logger.info(f"[Mock] Color set to Hue: {hue}, Sat: {saturation}")

class MockHub:
    def __init__(self, token, ip_address):
        self.lights = [MockLight("Trainer")]
        self.token = token
        self.ip_address = ip_address

    def get_lights(self) -> List[MockLight]:
        return self.lights

    def get(self, endpoint: str):
        # Simulates the self.hub.get("/devices") call
        if endpoint == "/devices":
            return {"status": "ok"}
        raise Exception("404 Not Found")