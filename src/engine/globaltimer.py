import time

_TICK_COUNT = 0

# used for fps tracking
_TICK_TIMES = [time.time()] * 10
_TICK_TIME_IDX = 0


def tick_count():
    """returns: How many 'ticks' the game has been running for. This number will never decrease on subsequent calls."""
    return _TICK_COUNT


def inc_tick_count():
    """
    It's pretty important that the game loop calls this once per frame (at the end, after rendering).
    src.engine.renderengine and src.engine.inputs specifically rely on this for their internal logic.
    """
    global _TICK_COUNT
    _TICK_COUNT += 1

    global _TICK_TIME_IDX
    _TICK_TIMES[_TICK_TIME_IDX] = time.time()
    _TICK_TIME_IDX = (_TICK_TIME_IDX + 1) % len(_TICK_TIMES)  # circular list


def get_fps():
    """returns: average fps of the last several frames."""
    min_time = min(_TICK_TIMES)
    max_time = max(_TICK_TIMES)
    elapsed_time = max_time - min_time
    if elapsed_time == 0:
        return 999
    else:
        return (len(_TICK_TIMES) - 1) / elapsed_time
