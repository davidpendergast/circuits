

def _bound(v, lower, upper):
    return max(min(v, upper), lower)


def to_float(r, g, b, a=None):
    rf = _bound(r / 256, 0, 1)
    gf = _bound(g / 256, 0, 1)
    bf = _bound(b / 256, 0, 1)
    if a is not None:
        return (rf, gf, bf, _bound(a / 256, 0, 1))
    else:
        return (rf, gf, bf)


def to_floatn(color):
    return tuple(_bound(v / 255, 0, 1) for v in color)


def to_int(r, g, b, a=None):
    ri = _bound(int(r * 256), 0, 255)
    gi = _bound(int(g * 256), 0, 255)
    bi = _bound(int(b * 256), 0, 255)
    if a is not None:
        return (ri, gi, bi, _bound(int(a * 256), 0, 255))
    else:
        return (ri, gi, bi)


def to_intn(color):
    return tuple(_bound(v * 256, 0, 255) for v in color)


PERFECT_WHITE = to_float(256, 256, 256)

PERFECT_LIGHT_GRAY = to_float(196, 196, 196)  # <--- skeletrisTM grays
PERFECT_DARK_GRAY = to_float(92, 92, 92)

PERFECT_VERY_DARK_GRAY = to_float(32, 32, 32)
PERFECT_BLACK = to_float(0, 0, 0)

PERFECT_RED = (1.0, 0.5, 0.5)
PERFECT_GREEN = (0.5, 1.0, 0.5)
PERFECT_BLUE = (0.5, 0.5, 1.0)
PERFECT_PINK = (1, 0.5, 1)
PERFECT_YELLOW = (1.0, 1.0, 117 / 256)
PERFECT_ORANGE = (1, 205 / 256, 117 / 256)


# in-game colors

WHITE = to_float(244, 244, 244)
LIGHT_GRAY = to_float(196, 196, 196)
DARK_GRAY = to_float(92, 92, 92)

BLUE = to_float(148, 176, 194)
DARK_BLUE = to_float(51, 60, 87)

GREEN = to_float(166, 231, 119)
DARK_GREEN = to_float(86, 123, 59)

TAN = to_float(256, 205, 117)
DARK_TAN = to_float(131, 108, 67)

PURPLE = to_float(228, 127, 253)
DARK_PURPLE = to_float(94, 56, 94)

# PURPLE = to_float(99, 228, 253)
# DARK_PURPLE = to_float(94, 56, 94)

EDITOR_SELECTION_COLOR = PERFECT_RED


