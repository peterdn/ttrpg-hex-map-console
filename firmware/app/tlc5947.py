"""
MicroPython driver for TLC5947 24-channel 12-bit PWM LED driver,
configured for 8 RGB channels. Daisy chaining not currently supported.

NOTE: requires a custom build of MicroPython with SoftSPI modified
to not require the MISO pin, since the TLC5947 is write-only.
"""

from machine import Pin, SoftSPI
import time


class TLC5974:
    def __init__(self, clk_pin, data_pin, latch_pin, freq=400000):
        if isinstance(clk_pin, int):
            clk_pin = Pin(clk_pin, Pin.OUT)
        if isinstance(data_pin, int):
            data_pin = Pin(data_pin, Pin.OUT)
        if isinstance(latch_pin, int):
            latch_pin = Pin(latch_pin, Pin.OUT)

        self.clk = clk_pin
        self.data = data_pin
        self.latch = latch_pin

        self.pwm_data = bytearray([0x00] * 36)

        self.spi = SoftSPI(baudrate=freq, polarity=0, sck=self.clk, mosi=self.data)

    def write(self):
        self.latch.value(0)
        self.spi.write(self.pwm_data)
        self.latch.value(1)
        time.sleep_us(1)
        self.latch.value(0)

    def set_rgb(self, c: int, r: float, g: float, b: float):
        if c < 0 or c > 8:
            raise ValueError("Channel must be between 0 and 8")

        r = max(0.0, min(1.0, r))
        g = max(0.0, min(1.0, g))
        b = max(0.0, min(1.0, b))

        r = int(r * 4095)
        g = int(g * 4095)
        b = int(b * 4095)

        bidx = ((7 - c) * 36) // 8
        if (7 - c) * 36 % 8 == 0:
            self.pwm_data[bidx] = (r >> 4) & 0xFF
            self.pwm_data[bidx + 1] = ((r & 0x0F) << 4) | ((g >> 8) & 0x0F)
            self.pwm_data[bidx + 2] = g & 0xFF
            self.pwm_data[bidx + 3] = (b >> 4) & 0xFF
            self.pwm_data[bidx + 4] = ((b & 0x0F) << 4) | self.pwm_data[bidx + 4] & 0x0F
        else:
            self.pwm_data[bidx] = (self.pwm_data[bidx + 4] & 0xF0) | ((r >> 8) & 0x0F)
            self.pwm_data[bidx + 1] = r & 0xFF
            self.pwm_data[bidx + 2] = (g >> 4) & 0xFF
            self.pwm_data[bidx + 3] = ((g & 0x0F) << 4) | ((b >> 8) & 0x0F)
            self.pwm_data[bidx + 4] = b & 0xFF

    def set_rgb_brightness(
        self, c: int, r: float, g: float, b: float, brightness: float, gamma=1.0
    ):
        perceived_brightness = brightness**gamma

        self.set_rgb(
            c,
            r * perceived_brightness,
            g * perceived_brightness,
            b * perceived_brightness,
        )
