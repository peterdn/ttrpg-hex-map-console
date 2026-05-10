"""Battery monitoring for the ESP32-S3-Touch-LCD-1.28 dev board."""

from machine import ADC

from ema import EMA

# Discharge voltage thresholds derived from empirical measurements.
# 3.15V=100%, 2.98V=80%, 2.84V=60%, 2.76V=40%, 2.70V=20%, <2.70V=0%
_DISCH_THRESHOLDS = (3.15, 2.98, 2.84, 2.76, 2.70)


class BatteryState:
    CHARGING = "charging"
    DISCHARGING = "discharging"

    def __init__(self):
        self._voltage_ema = EMA(alpha=0.01)

    def get_battery_voltage(self) -> float:
        adc = ADC(1, atten=ADC.ATTN_11DB)

        total = 0
        for _ in range(5):
            total += adc.read_u16()

        reading = total / 5
        conversion_factor = 3.3 / 65535 * 3

        voltage_value = reading * conversion_factor

        if abs(voltage_value - self._voltage_ema.value) > 0.5:
            self._voltage_ema.value = voltage_value
        else:
            self._voltage_ema.update(voltage_value)

        return round(self._voltage_ema.value, 2)

    def get_battery_state(self) -> Tuple[str, float]:
        # This board has no way to directly detect whether it is on USB power, running on battery,
        # charging, or discharging. Instead we infer the state from the voltage: if above 3.6V we
        # assume that it's on USB power and therefore charging. The % charge is then approximated
        # from the voltage. Voltage drops nonlinearly when discharging so a lookup table is used.
        observed = self.get_battery_voltage()

        if observed >= 3.6:
            # USB connected: observed 3.6V (uncharged) – 4.2V (full), 0.12V bands.
            state = BatteryState.CHARGING
            percentage = max(0, min(100, int((observed - 3.6) / 0.12 + 1e-9) * 20))
        else:
            # On battery: nonlinear lookup matched to empirical discharge curve.
            state = BatteryState.DISCHARGING
            percentage = 0
            for i, t in enumerate(_DISCH_THRESHOLDS):
                if observed >= t:
                    percentage = (5 - i) * 20
                    break

        return state, percentage
