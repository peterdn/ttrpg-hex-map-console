"""
LED state management and animation logic for:
- Flickering to simulate flame.
- Transitions between colours when fire states change.
"""

import random

from game_state import FireState
from ema import EMA


class HealthyFireLEDConfig:
    """Healthy fire is bright orange"""

    def __init__(self):
        self.base_color = (1.0, 0.41, 0)
        self.brightness_ema = EMA(0.1)
        self.red_jitter_ema = EMA(0.2)

    def tick(self):
        brightness = self.brightness_ema.update(random.random())
        red_jitter = self.red_jitter_ema.update(random.uniform(-0.1, 0.1))

        brightness = max(0.0, min(1.0, brightness + 0.3))

        r = brightness * (self.base_color[0] + red_jitter)
        r = max(0.0, min(1.0, r))
        g = brightness * (self.base_color[1] - red_jitter)
        g = max(0.0, min(1.0, g))
        b = brightness * self.base_color[2]
        b = max(0.0, min(1.0, b))

        return (r, g, b, brightness)


class ExtinguishedFireLEDConfig:
    """Extinguished fire is off"""

    def __init__(self):
        self.base_color = (0.0, 0.0, 0.0)

    def tick(self):
        return (0.0, 0.0, 0.0, 0.0)


class CorruptedFireLEDConfig(HealthyFireLEDConfig):
    """Corrupted fire is green"""

    def __init__(self):
        super().__init__()
        self.base_color = (0.0, 1.0, 0.0)


class EverburningFireLEDConfig(HealthyFireLEDConfig):
    """Everburning fire is bright golden white/yellow"""

    def __init__(self):
        super().__init__()
        self.base_color = (1.0, 0.9, 0.2)


class EtherealFireLEDConfig(HealthyFireLEDConfig):
    """Ethereal fire is blue"""

    def __init__(self):
        super().__init__()
        self.base_color = (0.2, 0.5, 1.0)


class LEDState:
    def __init__(
        self,
        name: str,
        channel: int,
        initial_fire_state: FireState = FireState.EXTINGUISHED,
    ):
        self.TRANSITION_TICKS = 20
        self.name = name
        self.channel = channel
        self._fire_state = initial_fire_state
        self.transition_ticks_remaining = 0

        self.led_configs = {
            FireState.HEALTHY: HealthyFireLEDConfig(),
            FireState.EXTINGUISHED: ExtinguishedFireLEDConfig(),
            FireState.CORRUPTED: CorruptedFireLEDConfig(),
            FireState.EVERBURNING: EverburningFireLEDConfig(),
            FireState.ETHEREAL: EtherealFireLEDConfig(),
        }

    def set_fire_state(self, fire_state: FireState):
        if fire_state == self._fire_state:
            return

        self._old_fire_state = self._fire_state
        self._fire_state = fire_state

        if self.transition_ticks_remaining == 0:
            self.transition_ticks_remaining = self.TRANSITION_TICKS
            self.transition_fire_values = self.led_configs[self._old_fire_state].tick()
        else:
            # a transition was already in progress, move the target without resetting the transition
            pass

    def tick(self):
        if self.transition_ticks_remaining > 0:
            # During a transition, interpolate between the old and new fire colours
            new_fire_values = self.led_configs[self._fire_state].tick()
            rdiff = new_fire_values[0] - self.transition_fire_values[0]
            gdiff = new_fire_values[1] - self.transition_fire_values[1]
            bdiff = new_fire_values[2] - self.transition_fire_values[2]
            brightness_diff = new_fire_values[3] - self.transition_fire_values[3]

            r = self.transition_fire_values[0] + rdiff / self.transition_ticks_remaining
            g = self.transition_fire_values[1] + gdiff / self.transition_ticks_remaining
            b = self.transition_fire_values[2] + bdiff / self.transition_ticks_remaining
            brightness = (
                self.transition_fire_values[3]
                + brightness_diff / self.transition_ticks_remaining
            )

            self.transition_ticks_remaining -= 1
            self.transition_fire_values = (r, g, b, brightness)
            return (r, g, b, brightness)
        else:
            # No transition in progress, just tick the current fire state config
            return self.led_configs[self._fire_state].tick()
