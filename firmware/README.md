# Firmware

This directory contains the software for the ESP32-S3 that powers the project.

## Software stack

The ESP32-S3 runs the following software stack:

1. Base firmware: custom build of [lv_micropython](https://github.com/lvgl/lv_micropython) (a [MicroPython](https://micropython.org/) fork that includes LVGL UI library).
2. GC9A01 display driver: [gc9a01_mpy](https://github.com/russhughes/gc9a01_mpy) built as a MicroPython user module.
3. User interface: [LVGL v9.3](https://github.com/lvgl/lvgl).
4. HTTP server and API: [Microdot](https://github.com/miguelgrinberg/microdot).

## Structure

- app/ -- source for the Age of Umbra application, including LVGL-compatible image files for the assets.
- assets/ -- original image assets.
- patches/ -- patches for lv_micropython and gc9a01_mpy to enable some required functionality and fix incompatibilities.
- tools/ -- scripts and tools for testing.

## Prerequisites

**ESP-IDF**

[ESP-IDF ESP32 toolchain](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/get-started/index.html) [v5.2.2](https://github.com/espressif/esp-idf/tree/v5.2.2) (_specifically_) is required for building firmware for this device. Check out this version using:

```bash
git clone -b v5.2.2 --recursive https://github.com/espressif/esp-idf.git esp-idf-5.2.2
```

And follow the build instructions in that repo.

**mpremote**

[mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html) is a MicroPython tool for interacting with a device over serial, including copying files, and Python REPL. Install it via pip:

```bash
pip install --user mpremote
```

## Custom MicroPython firmware

A custom firmware image was built using:

1. [lv_micropython](https://github.com/lvgl/lv_micropython) commit `acfeb7b7ead9eedc636d2d82c8a8d9908ea5ffac`.
2. [gc9a01_mpy](https://github.com/russhughes/gc9a01_mpy) commit `6ceba791a462bc5764d8340c2af0d0c3f77fb4d3`.

**Check out lv_micropython and apply patch**

This patch is required to set a few build configurations, and enable the use of MicroPython's SoftSPI without specifying MISO pin, as we want to use this to drive the TLC5947 LED driver but it is a write-only device.

From within `firmware` directory:

```bash
git clone git@github.com:lvgl-micropython/lvgl_micropython.git lvmp
cd lvmp
git checkout acfeb7b7ead9eedc636d2d82c8a8d9908ea5ffac
git apply ../patches/lv_micropython/lvmp.patch
```

**Check out gc9a01_mpy and apply patch**

This patch is required to disable linking of `tjpg` library to avoid conflicts with it already linked into MicroPython.

From within `firmware` directory:

```bash
git clone git@github.com:russhughes/gc9a01_mpy.git
cd gc9a01_mpy
git checkout 6ceba791a462bc5764d8340c2af0d0c3f77fb4d3
git apply ../patches/gc9a01_mpy/gc9a01mpy.patch
```

**Build the firmware image**

From within `firmware` directory:

```bash
cd lvmp
git submodule update --init --recursive user_modules/lv_binding_micropython
make -C mp-cross
cd ports/esp32
make USER_C_MODULES=../../../gc9a01_mpy/src/micropython.cmake BOARD=ESP32_GENERIC_S3 LV_CFLAGS="-DLV_COLOR_DEPTH=16 -DLV_COLOR_16_SWAP=1" all
```

**Flash the firmware**

From within the `firmware` directory, erase and flash the new firmware:

```bash
esptool.py --chip esp32s3 --port <PORT> erase_flash
esptool.py --chip esp32s3 --port <PORT> write_flash -z 0x0 lvmp/ports/esp32/build-ESP32_GENERIC_S3/firmware.bin
```

## Age of Umbra app

**Set WiFi credentials**

Rename the template configuration file from `config.json.template` to `config.json` and enter your WiFi credentials so the device can connect.

**FIXME**: the app is liable to hang if it is unable to connect to WiFi.

**Install app**

To install the app on an ESP32-S3, copy the entire contents of `app/` to the root of the device using `mpremote`:

```bash
mpremote connect <PORT> fs cp -r app/. :
```

## Tools

**serve_http_app.py**

This runs the Microdot HTTP server locally for testing. It mocks out various device-specific functionality. Run it from the `firmware` directory:

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/app
python -m tools.serve_http_app
```

Access the app at http://localhost:5000.

## Asset attribution

- age_of_umbra.png -- from Darrington Press Daggerheart Age of Umbra mini-series, 2025 [announcement](https://darringtonpress.com/daggerheart-age-of-umbra-mini-series-coming-to-critical-role-may-29th/) (fair use).
- blacktower.png -- from "Chepstow Castle" by artist John Martin, [painted 1815](https://commons.wikimedia.org/wiki/File:John_Martin_-_Moonlight_-_Chepstow_Castle_-_Google_Art_Project.jpg).
- flame\_\* -- from [Flames SVG free download](https://svgcrown.com/download.php?category=flames&id=1) @ svgcrown.com.
- galestone.png -- from "Festivities in Windsor Castle" by artist Paul Sandby, [painted 1776](https://en.wikipedia.org/wiki/Guy_Fawkes_Night#/media/File:Windsor_castle_guyfawkesnight1776.jpg)
- paleburg.png -- from [Daggerheart Core Rulebook](https://www.daggerheart.com/buy/) p280 Chapter 5: The Age of Umbra, 2025 (fair use).
- ransfall.png -- from "Ruins of an Ancient City" by artist John Martin, [painted between 1810-1820](https://artsandculture.google.com/asset/ruins-of-an-ancient-city-john-martin-british-1789%E2%80%931854/dAHVu0DaiYAoIg?hl=en).
