"""LVGL driver for CST816S I2C touch controller."""

from machine import Pin, I2C
from micropython import const
import time

import lvgl as lv

_CST816S_I2C_ADDR = const(0x15)

_CST816S_REG_FINGER_NUM = const(0x02)  # Finger count: 0 none, 1 one
_CST816S_REG_XPOSH = const(0x03)  # High 4 bits of X coordinate
_CST816S_REG_XPOSL = const(0x04)  # Low 8 bits of X coordinate
_CST816S_REG_YPOSH = const(0x05)  # High 4 bits of Y coordinate
_CST816S_REG_YPOSL = const(0x06)  # Low 8 bits of Y coordinate

_CST816S_REG_CHIP_ID = const(0xA7)
_CST816S_REG_FIRMWARE_VERSION = const(0xA9)
_CST816S_REG_DISABLE_SLEEP = const(0xFE)


class CST816S:
    def __init__(self, scl, sda, rst, freq=400000, mirror_x=False, mirror_y=False):
        self.i2c = I2C(
            0,
            scl=Pin(scl),
            sda=Pin(sda),
            freq=freq,
        )

        self.rst = Pin(rst, Pin.OUT)
        self.mirror_x = mirror_x
        self.mirror_y = mirror_y

        self.reset()
        self._verify_device()
        self.disable_sleep()

        # set up LVGL indev OBJECT
        if not lv.is_initialized():
            lv.init()

        self.lv_input_drv = lv.indev_create()
        self.lv_input_drv.set_type(lv.INDEV_TYPE.POINTER)
        self.lv_input_drv.set_read_cb(self._lv_read_cb)

    def _lv_read_cb(self, indev_drv, data):
        pos = self.touch_pos()
        if pos is None:
            data.state = lv.INDEV_STATE.RELEASED
        else:
            data.point.x = pos[0]
            data.point.y = pos[1]
            data.state = lv.INDEV_STATE.PRESSED

    def _i2c_write(self, register, data):
        self.i2c.writeto_mem(_CST816S_I2C_ADDR, register, data)

    def _i2c_read(self, register):
        data = bytearray(1)
        self.i2c.readfrom_mem_into(_CST816S_I2C_ADDR, register, data)
        return data[0]

    def touch_pos(self):
        finger_num = self._i2c_read(_CST816S_REG_FINGER_NUM)
        if finger_num == 0:
            return None

        xpos_h = self._i2c_read(_CST816S_REG_XPOSH) & 0x0F
        xpos_l = self._i2c_read(_CST816S_REG_XPOSL)
        ypos_h = self._i2c_read(_CST816S_REG_YPOSH) & 0x0F
        ypos_l = self._i2c_read(_CST816S_REG_YPOSL)

        x = (xpos_h << 8) | xpos_l
        y = (ypos_h << 8) | ypos_l

        if self.mirror_x:
            x = 240 - x
        if self.mirror_y:
            y = 240 - y

        return (x, y)

    def get_gesture(self):
        return self.lv_input_drv.get_gesture_dir()

    def reset(self):
        self.rst.value(0)
        time.sleep_ms(1)
        self.rst.value(1)
        time.sleep_ms(50)

    def disable_sleep(self):
        self._i2c_write(_CST816S_REG_DISABLE_SLEEP, b"\x01")

    def chip_id(self):
        return self._i2c_read(_CST816S_REG_CHIP_ID)

    def _verify_device(self):
        chip_id = self.chip_id()
        if chip_id != 0xB5:
            raise RuntimeError(f"Unexpected CST816S chip ID: 0x{chip_id:02X}")

    def firmware_version(self):
        return self._i2c_read(_CST816S_REG_FIRMWARE_VERSION)
