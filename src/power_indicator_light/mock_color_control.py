import math
from dataclasses import dataclass
from typing import Tuple, List, Optional

class MockAttributes:
    def __init__(self, name: str):
        self.custom_name = name
        self.is_on = True
        self.light_level = 100
        self.color_temperature = 2700
        self.color_hue = 0.0
        self.color_saturation = 0.0
        self.color_mode = "color"

class MockLight:
    def __init__(self, name: str):
        self.attributes = MockAttributes(name)
        self.reachable = True

    def is_reachable(self) -> bool:
        return self.reachable

    def set_light(self, on: bool):
        self.attributes.is_on = on
        print(f"[Mock] Light {'ON' if on else 'OFF'}")

    def set_light_level(self, level: int):
        self.attributes.light_level = level
        print(f"[Mock] Light level set to {level}")

    def set_color_temperature(self, temp: int):
        self.attributes.color_temperature = temp
        print(f"[Mock] Color temp set to {temp}K")

    def set_light_color(self, hue: float, saturation: float):
        self.attributes.color_hue = hue
        self.attributes.color_saturation = saturation
        print(f"[Mock] Color set to Hue: {hue}, Sat: {saturation}")

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