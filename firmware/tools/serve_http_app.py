"""
A simple script to serve the HTTP app for testing purposes.

Usage: From the `firmware` directory:

  export PYTHONPATH=$PYTHONPATH:$(pwd)/app
  python -m tools.serve_http_app

Access the app at http://localhost:5000.
"""

import asyncio
import os

os.chdir(os.path.join(os.path.dirname(__file__), "..", "app"))

from http_app import HttpApp
from game_state import GameState


class MockBatteryState:
    def get_battery_voltage(self) -> float:
        return 0

    def get_battery_state(self) -> tuple[str, int]:
        return "charging", 0


def main():
    game_state = GameState()
    battery_state = MockBatteryState()
    http_app = HttpApp(game_state, battery_state)
    asyncio.run(http_app.app.start_server())


if __name__ == "__main__":
    main()
