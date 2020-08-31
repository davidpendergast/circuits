import pygame
import traceback

import src.engine.sprites as sprites
import src.utils.util as util
import src.utils.artutils as artutils


class SpriteSheet:

    def __init__(self, sheet_id, filepath):
        self._sheet_id = sheet_id
        self._filepath = filepath

    def get_sheet_id(self):
        return self._sheet_id

    def get_draw_order(self):
        """
        sheets with a lower draw order will be drawn first. if one sheet relies on the
        sprites of another, it must return a higher number here to ensure it'll have
        access to those sprites when it's drawing itself.
        """
        return 0

    def get_filepath(self):
        return self._filepath

    def get_size(self, img_size):
        """
        sheets can override this to provide extra space for generated sprites.
        :param img_size: the size of the sheet's image on disk.
        """
        return img_size

    def draw_to_atlas(self, atlas, sheet, start_pos=(0, 0)):
        if atlas is not None and sheet is not None:
            atlas.blit(sheet, start_pos)


class FontCharacterSpriteLookup:

    def get_char(self, c):
        """returns: an ImageSprite for the character c, or None if one isn't defined."""
        return None


class FontSheet(SpriteSheet, FontCharacterSpriteLookup):

    def __init__(self, sheet_id, filename):
        SpriteSheet.__init__(self, sheet_id, filename)
        self._sprite_lookup = {}  # char -> ImageModel
        self._swap_chars = {}  # char -> char

        self.char_sizes = set()

    def set_swap_chars(self, mapping):
        self._swap_chars = mapping

    def set_char(self, c, model):
        self._sprite_lookup[c] = model
        if model is not None:
            self.char_sizes.add(model.size())

    def is_mono(self):
        """returns: whether the font is monospaced"""
        return len(self.char_sizes) <= 1

    def get_char(self, c):
        """returns: an ImageSprite for the character c, or None if one isn't defined."""
        if c in self._swap_chars:
            c = self._swap_chars[c]

        if c in self._sprite_lookup:
            return self._sprite_lookup[c]
        elif "?" in self._sprite_lookup:
            return self._sprite_lookup["?"]
        else:
            return None


class DefaultFontMono(FontSheet):

    SHEET_ID = "default_font_mono"

    def __init__(self, font_id=None):
        FontSheet.__init__(self, DefaultFontMono.SHEET_ID if font_id is None else font_id, "assets/font.png")

        self.set_swap_chars({
            "→": chr(16),
            "←": chr(17),
            "↑": chr(24),
            "↓": chr(25)
        })

    def xform_char_rect(self, r, sheet):
        return r

    def draw_to_atlas(self, atlas, sheet, start_pos=(0, 0)):
        super().draw_to_atlas(atlas, sheet, start_pos=start_pos)
        if sheet is None:
            return

        # it's a 32x8 grid of characters
        char_w = round(sheet.get_width() / 32)
        char_h = round(sheet.get_height() / 8)
        for y in range(0, 8):
            for x in range(0, 32):
                c = chr(y * 32 + x)
                rect = [x * char_w, y * char_h, char_w, char_h]
                rect = self.xform_char_rect(rect, sheet)
                if rect is None or rect[2] == 0:
                    self.set_char(c, None)
                else:
                    self.set_char(c, sprites.ImageModel(rect[0], rect[1], rect[2], rect[3], offset=start_pos))


class DefaultFont(DefaultFontMono):

    SHEET_ID = "default_font"

    def __init__(self):
        DefaultFontMono.__init__(self, DefaultFont.SHEET_ID)

    def xform_char_rect(self, rect, sheet):
        r = artutils.find_bounding_rect(rect, sheet, keep_vert=True)
        if r is not None and r[2] > 0:
            return util.rect_expand(r, right_expand=1)
        else:
            return None


class DefaultFontSmall(FontSheet):

    SHEET_ID = "font_small"

    def __init__(self):
        FontSheet.__init__(self, DefaultFontSmall.SHEET_ID, "assets/font_small.png")

    def draw_to_atlas(self, atlas, sheet, start_pos=(0, 0)):
        super().draw_to_atlas(atlas, sheet, start_pos=start_pos)
        if sheet is None:
            return

        # it's a 32x8 grid of characters
        char_w = round(sheet.get_width() / 32)
        char_h = round(sheet.get_height() / 8)
        for y in range(0, 8):
            for x in range(0, 32):
                c = chr(y * 32 + x)
                grid_cell = [x * char_w, y * char_h, char_w, char_h]
                true_rect = artutils.find_bounding_rect(grid_cell, sheet, keep_vert=True)
                print("INFO: found c={} --> {}".format(c, true_rect))
                if true_rect[2] == 0:
                    self.set_char(c, None)
                else:
                    true_rect = util.rect_expand(true_rect, right_expand=1)
                    img = sprites.ImageModel(true_rect[0], true_rect[1], true_rect[2], true_rect[3], offset=start_pos)
                    self.set_char(c, img)


