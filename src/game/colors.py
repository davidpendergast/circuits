

def to_float(r, g, b):
    return (r / 256, g / 256, b / 256)


def to_int(rgb):
    res = (int(rgb[0] * 256), int(rgb[1] * 256), int(rgb[2] * 256))
    return (min(255, res[0]), min(255, res[1]), min(255, res[2]))


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


