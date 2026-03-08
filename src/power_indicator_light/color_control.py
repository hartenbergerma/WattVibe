import math
from dataclasses import dataclass
from typing import Tuple
import threading
import colour

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
    xy = colour.temperature.CCT_to_xy_Planckian(kelvin)
    xyz = colour.xy_to_XYZ(xy)
    rgb = colour.XYZ_to_sRGB(xyz)
    rgb_clipped = colour.utilities.intermediate.np.clip(rgb, 0, 1)
    hsv = colour.RGB_to_HSV(rgb_clipped)
    
    # hsv[0] ist Hue (0-1), hsv[1] ist Saturation (0-1)
    hue_degrees = hsv[0] * 360
    sat = hsv[1]

    return hue_degrees, sat

class LightController:
    def __init__(self, hub, light_name: str, ftp: float):
        self.hub = hub
        self.light_name = light_name
        self.ftp = ftp
        self.light = None
        self.cached_light_state = None
        self._lock = threading.Lock()

    def find_light(self) -> bool:
        if self.light:
            self.capture_light_state()
            return True
        try:
            lights = self.hub.get_lights()
            light = [light for light in lights if light.attributes.custom_name == self.light_name]
            if light:
                self.light = light[0]
                self.capture_light_state()
                return True
            else:
                print(f"Light '{self.light_name}' not found.")
                return False
        except Exception as e:
            print(f"Error finding light: {e}")
            return False
        
    def capture_light_state(self):
        if self.cached_light_state is None:
            state = {  
                'is_on': self.light.attributes.is_on,  
                'light_level': self.light.attributes.light_level,  
                'color_mode': self.light.attributes.color_mode,
                'color_temperature': self.light.attributes.color_temperature,  
                'color_hue': self.light.attributes.color_hue,  
                'color_saturation': self.light.attributes.color_saturation,  
            }
            self.cached_light_state = state

    def get_light_color(self) -> Tuple[float, float]:
        with self._lock:
            try:
                if self.find_light():
                    if self.light.attributes.color_mode == 'temperature':
                        temperature = self.light.attributes.color_temperature
                        if temperature is not None:
                            return kelvin_to_hue_sat(temperature)
                    else:
                        hue = self.light.attributes.color_hue
                        saturation = self.light.attributes.color_saturation
                        return hue, saturation
            except Exception as e:
                print(f"Error getting light color: {e}")
                return 0.0, 0.0

    def get_hub_status(self) -> bool:
        with self._lock:
            try:  
                # Make a simple GET request to check connectivity  
                response = self.hub.get("/devices")  
                return True
            except Exception as e:
                print(f"Hub is not reachable: {e}")
                return False

    def get_light_status(self) -> bool:
        with self._lock:
            try:
                if self.find_light():
                    return self.light.is_reachable()
            except Exception as e:
                print(f"Light is not reachable: {e}")
            return False

    def restore_light_state(self):
        with self._lock:
            if self.cached_light_state and self.find_light():
                state = self.cached_light_state
                try:
                    self.light.set_light(state['is_on'])
                    self.light.set_light_level(state['light_level'])

                    if state['color_mode'] == 'temperature':
                        temperature = state['color_temperature']
                        if temperature is not None:
                            self.light.set_color_temperature(temperature)
                            set_light_color(kelvin_to_hue_sat(temperature))
                    else:
                        hue = state['color_hue']
                        saturation = state['color_saturation']
                        if hue is not None and saturation is not None:
                            self.light.set_light_color(hue, saturation)
                            set_light_color(hue, saturation)
                    self.cached_light_state = None
                except Exception as e:
                    print(f"Error restoring light state: {e}")

    def update_light_color(self, power: float):
        with self._lock:
            try:
                hue, saturation = get_zone_color(power, self.ftp)
                if self.find_light():
                    self.light.set_light_color(hue, saturation)
                    set_light_color(hue, saturation)
            except Exception as e:
                print(f"Error updating light color: {e}")