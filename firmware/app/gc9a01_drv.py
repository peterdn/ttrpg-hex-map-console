"""LVGL driver for GC9A01 SPI display controller."""

from machine import Pin

from gc9a01 import *

import lvgl as lv


class GC9A01(GC9A01):
    def __init__(
        self,
        spi,
        width,
        height,
        reset,
        cs,
        dc,
        backlight,
        rotation=0,
        color_16_swap=False,
    ):
        self.color_16_swap = color_16_swap

        if isinstance(reset, int):
            reset = Pin(reset, Pin.OUT)
        if isinstance(cs, int):
            cs = Pin(cs, Pin.OUT)
        if isinstance(dc, int):
            dc = Pin(dc, Pin.OUT)
        if isinstance(backlight, int):
            backlight = Pin(backlight, Pin.OUT)

        super().__init__(
            spi=spi,
            width=width,
            height=height,
            reset=reset,
            cs=cs,
            dc=dc,
            backlight=backlight,
            rotation=rotation,
        )

        super().init()

        # Set up LVGL display driver object
        if not lv.is_initialized():
            lv.init()

        color_format = lv.COLOR_FORMAT.RGB565
        buf1 = lv.draw_buf_create(width, 240, color_format, 0)

        disp_drv = lv.display_create(width, height)
        disp_drv.color_format = color_format
        disp_drv.set_draw_buffers(buf1, None)
        disp_drv.set_render_mode(lv.DISPLAY_RENDER_MODE.PARTIAL)
        disp_drv.set_flush_cb(self._lv_flush_cb)

    def _lv_flush_cb(self, disp_drv, area, color_p):
        w = area.x2 - area.x1 + 1
        h = area.y2 - area.y1 + 1

        size = int(w * h)
        data = color_p.__dereference__(size * 2)

        if self.color_16_swap:
            lv.draw_sw_rgb565_swap(data, size)

        super().blit_buffer(bytes(data), area.x1, area.y1, w, h)
        disp_drv.flush_ready()