class WhiteSquare(SpriteSheet):
    """this is used by triangle sprites..."""

    SHEET_ID = "white_square"

    def __init__(self):
        SpriteSheet.__init__(self, WhiteSquare.SHEET_ID, None)

        self.white_box = None

    def get_size(self, img_size):
        return (32, 32)

    def draw_to_atlas(self, atlas, sheet, start_pos=(0, 0)):
        w, h = self.get_size((0, 0))
        rect = [start_pos[0], start_pos[1], w, h]
        pygame.draw.rect(atlas, (255, 255, 255), rect)

        self.white_box = sprites.ImageModel(0, 0, w, h, offset=start_pos)


class SingleImageSheet(SpriteSheet):

    def __init__(self, filepath):
        SpriteSheet.__init__(self, filepath, filepath)
        self._img = None

    def get_size(self, img_size):
        return img_size

    def get_img(self):
        return self._img

    def draw_to_atlas(self, atlas, sheet, start_pos=(0, 0)):
        super().draw_to_atlas(atlas, sheet, start_pos=start_pos)

        self._img = sprites.ImageModel(0, 0, sheet.get_width(), sheet.get_height(), offset=start_pos)


_SINGLETON = None


def create_instance():
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = SpriteAtlas()
        return _SINGLETON
    else:
        raise ValueError("SpriteAtlas has already been created")


def get_instance():
    return _SINGLETON


class SpriteAtlas:

    def __init__(self):
        self._sheets = {}  # sheet_id -> SpriteSheet

        # some "built-in" sheets
        self.add_sheet(DefaultFont())
        self.add_sheet(DefaultFontMono())
        self.add_sheet(DefaultFontSmall())

        self.add_sheet(WhiteSquare())

    def add_sheet(self, sheet):
        self._sheets[sheet.get_sheet_id()] = sheet

    def get_sheet(self, sheet_id):
        if sheet_id in self._sheets:
            return self._sheets[sheet_id]
        else:
            return None

    def create_atlas_surface(self):
        print("INFO: creating sprite atlas for {} sheets: [{}]".format(
            len(self._sheets), ", ".join([s_id for s_id in self._sheets])))

        sizes = {}  # sheet_id -> (w, h)
        all_non_empty_sizes = []

        loaded_images = {}  # sheet_id -> Surface or None
        for s_id in self._sheets:
            rel_path = self._sheets[s_id].get_filepath()
            if rel_path is None:
                loaded_images[s_id] = None
            else:
                resource_path = util.resource_path(rel_path)
                try:
                    loaded_images[s_id] = pygame.image.load(resource_path)
                except Exception:
                    print("ERROR: failed to load sprite sheet {} from path: {}".format(s_id, resource_path))
                    traceback.print_exc()
                    loaded_images[s_id] = None

        for s_id in self._sheets:
            img_size = (0, 0)
            if loaded_images[s_id] is not None:
                img_size = loaded_images[s_id].get_size()

            s_size = self._sheets[s_id].get_size(img_size)
            sizes[s_id] = s_size
            if s_size[0] > 0 and s_size[1] > 0:
                all_non_empty_sizes.append(s_size)
            else:
                print("WARN: sprite sheet {} has empty or invalid size: {}".format(s_id, s_size))

        packed_rects, atlas_size = util.pack_rects_into_smallest_rect(all_non_empty_sizes)

        packed_rects_set = set()
        for r in packed_rects:
            packed_rects_set.add(tuple(r))

        positions = {}  # sheet_id -> (x, y)
        for s_id in self._sheets:
            my_rect = None

            for r in packed_rects_set:
                if r[2] == sizes[s_id][0] and r[3] == sizes[s_id][1]:
                    positions[s_id] = (r[0], r[1])
                    my_rect = r
                    break

            if my_rect is not None:
                packed_rects_set.remove(my_rect)
            else:
                positions[s_id] = (0, 0)  # "draw" invalid sheets at (0, 0)

        all_sheets = [s_id for s_id in self._sheets]
        all_sheets.sort(key=lambda s_id: self._sheets[s_id].get_draw_order())

        # XXX this is a big hack that tells all the ImageModels we're about to create what size
        # their texture is. They need to know because their GL texture coordinates use an "upward"
        # y-axis (and everything in my code uses the opposite), so they need to flip themselves.
        sprites._CURRENT_ATLAS_SIZE = atlas_size

        atlas_surface = pygame.Surface(atlas_size, pygame.SRCALPHA, 32)
        atlas_surface.fill((255, 255, 255, 0))

        for s_id in all_sheets:
            pos = positions[s_id]
            img = loaded_images[s_id]
            size = sizes[s_id]
            print("INFO:   drawing {} [{}x{}] to ({}, {})".format(s_id, size[0], size[1], pos[0], pos[1]))
            self._sheets[s_id].draw_to_atlas(atlas_surface, img, start_pos=pos)

        sprites.CURRENT_ATLAS_SIZE = None  # clean it up for good measure ~

        return atlas_surface




