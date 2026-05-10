"""WiFi connection helper using MicroPython's network module."""

import asyncio
import network


async def connect_to_wifi(ssid: str, password: str, wifi_connection_cb):
    wlan = network.WLAN()
    wlan.active(True)
    if not wlan.isconnected():
        print(f"Connecting to network {ssid}...")
        wlan.connect(ssid, password)
        while not wlan.isconnected():
            await asyncio.sleep_ms(500)
            wifi_connection_cb(wlan)

    wifi_connection_cb(wlan)
    print("Network connected:", wlan.ifconfig())
