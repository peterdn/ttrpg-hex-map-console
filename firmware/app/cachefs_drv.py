"""
A read-only filesystem driver for LVGL that bridges to MicroPython's
built-in filesystem. Files are cached entirely in memory upon opening.
For obvious reasons this is not suitable for using with large files.
"""

import struct
import lvgl as lv


class CacheFS:
    def __init__(self, drive_letter="M", cache_size=4096):
        self.drive_letter = drive_letter
        self.files = {}
        self.positions = {}

        # Set up LVGL filesystem driver object
        if not lv.is_initialized():
            lv.init()

        self.fs_drv = lv.fs_drv_t()
        self.fs_drv.init()
        self.fs_drv.letter = ord(self.drive_letter)
        self.fs_drv.open_cb = self._lv_open_cb
        self.fs_drv.read_cb = self._lv_read_cb
        self.fs_drv.seek_cb = self._lv_seek_cb
        self.fs_drv.tell_cb = self._lv_tell_cb
        self.fs_drv.close_cb = self._lv_close_cb
        if cache_size >= 0:
            self.fs_drv.cache_size = cache_size

        self.fs_drv.register()

    def _lv_open_cb(self, drv, path, mode):
        if mode != lv.FS_MODE.RD:
            raise RuntimeError("Only read mode is supported")

        if path not in self.files:
            with open(path, "rb") as f:
                self.files[path] = f.read()

        self.positions[path] = 0
        return {"file": self.files[path], "path": path}

    def _lv_read_cb(self, drv, file, buf, btr, br):
        # Recast the opaque file object back to the
        # Python dict that we returned from _lv_open_cb
        file_data = file.__cast__()["file"]
        path = file.__cast__()["path"]
        position = self.positions[path]
        data = file_data[position : position + btr]

        self.positions[path] += len(data)

        # Copy the data into the C buffer provided by LGVL
        buf.__dereference__(btr)[0 : len(data)] = data

        # Write the number of bytes read back to the provided int pointer
        # The format string "<L" means little-endian unsigned long (4 bytes)
        br.__dereference__(4)[0:4] = struct.pack("<L", len(data))
        return lv.FS_RES.OK

    def _lv_seek_cb(self, drv, file, pos, whence):
        path = file.__cast__()["path"]

        if whence == 0:  # SEEK_SET
            self.positions[path] = pos
        elif whence == 1:  # SEEK_CUR
            self.positions[path] += pos
        elif whence == 2:  # SEEK_END
            self.positions[path] = len(file["file"]) + pos

        return lv.FS_RES.OK

    def _lv_tell_cb(self, drv, file, pos):
        path = file.__cast__()["path"]
        tpos = self.positions[path]
        pos.__dereference__(4)[0:4] = struct.pack("<L", tpos)
        return lv.FS_RES.OK

    def _lv_close_cb(self, drv, file):
        return lv.FS_RES.OK
