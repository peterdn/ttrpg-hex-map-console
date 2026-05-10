"""
Game state model that tracks:
- The current location displayed on the screen.
- The state of the fire at each location.

Notifies subscribed event handlers when game state changes.
"""


class FireState:
    EXTINGUISHED = 0
    HEALTHY = 1
    CORRUPTED = 2
    EVERBURNING = 3
    ETHEREAL = 4

    @staticmethod
    def is_valid(state):
        return state >= FireState.EXTINGUISHED and state <= FireState.ETHEREAL


class GameState:
    def __init__(self):
        self.locations = [
            "Galestone",
            "Ransfall",
            "Blacktower",
            "Pale Burg",
        ]
        self.fire_states = {loc: FireState.EXTINGUISHED for loc in self.locations}
        self.current_location = "Galestone"
        self.event_handlers = []

    def subscribe(self, event_handler):
        self.event_handlers.append(event_handler)

    def set_fire_state(self, location: str, state: int):
        if not FireState.is_valid(state):
            raise ValueError(f"Invalid fire state: {state}")
        if self.fire_states.get(location) != state:
            self.fire_states[location] = state
            self._dispatch_event("fire_state_change", location, state)

    def set_current_location(self, location: str):
        if location in self.locations and location != self.current_location:
            self.current_location = location
            self._dispatch_event(
                "location_change", location, self.fire_states[location]
            )

    def _dispatch_event(self, event_type, location, state):
        for handler in self.event_handlers:
            handler(event_type, location, state)
