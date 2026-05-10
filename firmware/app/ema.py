"""Exponential Moving Average (EMA) filter."""


class EMA:
    def __init__(self, alpha: float):
        self.alpha = alpha
        self.value = 0.0

    def update(self, new_value: float) -> float:
        self.value = (self.alpha * new_value) + ((1 - self.alpha) * self.value)
        return self.value
