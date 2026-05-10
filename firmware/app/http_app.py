"""
Microdot-powered HTTP API for the game.
Provides endpoints to get and update game state, and to
subscribe to game state changes via Server-Sent Events.
Also serves static assets for the web app.
"""

import asyncio
import gc
import json

try:
    from asyncio import Queue
except (ImportError, AttributeError):
    from queue import Queue

from microdot import Microdot, Response

from game_state import GameState, FireState


class HttpApp:
    def __init__(self, game_state: GameState, battery_state: object):
        self.app = Microdot()
        self.game_state = game_state
        self.battery_state = battery_state
        self.app.route("/")(self.index)
        self.app.route("/favicon.ico")(self.favicon)
        self.app.route("/assets/<filename>", methods=["GET"])(self.assets)
        self.app.route("/state", methods=["POST", "GET"])(self.state)
        self.app.route("/battery", methods=["GET"])(self.battery)
        self.app.route("/reset", methods=["POST"])(self.reset)
        self.app.route("/subscribe", methods=["GET"])(self.subscribe)
        self.app.before_request(self._cleanup)
        self.game_state.subscribe(self._on_game_state_change)
        self.subscribers = []

    async def start_server(self):
        await self.app.start_server()

    async def _cleanup(self, request):
        gc.collect()

    async def index(self, request):
        return Response.send_file("assets/index.html", content_type="text/html")

    async def favicon(self, request):
        return Response.send_file(
            "assets/flame_healthy.png", content_type="image/png", max_age=86400
        )

    async def assets(self, request, filename):
        if "/" in filename or "\\" in filename or ".." in filename:
            return {"error": "Forbidden"}, 403
        if not filename.endswith(".png"):
            return {"error": "Not found"}, 404
        try:
            return Response.send_file(
                f"assets/{filename}", content_type="image/png", max_age=86400
            )
        except OSError:
            return {"error": "Not found"}, 404

    def _format_current_state(self):
        return {
            "current_location": self.game_state.current_location,
            "locations": self.game_state.locations,
            "fire_states": self.game_state.fire_states,
        }

    async def state(self, request):
        if request.method == "GET":
            return self._format_current_state()
        elif request.method == "POST":
            data = request.json
            try:
                fire_states = data.get("fire_states", {})
                if not isinstance(fire_states, dict):
                    raise ValueError("fire_states must be a dictionary")
                # Validate locations and fire states by throwing ValueError
                for location, fire_state in fire_states.items():
                    if location not in self.game_state.locations:
                        raise ValueError(f"Invalid location: {location}")
                    if not FireState.is_valid(fire_state):
                        raise ValueError(
                            f"Invalid fire state for location: {location} {fire_state}"
                        )
            except ValueError as e:
                return {"error": str(e)}, 400

            for location, fire_state in fire_states.items():
                if location not in self.game_state.locations:
                    return {"error": "Invalid location"}, 400

                print(f"Setting fire state for {location} to {fire_state}")

                self.game_state.set_fire_state(location, fire_state)

            if "current_location" in data:
                current_location = data["current_location"]
                if current_location not in self.game_state.locations:
                    return {"error": "Invalid location"}, 400
                self.game_state.set_current_location(current_location)

            return {
                "status": "success",
                "current_location": self.game_state.current_location,
                "fire_states": self.game_state.fire_states,
            }

    async def battery(self, request):
        voltage = self.battery_state.get_battery_voltage()
        battery_state = self.battery_state.get_battery_state()
        return {
            "voltage": voltage,
            "state": battery_state[0],
            "percentage": battery_state[1],
        }

    def _on_game_state_change(self, event_type, location, state):
        print(f"Game state changed: {event_type} {location} {state}")
        event = {"event_type": event_type, "location": location, "state": state}
        for q in self.subscribers:
            q.put_nowait(event)

    async def subscribe(self, request):
        queue = Queue()
        self.subscribers.append(queue)
        initial = self._format_current_state()
        initial["event_type"] = "initial_state"

        # MicroPython doesn't support async generator functions
        # but async class-based generators work fine...
        class EventStream:
            def __aiter__(s):
                s._sent_initial = False
                return s

            async def __anext__(s):
                if not s._sent_initial:
                    s._sent_initial = True
                    return f"data: {json.dumps(initial)}\n\n".encode()
                data = await queue.get()
                return f"data: {json.dumps(data)}\n\n".encode()

            async def aclose(s):
                self.subscribers.remove(queue)

        return Response(
            body=EventStream(),
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    async def reset(self, request):
        # self.app.shutdown()
        # reset()
        # TODO: send a message to main loop, shutdown server, display UI
        asyncio.create_task(self._reset_async())
        return {"status": "resetting"}

    async def _reset_async(self):
        from machine import reset

        await asyncio.sleep(5)
        reset()
