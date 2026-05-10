"""A simple profiling decorator to measure execution time of functions."""

import time


def profile(func):
    def wrapper(*args, **kwargs):
        start_time = time.ticks_ms()
        result = func(*args, **kwargs)
        end_time = time.ticks_ms()
        elapsed = time.ticks_diff(end_time, start_time)
        print(f"Function {func.__name__} executed in {elapsed}ms")
        return result

    return wrapper
