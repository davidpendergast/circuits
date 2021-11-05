import pygame

DEFAULT = pygame.cursors.arrow
HAND = None
INVISIBLE = None

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


def get_cursor(cursor_key):
    if cursor_key is None:
        return _CUSTOM_CURSORS["default"]
    elif cursor_key in _CUSTOM_CURSORS:
        return _CUSTOM_CURSORS[cursor_key]
    else:
        raise ValueError("Unrecognized cursor key: {}".format(cursor_key))


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

class Cursors:
    arrow_cursor_sprite = None
    hand_cursor_sprite = None
    invis_cursor_sprite = None

    arrow_cursor = None
    hand_cursor = None

    # need to use an invisible cursor instead of calling pygame.set_visible(False)
    # because there's a bug on linux where the cursor position jumps around when
    # you toggle its visibility in fullscreen mode.
    invisible_cursor = None

    @staticmethod
    def init_cursors(sheet):
        UI.Cursors.arrow_cursor = pygame.cursors.arrow  # it just looks better, sorry

        UI.Cursors.hand_cursor = UI.Cursors.sprite_to_cursor(UI.Cursors.hand_cursor_sprite.rect(),
                                                             sheet, hotspot=(5, 3))

        UI.Cursors.invisible_cursor = UI.Cursors.sprite_to_cursor(UI.Cursors.invis_cursor_sprite.rect(),
                                                                  sheet, hotspot=(0, 0))