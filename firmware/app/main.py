import asyncio
import gc
from machine import Pin, SPI

import gc9a01_drv
from battery import BatteryState
from cachefs_drv import CacheFS
from config import Config
from cst816s_drv import CST816S
from game_state import GameState
from http_app import HttpApp
from tlc5947 import TLC5947
from ui import UserInterface, ui_task
from wifi import connect_to_wifi

gc.enable()
gc.collect()


async def main():
    # set up display
    spi = SPI(2, baudrate=80000000, polarity=0, sck=Pin(10), mosi=Pin(11))
    display = gc9a01_drv.GC9A01(
        spi, 240, 240, reset=14, cs=9, dc=8, backlight=2, rotation=2
    )
    display.fill(gc9a01_drv.BLACK)

    # set up touch input
    cst816s = CST816S(scl=7, sda=6, rst=13, mirror_x=True, mirror_y=True)

    print("Device setup complete!")

    # set up file system and cache
    # NOTE: the variable is unused but the object sets up some global LVGL state
    cache_fs = CacheFS(cache_size=32768)

    tlc5947 = TLC5947(clk_pin=16, data_pin=17, latch_pin=18, freq=400000)

    battery_state = BatteryState()

    game_state = GameState()

    ui = UserInterface(cst816s, tlc5947, game_state, battery_state)

    config = Config("config.json")

    http_app = HttpApp(game_state, battery_state)

    server = asyncio.create_task(http_app.start_server())
    wifi_task = asyncio.create_task(
        connect_to_wifi(config.wifi_ssid, config.wifi_password, ui.wifi_connection_cb)
    )
    await asyncio.gather(ui_task(), server, wifi_task)


if __name__ == "__main__":
    asyncio.run(main())
