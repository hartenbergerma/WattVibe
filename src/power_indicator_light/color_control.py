import math
from dataclasses import dataclass
from typing import Tuple
import threading
import colour
import logging
import numpy as np

from .control_status import set_light_color


@dataclass
class Zone:
    name: str
    upper_threshold: float # Anteil der FTP (0.6 = 60%)
    color: Tuple[int, int, int]  # RGB

# Definiere die Zwift-Zonen (Schwellenwerte sind jeweils das Ende der Zone)
ZWIFT_ZONES = [
    Zone("Recovery", 0.6, (0.0, 0.0)),       # Gray (Saturation 0)
    Zone("Endurance", 0.76, (210.0, 0.7)),   # Blue
    Zone("Tempo", 0.9, (120.0, 0.6)),        # Green
    Zone("Threshold", 1.05, (54.0, 0.9)),    # Yellow
    Zone("VO2 Max", 1.18, (28.0, 0.9)),      # Orange
    Zone("Anaerobic", math.inf, (0.0, 1.0))  # Red
]

def get_zone_color(power: float, ftp: float) -> Tuple[float, float]:
    percent_ftp = power / ftp

    for zone in ZWIFT_ZONES:
        if percent_ftp < zone.upper_threshold:
            return zone.color
        

def kelvin_to_hue_sat(kelvin):
    # Fixed from previous error
    xy = colour.temperature.CCT_to_xy(kelvin)
    xyz = colour.xy_to_XYZ(xy)
    rgb = colour.XYZ_to_sRGB(xyz)
    
    # Use NumPy directly instead of the hidden 'intermediate' attribute
    rgb_clipped = np.clip(rgb, 0, 1)
    
    hsv = colour.RGB_to_HSV(rgb_clipped)
    
    hue_degrees = hsv[0] * 360
    sat = hsv[1]

    return hue_degrees, sat

class LightController:
    def __init__(self, hub, light_name: str, ftp: float, log_level: str, log_format: str):
        self.hub = hub
        self.light_name = light_name
        self.ftp = ftp
        self.light = None
        self.cached_light_state = None
        self.trainer_connection_status = False
        self._lock = threading.Lock()
        
        self._logger = logging.getLogger(__name__)
        handler = logging.StreamHandler() # oder FileHandler
        formatter = logging.Formatter(log_format)
        handler.setFormatter(formatter)
        
        self._logger.addHandler(handler)
        self._logger.setLevel(log_level.upper())

    def find_light(self) -> bool:
        try:
            if self.light:
                return True
            lights = self.hub.get_lights()
            light = [light for light in lights if light.attributes.custom_name == self.light_name]
            if light:
                self.light = light[0]
                return True
            else:
                self._logger.warning(f"Light '{self.light_name}' not found.")
                return False
        except Exception as e:
            self._logger.error(f"Error finding light: {e}")
            return False
        
    def get_light_color(self) -> Tuple[float, float]:
        with self._lock:
            try:
                if self.find_light():
                    if self.light.attributes.color_mode == 'temperature':
                        temperature = self.light.attributes.color_temperature
                        if temperature is not None:
                            hue, saturation = kelvin_to_hue_sat(temperature)
                            return hue, saturation
                    else:
                        hue = self.light.attributes.color_hue
                        saturation = self.light.attributes.color_saturation
                        return hue, saturation
            except Exception as e:
                self._logger.error(f"Error getting light color: {e}")
                return 0.0, 0.0

    def get_hub_status(self) -> bool:
        with self._lock:
            try:  
                # Make a simple GET request to check connectivity  
                response = self.hub.get("/devices")  
                return True
            except Exception as e:
                self._logger.error(f"Hub is not reachable: {e}")
                return False

    def get_light_status(self) -> bool:
        with self._lock:
            try:
                if self.find_light():
                    return self.light.is_reachable()
            except Exception as e:
                self._logger.error(f"Light is not reachable: {e}")
            return False

    def update_connection_status(self, is_connected: bool):
        with self._lock:
            try:
                if is_connected and not self.trainer_connection_status:
                    self._logger.debug("Trainer connected. Capturing light state.")
                    self.capture_light_state()
                    self.light.set_light(True)
                    self.light.set_light_level(100)
                    self.trainer_connection_status = True
                elif not is_connected and self.trainer_connection_status:
                    self._logger.debug("Trainer disconnected.")
                    self.restore_light_state()
                    self.cached_light_state = None
                    self.trainer_connection_status = False
                else:
                    self._logger.debug("Trainer connection status unchanged.")
            except Exception as e:
                self._logger.error(f"Error updating connection status: {e}")

    def capture_light_state(self):
        if self.find_light():
            state = {  
                'is_on': self.light.attributes.is_on,  
                'light_level': self.light.attributes.light_level,  
                'color_mode': self.light.attributes.color_mode,
                'color_temperature': self.light.attributes.color_temperature,  
                'color_hue': self.light.attributes.color_hue,  
                'color_saturation': self.light.attributes.color_saturation,  
            }
            self.cached_light_state = state
            self._logger.debug(f"Captured light state: {state}")
        else:
            self._logger.warning("No light found to capture state.")

    def restore_light_state(self):
        self._logger.debug(f"Attempting to restore light state: {self.cached_light_state}")
        if not self.cached_light_state:
            self._logger.warning("No cached light state to restore.")
            return
        if self.find_light():
            state = self.cached_light_state
            self.light.set_light(state['is_on'])
            self.light.set_light_level(state['light_level'])

            if state['color_mode'] == 'temperature':
                temperature = state['color_temperature']
                if temperature is not None:
                    self.light.set_color_temperature(temperature)
                    hue, saturation = kelvin_to_hue_sat(temperature)
                    set_light_color(hue, saturation)
                    self._logger.debug(f"Restored light color to temperature mode with {temperature}K")
            else:
                hue = state['color_hue']
                saturation = state['color_saturation']
                if hue is not None and saturation is not None:
                    self.light.set_light_color(hue, saturation)
                    set_light_color(hue, saturation)
                    self._logger.debug(f"Restored light color to hue: {hue}, saturation: {saturation}")
            self.cached_light_state = None
        else:
            self._logger.warning("No light found to restore state.")

    def update_light_color(self, power: float):
        with self._lock:
            try:
                hue, saturation = get_zone_color(power, self.ftp)
                if self.find_light():
                    self.light.set_light_color(hue, saturation)
                    set_light_color(hue, saturation)
                    self._logger.debug(f"Updated light color to hue: {hue}, saturation: {saturation}")
            except Exception as e:
                self._logger.error(f"Error updating light color: {e}")