import pygame

import traceback

_CURRENT_CURSOR = None
_CUSTOM_CURSORS = {
    "default": pygame.cursors.arrow
}


def init_cursors(image_path, infos):
    """
    :param infos: list of (cursor_key, rect, hotspot), with hotspot relative to rect's corner
    """
    image = pygame.image.load(image_path)
    for info in infos:
        _CUSTOM_CURSORS[info[0]] = _sprite_to_cursor(info[1], image, hotspot=info[2])


def _get_cursor(cursor_key):
    if cursor_key is None:
        return _CUSTOM_CURSORS["default"]
    elif cursor_key in _CUSTOM_CURSORS:
        return _CUSTOM_CURSORS[cursor_key]
    else:
        raise ValueError("Unrecognized cursor key: {}".format(cursor_key))


_DISABLE_CUSTOM_CURSORS = False


def set_cursor(cursor_key):
    global _CURRENT_CURSOR
    if cursor_key == _CURRENT_CURSOR:
        return
    else:
        _CURRENT_CURSOR = cursor_key

    global _DISABLE_CUSTOM_CURSORS
    if _DISABLE_CUSTOM_CURSORS:
        return

    cursor_data = None
    try:
        cursor_data = _get_cursor(cursor_key)
        size, hotspot, xormasks, andmasks = cursor_data
        pygame.mouse.set_cursor(size, hotspot, xormasks, andmasks)
    except Exception:
        # I saw a bizarre crash here once, when calling pygame.mouse.set_cursor(*cursor_data)
        # in pygame 2.1.0 (SDL 2.0.16, Python 3.7.5):
        #   pygame.error: CreateIconIndirect(): The parameter is incorrect.
        # And I couldn't find anything about it online so I assume it's some rare pygame bug..?
        print("ERROR: failed to set cursor: {}={}".format(cursor_key, cursor_data))
        traceback.print_exc()

        # Just stop using custom cursors entirely
        _DISABLE_CUSTOM_CURSORS = True
        pygame.mouse.set_cursor(pygame.cursors.arrow)


def _sprite_to_cursor(cursor_rect, sheet, hotspot=(0, 0)):
    lines = []
    width = 8 * (cursor_rect[2] // 8)
    height = 8 * (cursor_rect[3] // 8)
    for y in range(0, height):
        lines.append("")
        for x in range(0, width):
            if x < cursor_rect[2] and y < cursor_rect[3]:
                pos = (cursor_rect[0] + x, cursor_rect[1] + y)
                c = sheet.get_at(pos)
                if c[3] == 0:
                    lines[-1] = lines[-1] + " "
                elif c[0] == 0:
                    lines[-1] = lines[-1] + "X"
                else:
                    lines[-1] = lines[-1] + "."
            else:
                lines[-1] = lines[-1] + " "

    and_and_xors = pygame.cursors.compile(lines, black="X", white=".", xor="o")
    return ((width, height), hotspot, and_and_xors[0], and_and_xors[1])
