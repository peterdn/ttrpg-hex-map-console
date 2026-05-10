"""Powers the LVGL user interface and fire LED states."""

import asyncio
import time

import lvgl as lv

from battery import BatteryState
from cst816s_drv import CST816S
from game_state import FireState, GameState
from led_state import LEDState
from tlc5947 import TLC5974


async def ui_task():
    last_tick = time.ticks_ms()
    while True:
        lv.timer_handler()
        await asyncio.sleep_ms(5)
        current_ticks = time.ticks_ms()
        elapsed = time.ticks_diff(current_ticks, last_tick)

        # Need to manually tell LVGL how much time has passed since the
        # last tick so it can update animations and fire timers etc.
        lv.tick_inc(elapsed)
        last_tick = current_ticks


class UserInterface:
    """
    Controller for the user interface.

    Creates a 2-tile LVGL tileview:
    - The main tile displays the current location and fire state.
      Swiping left/right changes location, tapping the fire icon
      cycles through fire states. Swiping up accesses the settings tile.
    - The settings tile displays network and battery status.
      Swiping down returns to the main tile.

    Also manages the state of the fire LEDs via the TLC5947 driver.

    Event-driven to update the UI and LEDs in response to various state
    changes, from user input to via the HTTP API.
    """

    def __init__(
        self,
        cst816s: CST816S,
        tlc5947: TLC5974,
        game_state: GameState,
        battery_state: BatteryState,
    ):
        self.cst816s = cst816s
        self.tlc5947 = tlc5947
        self.game_state = game_state
        self.battery_state = battery_state
        self.scr = lv.screen_active()
        self.scr.set_style_bg_color(lv.color_make(0, 0, 0), 0)

        self.tv = lv.tileview(self.scr)

        self.town_tile = self.tv.add_tile(0, 1, lv.DIR.TOP)
        self._create_settings_tile()

        self.tv.set_tile(self.town_tile, False)

        self.image = lv.image(self.town_tile)
        self.image.set_src("M:assets/galestone.bin")
        self.image.align(lv.ALIGN.CENTER, 0, 0)
        self.image.set_size(240, 240)

        self.town_name_label = lv.label(self.town_tile)
        self.town_name_label.align(lv.ALIGN.CENTER, 0, 25)
        self.town_name_label.set_style_bg_color(lv.color_make(0, 0, 0), 0)
        self.town_name_label.set_style_bg_opa(128, 0)
        self.town_name_label.set_style_radius(10, 0)
        self.town_name_label.set_style_pad_all(10, 0)
        self.town_name_label.set_style_border_width(0, 0)
        self.town_name_label.set_style_text_color(lv.color_make(255, 255, 255), 0)
        self.town_name_label.set_style_text_font(lv.font_montserrat_24, 0)
        self.town_name_label.set_text(self.game_state.current_location)

        self.scr.add_event_cb(self.image_event_cb, lv.EVENT.GESTURE, None)

        # Fire state icon — tap to cycle through fire states
        self.fire_icon = lv.image(self.town_tile)
        self.fire_icon.set_src("M:assets/flame_healthy.bin")
        self.fire_icon.align(lv.ALIGN.CENTER, 0, -30)
        self.fire_icon.set_size(60, 76)
        self.fire_icon.add_flag(lv.obj.FLAG.CLICKABLE)
        self.fire_icon.add_event_cb(self.fire_icon_event_cb, lv.EVENT.CLICKED, None)

        lv.timer_create(self.led_tick, 50, None)

        self.game_state.subscribe(self.game_event_handler)

        self.leds = [
            LEDState("Galestone", 7),
            LEDState("Ransfall", 5),
            LEDState("Blacktower", 3),
            LEDState("Pale Burg", 1),
        ]

        for location in self.game_state.locations:
            self.game_state.set_fire_state(location, FireState.HEALTHY)

    def _battery_icon_for(self, state, percentage):
        if state == BatteryState.CHARGING:
            return lv.SYMBOL.CHARGE
        if percentage >= 80:
            return lv.SYMBOL.BATTERY_FULL
        elif percentage >= 60:
            return lv.SYMBOL.BATTERY_3
        elif percentage >= 40:
            return lv.SYMBOL.BATTERY_2
        elif percentage >= 20:
            return lv.SYMBOL.BATTERY_1
        else:
            return lv.SYMBOL.BATTERY_EMPTY

    def _create_settings_tile(self):
        self.settings_tile = self.tv.add_tile(0, 0, lv.DIR.BOTTOM)

        # Background image
        image = lv.image(self.settings_tile)
        image.set_src("M:assets/age_of_umbra.bin")
        image.align(lv.ALIGN.CENTER, 0, 0)
        image.set_size(240, 240)

        # Semi-transparent overlay panel for text
        self.settings_panel = lv.obj(self.settings_tile)
        self.settings_panel.set_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT)
        self.settings_panel.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        self.settings_panel.set_flex_align(
            lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER
        )
        self.settings_panel.align(lv.ALIGN.CENTER, 0, 0)
        self.settings_panel.set_style_bg_color(lv.color_make(0, 0, 0), 0)
        self.settings_panel.set_style_bg_opa(128, 0)
        self.settings_panel.set_style_radius(5, 0)
        self.settings_panel.set_style_pad_all(10, 0)
        self.settings_panel.set_style_border_width(0, 0)

        # Row for network status
        network_row = lv.obj(self.settings_panel)
        network_row.set_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT)
        network_row.center()
        network_row.set_flex_flow(lv.FLEX_FLOW.ROW)
        network_row.set_flex_align(
            lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER
        )
        network_row.set_style_bg_opa(0, 0)
        network_row.set_style_border_width(0, 0)
        network_row.set_style_pad_all(0, 0)
        network_row.set_style_pad_column(10, 0)

        self.wifi_icon = lv.label(network_row)
        self.wifi_icon.set_text(f"{lv.SYMBOL.WIFI}")
        self.wifi_icon.align(lv.ALIGN.TOP_LEFT, 0, 0)
        self.wifi_icon.set_style_text_font(lv.font_montserrat_24, 0)
        self.wifi_icon.set_style_text_color(lv.color_make(255, 255, 255), 0)

        self.ifconfig_label = lv.label(network_row)
        self.ifconfig_label.align(lv.ALIGN.TOP_LEFT, 37, 5)
        self.ifconfig_label.set_style_text_color(lv.color_make(255, 255, 255), 0)

        # Row for battery/charging status
        battery_row = lv.obj(self.settings_panel)
        battery_row.set_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT)
        battery_row.center()
        battery_row.set_flex_flow(lv.FLEX_FLOW.ROW)
        battery_row.set_flex_align(
            lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER
        )
        battery_row.set_style_bg_opa(0, 0)
        battery_row.set_style_border_width(0, 0)
        battery_row.set_style_pad_all(0, 0)
        battery_row.set_style_pad_column(10, 0)

        self.battery_icon = lv.label(battery_row)
        self.battery_icon.set_text(f"{lv.SYMBOL.BATTERY_FULL}")
        self.battery_icon.align(lv.ALIGN.TOP_LEFT, 0, 40)
        self.battery_icon.set_style_text_font(lv.font_montserrat_24, 0)
        self.battery_icon.set_style_text_color(lv.color_make(255, 255, 255), 0)

        self.battery_label = lv.label(battery_row)
        self.battery_label.align(lv.ALIGN.TOP_LEFT, 37, 45)
        self.battery_label.set_style_text_color(lv.color_make(255, 255, 255), 0)

        self.wifi_icon_alternate = 1

        return self.settings_tile

    def led_tick(self, timer):
        for i in range(len(self.leds)):
            r, g, b, brightness = self.leds[i].tick()

            self.tlc5947.set_rgb_brightness(
                self.leds[i].channel, r, g, b, brightness=brightness, gamma=2.2
            )

        self.tlc5947.write()
        state, percentage = self.battery_state.get_battery_state()
        self.battery_icon.set_text(self._battery_icon_for(state, percentage))
        self.battery_label.set_text(
            f"{percentage}% ({self.battery_state.get_battery_voltage():.2f} V)"
        )

    def _update_fire_icon(self, fire_state):
        file_names = {
            FireState.EXTINGUISHED: "extinguished",
            FireState.HEALTHY: "healthy",
            FireState.CORRUPTED: "corrupted",
            FireState.EVERBURNING: "everburning",
            FireState.ETHEREAL: "ethereal",
        }
        name = file_names.get(fire_state, "healthy")
        self.fire_icon.set_src(f"M:assets/flame_{name}.bin")

    def fire_icon_event_cb(self, e):
        current_state = self.game_state.fire_states[self.game_state.current_location]
        next_state = (current_state + 1) % (FireState.ETHEREAL + 1)
        self.game_state.set_fire_state(self.game_state.current_location, next_state)

    def image_event_cb(self, e):
        gesture = self.cst816s.get_gesture()
        current_idx = self.game_state.locations.index(self.game_state.current_location)
        if gesture == lv.DIR.LEFT:
            new_idx = (current_idx + 1) % len(self.game_state.locations)
            self.game_state.set_current_location(self.game_state.locations[new_idx])
            self.town_name_label.set_text(self.game_state.current_location)
        elif gesture == lv.DIR.RIGHT:
            new_idx = (current_idx - 1) % len(self.game_state.locations)
            self.game_state.set_current_location(self.game_state.locations[new_idx])
            self.town_name_label.set_text(self.game_state.current_location)

    def wifi_connection_cb(self, wlan):
        if wlan.isconnected():
            self.wifi_icon.set_style_text_color(lv.color_make(0, 255, 0), 0)
            self.ifconfig = wlan.ifconfig()
            self.ifconfig_label.set_text(f"IP: {self.ifconfig[0]}")
        else:
            color = 128 if self.wifi_icon_alternate else 255
            self.wifi_icon.set_style_text_color(lv.color_make(color, color, color), 0)
            self.wifi_icon_alternate = 1 - self.wifi_icon_alternate

    def game_event_handler(self, event_type: str, location: str, state):
        if event_type == "fire_state_change":
            for led in self.leds:
                if led.name == location:
                    led.set_fire_state(state)
            if location == self.game_state.current_location:
                self._update_fire_icon(state)
        elif event_type == "location_change":
            self.image.set_src(f"M:assets/{location.lower().replace(' ', '')}.bin")
            self.town_name_label.set_text(location)
            self._update_fire_icon(state)
