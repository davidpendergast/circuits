
import re

_CUR_SPRITE_MODE = 0
_SPRITE_MODES = [
    ("all", re.compile(r".*")),
    ("rect_only", re.compile(r".*rect.*")),
    ("slope_only", re.compile(r".*slope.*"))
]


def toggle_debug_sprite_mode():
    global _CUR_SPRITE_MODE
    _CUR_SPRITE_MODE = (_CUR_SPRITE_MODE + 1) % len(_SPRITE_MODES)
    print("DEBUG: set sprite mode to: {}".format(_SPRITE_MODES[_CUR_SPRITE_MODE][0]))


def should_show_debug_sprite_with_name(name):
    if name is None:
        return True
    else:
        regex = _SPRITE_MODES[_CUR_SPRITE_MODE][1]
        return re.match(regex, name)
