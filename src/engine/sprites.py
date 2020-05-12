
import src.engine.globaltimer as globaltimer

import math

from src.utils.util import Utils


UNIQUE_ID_CTR = 0


def gen_unique_id():
    """Note: this ain't threadsafe"""
    global UNIQUE_ID_CTR
    UNIQUE_ID_CTR += 1
    return UNIQUE_ID_CTR - 1


class SpriteTypes:
    IMAGE = "IMAGE"
    TRIANGLE = "TRIANGLE"


class _Sprite:

    def __init__(self, sprite_type, layer_id, uid=None):
        self._sprite_type = sprite_type
        self._layer_id = layer_id
        self._uid = gen_unique_id() if uid is None else uid

        self._last_modified_tick = globaltimer.tick_count()

    def last_modified_tick(self):
        return self._last_modified_tick

    def sprite_type(self):
        return self._sprite_type

    def layer_id(self):
        return self._layer_id

    def uid(self):
        return self._uid

    def is_parent(self):
        return False

    def all_sprites_nullable(self):
        yield

    def all_sprites(self):
        for spr in self.all_sprites_nullable():
            if spr is not None:
                yield spr

    def __repr__(self):
        return "_Sprite({}, {}, {})".format(self.sprite_type(), self.layer_id(), self.uid())


class TriangleSprite(_Sprite):

    def __init__(self, layer_id, p1=(0, 0), p2=(0, 0), p3=(0, 0), color=(1, 1, 1), depth=1, uid=None):
        _Sprite.__init__(self, SpriteTypes.TRIANGLE, layer_id, uid=uid)

        # (._.)
        import src.engine.spritesheets as spritesheets
        self._model = spritesheets.get_instance().get_sheet(spritesheets.WhiteSquare.SHEET_ID).white_box

        self._p1 = p1
        self._p2 = p2
        self._p3 = p3
        self._color = color
        self._depth = depth

    def points(self):
        return (self.p1(), self.p2(), self.p3())

    def p1(self):
        return self._p1

    def p2(self):
        return self._p2

    def p3(self):
        return self._p3

    def color(self):
        return self._color

    def depth(self):
        return self._depth

    def update(self, new_points=None, new_p1=None, new_p2=None, new_p3=None, new_color=None, new_depth=None):
        points = new_points if new_points is not None else self.points()
        p1 = new_p1 if new_p1 is not None else points[0]
        p2 = new_p2 if new_p2 is not None else points[1]
        p3 = new_p3 if new_p3 is not None else points[2]

        color = new_color if new_color is not None else self._color
        depth = new_depth if new_depth is not None else self._depth

        if (p1 == self._p1 and p2 == self._p2 and p3 == self._p3 and
                color == self._color and
                depth == self._depth):
            return self
        else:
            return TriangleSprite(self.layer_id(), color=color, depth=depth, p1=p1, p2=p2, p3=p3, uid=self.uid())

    def add_urself(self, i, vertices, texts, colors, indices):
        p1 = self.p1()
        p2 = self.p2()
        p3 = self.p3()

        vertices[i * 6 + 0] = p1[0]
        vertices[i * 6 + 1] = p1[1]
        vertices[i * 6 + 2] = p2[0]
        vertices[i * 6 + 3] = p2[1]
        vertices[i * 6 + 4] = p3[0]
        vertices[i * 6 + 5] = p3[1]

        if colors is not None:
            rgb = self.color()
            for j in range(0, 9):
                colors[i * 9 + j] = rgb[j % 3]

        model = self._model
        if model is not None:
            for j in range(0, 3):
                texts[i * 6 + j * 2] = (model.tx1 + model.tx2) // 2
                texts[i * 6 + j * 2 + 1] = (model.ty1 + model.ty2) // 2

        indices[3 * i + 0] = 3 * i
        indices[3 * i + 1] = 3 * i + 1
        indices[3 * i + 2] = 3 * i + 2

    def __repr__(self):
        return "TriangleSprite({}, {}, {}, {}, {})".format(
             self.points(), self.layer_id(), self.color(), self.depth(), self.uid())
    

class ImageSprite(_Sprite):

    @staticmethod
    def new_sprite(layer_id, scale=1, depth=0):
        return ImageSprite(None, 0, 0, layer_id, scale=scale, depth=depth)

    def __init__(self, model, x, y, layer_id, scale=1, depth=1, xflip=False, rotation=0, color=(1, 1, 1), ratio=(1, 1), uid=None):
        _Sprite.__init__(self, SpriteTypes.IMAGE, layer_id, uid=uid)
        self._model = model
        self._x = x
        self._y = y
        self._scale = scale
        self._depth = depth
        self._xflip = xflip
        self._rotation = rotation
        self._color = color
        self._ratio = ratio
            
    def update(self, new_model=None, new_x=None, new_y=None, new_scale=None, new_depth=None,
               new_xflip=None, new_color=None, new_rotation=None, new_ratio=None):

        if isinstance(new_model, bool) and new_model is False:
            model = None
        else:
            model = self.model() if new_model is None else new_model

        x = self.x() if new_x is None else new_x
        y = self.y() if new_y is None else new_y
        scale = self.scale() if new_scale is None else new_scale
        depth = self.depth() if new_depth is None else new_depth
        xflip = self.xflip() if new_xflip is None else new_xflip
        color = self.color() if new_color is None else new_color
        rotation = self.rotation() if new_rotation is None else new_rotation
        ratio = self.ratio() if new_ratio is None else new_ratio
        
        if (model == self.model() and 
                x == self.x() and 
                y == self.y() and
                scale == self.scale() and
                depth == self.depth() and 
                xflip == self.xflip() and
                color == self.color() and
                ratio == self.ratio() and
                rotation == self.rotation()):
            return self
        else:
            res = ImageSprite(model, x, y, self.layer_id(), scale=scale, depth=depth, xflip=xflip, rotation=rotation,
                              color=color, ratio=ratio, uid=self.uid())
            return res
        
    def model(self):
        return self._model
    
    def x(self):
        return self._x
        
    def y(self):
        return self._y
        
    def width(self):
        if self.model() is None:
            return 0
        elif self.rotation() % 2 == 0:
            return self.model().width() * self.scale() * self.ratio()[0]
        else:
            return self.model().height() * self.scale() * self.ratio()[1]
        
    def height(self):
        if self.model() is None:
            return 0
        elif self.rotation() % 2 == 0:
            return self.model().height() * self.scale() * self.ratio()[1]
        else:
            return self.model().width() * self.scale() * self.ratio()[0]

    def size(self):
        return (self.width(), self.height())

    def scale(self):
        return self._scale
        
    def depth(self):
        return self._depth
        
    def xflip(self):
        return self._xflip

    def rotation(self):
        """returns: int: 0, 1, 2, or 3 representing a number of clockwise 90 degree rotations."""
        return self._rotation
        
    def color(self):
        return self._color

    def ratio(self):
        return self._ratio
        
    def add_urself(self, i, vertices, texts, colors, indices):
        """
            i: sprite's "index", which determines where in the arrays its data is written.
        """
        x = self.x()
        y = self.y()

        model = self.model()
        if model is None:
            w = 0
            h = 0
        else:
            w = model.w * self.scale() * self.ratio()[0]
            h = model.h * self.scale() * self.ratio()[1]

        if self.rotation() == 1 or self._rotation == 3:
            temp_w = w
            w = h
            h = temp_w

        vertices[i*8 + 0] = x
        vertices[i*8 + 1] = y
        vertices[i*8 + 2] = x
        vertices[i*8 + 3] = y + h
        vertices[i*8 + 4] = x + w
        vertices[i*8 + 5] = y + h
        vertices[i*8 + 6] = x + w
        vertices[i*8 + 7] = y

        if colors is not None:
            rgb = self.color()
            for j in range(0, 12):
                colors[i * 12 + j] = rgb[j % 3]

        if model is not None:
            corners = [
                model.tx1, model.ty2,
                model.tx1, model.ty1,
                model.tx2, model.ty1,
                model.tx2, model.ty2
            ]

            if self.xflip():
                corners[0] = model.tx2
                corners[2] = model.tx2
                corners[4] = model.tx1
                corners[6] = model.tx1

            for _ in range(0, self.rotation()):
                corners = corners[2:] + corners[:2]

            for j in range(0, 8):
                texts[i * 8 + j] = corners[j]

        indices[6 * i + 0] = 4 * i
        indices[6 * i + 1] = 4 * i + 1
        indices[6 * i + 2] = 4 * i + 2
        indices[6 * i + 3] = 4 * i
        indices[6 * i + 4] = 4 * i + 2
        indices[6 * i + 5] = 4 * i + 3

    def __repr__(self):
        return "ImageSprite({}, {}, {}, {}, {}, {}, {}, {}, {}. {})".format(
                self.model(), self.x(), self.y(), self.layer_id(),
                self.scale(), self.depth(), self.xflip(), self.color(), self.ratio(), self.uid())


_CURRENT_ATLAS_SIZE = None  # XXX this is a mega hack, just look away please


class ImageModel:

    def __init__(self, x, y, w, h, offset=(0, 0), texture_size=None):
        # sheet coords, origin top left corner
        self.x = x + offset[0]
        self.y = y + offset[1]
        self.w = w
        self.h = h
        self._rect = (self.x, self.y, self.w, self.h)

        tex_size = texture_size if texture_size is not None else _CURRENT_ATLAS_SIZE
        if tex_size is None:
            raise ValueError("can't construct an ImageModel without a texture size")

        # texture coords, origin bottom left corner
        self.tx1 = self.x
        self.ty1 = tex_size[1] - (self.y + self.h)
        self.tx2 = self.x + self.w
        self.ty2 = tex_size[1] - self.y
        
    def rect(self):
        return self._rect
        
    def size(self):
        return (self.w, self.h)
        
    def width(self):
        return self.w
        
    def height(self):
        return self.h
        
    def __repr__(self):
        return "ImageModel({}, {}, {}, {})".format(self.x, self.y, self.w, self.h)


class MultiSprite(_Sprite):

    def __init__(self, sprite_type, layer_id):
        _Sprite.__init__(self, sprite_type, layer_id)

    def is_parent(self):
        return True

    def all_sprites_nullable(self):
        raise NotImplementedError()

    def last_modified_tick(self):
        return max(spr.last_modified_tick() for spr in self.all_sprites())

    def __repr__(self):
        return type(self).__name__ + "({}, {})".format(self.sprite_type(), self.layer_id())


class LineSprite(MultiSprite):
    """two triangles next to each other"""

    def __init__(self, layer_id, p1=(0, 0), p2=(0, 0), thickness=1, color=(1, 1, 1), depth=1):
        MultiSprite.__init__(self, SpriteTypes.TRIANGLE, layer_id)
        self._p1 = p1
        self._p2 = p2
        self._thickness = thickness
        self._color = color
        self._depth = depth

        self._triangle1 = TriangleSprite(self.layer_id())  # butt is at p1
        self._triangle2 = TriangleSprite(self.layer_id())
        self._update_triangles()

    def all_sprites_nullable(self):
        yield self._triangle1
        yield self._triangle2

    def p1(self):
        return self._p1

    def p2(self):
        return self._p2

    def color(self):
        return self._color

    def thickness(self):
        return self._thickness

    def depth(self):
        return self._depth

    def update(self, new_p1=None, new_p2=None, new_thickness=None, new_color=(1, 1, 1), new_depth=1):
        did_change = False
        if new_p1 is not None and new_p1 != self._p1:
            self._p1 = new_p1
            did_change = True

        if new_p2 is not None and new_p2 != self._p2:
            self._p2 = new_p2
            did_change = True

        if new_thickness is not None and new_thickness != self._thickness:
            self._thickness = new_thickness
            did_change = True

        if new_color is not None and new_color != self._color:
            self._color = new_color
            did_change = True

        if new_depth is not None and new_depth != self._depth:
            self._depth = new_depth
            did_change = True

        if did_change:
            self._update_triangles()

        return self

    def _update_triangles(self):
        p1 = self.p1()
        p2 = self.p2()
        if p1 == p2:
            self._triangle1 = self._triangle1.update(new_points=(p1, p1, p1), new_color=self.color(), new_depth=self.depth())
            self._triangle2 = self._triangle2.update(new_points=(p1, p1, p1), new_color=self.color(), new_depth=self.depth())
        else:
            thickness = self.thickness()
            color = self.color()

            line_vec = Utils.sub(p2, p1)
            ortho_up = Utils.set_length(Utils.rotate(line_vec, 3.141529 / 2), thickness // 2)
            ortho_down = Utils.set_length(Utils.rotate(line_vec, -3.141529 / 2), int(0.5 + thickness / 2))

            #  r1-------r2
            #  p1     - p2
            #  |  -      |
            #  r4-------r3
            r1 = Utils.sum([p1, ortho_up])
            r2 = Utils.sum([p1, line_vec, ortho_up])
            r3 = Utils.sum([p1, line_vec, ortho_down])
            r4 = Utils.sum([p1, ortho_down])

            self._triangle1 = self._triangle1.update(new_points=(r1, r2, r4), new_color=color, new_depth=self.depth())
            self._triangle2 = self._triangle2.update(new_points=(r3, r4, r2), new_color=color, new_depth=self.depth())

    def __repr__(self):
        return type(self).__name__ + "({}, {})".format(self.p1(), self.p2())


class RectangleSprite(MultiSprite):

    def __init__(self, layer_id, x, y, w, h, color=(1, 1, 1), depth=1):
        MultiSprite.__init__(self, SpriteTypes.TRIANGLE, layer_id)
        self._x = x
        self._y = y
        self._w = w
        self._h = h
        self._color = color
        self._depth = depth

        self._top_left_sprite = None
        self._bottom_right_sprite = None

        self._build_sprites()

    def get_rect(self):
        return (self._x, self._y, self._w, self._h)

    def _build_sprites(self):
        if self._top_left_sprite is None:
            self._top_left_sprite = TriangleSprite(self.layer_id())
        self._top_left_sprite = self._top_left_sprite.update(
                                                   new_p1=(self._x, self._y),
                                                   new_p2=(self._x + self._w, self._y),
                                                   new_p3=(self._x, self._y + self._h),
                                                   new_color=self._color,
                                                   new_depth=self._depth)
        if self._bottom_right_sprite is None:
            self._bottom_right_sprite = TriangleSprite(self.layer_id())
        self._bottom_right_sprite = self._bottom_right_sprite.update(
                                                   new_p1=(self._x + self._w, self._y + self._h),
                                                   new_p2=(self._x, self._y + self._h),
                                                   new_p3=(self._x + self._w, self._y),
                                                   new_color=self._color,
                                                   new_depth=self._depth)

    def update(self, new_x=None, new_y=None, new_w=None, new_h=None, new_color=None, new_depth=None):
        did_change = False

        if new_x is not None and new_x != self._x:
            did_change = True
            self._x = new_x
        if new_y is not None and new_y != self._y:
            did_change = True
            self._y = new_y
        if new_w is not None and new_w != self._w:
            did_change = True
            self._w = new_w
        if new_h is not None and new_h != self._h:
            did_change = True
            self._h = new_h
        if new_color is not None and new_color != self._color:
            did_change = True
            self._color = new_color
        if new_depth is not None and new_depth != self._depth:
            did_change = True
            self._depth = new_depth

        if did_change:
            self._build_sprites()

        return self

    def all_sprites_nullable(self):
        yield self._top_left_sprite
        yield self._bottom_right_sprite


class TextSprite(MultiSprite):

    DEFAULT_X_KERNING = 0
    DEFAULT_Y_KERNING = 0

    def __init__(self, layer_id, x, y, text, scale=1.0, depth=0, color=(1, 1, 1), color_lookup=None, font_lookup=None,
                 x_kerning=DEFAULT_X_KERNING, y_kerning=DEFAULT_Y_KERNING):

        MultiSprite.__init__(self, SpriteTypes.IMAGE, layer_id)
        self._x = x
        self._y = y
        self._text = text
        self._scale = scale
        self._depth = depth
        self._base_color = color
        self._color_lookup = color_lookup if color_lookup is not None else {}
        self._x_kerning = x_kerning
        self._y_kerning = y_kerning

        if font_lookup is not None:
            self._font_lookup = font_lookup
        else:
            import src.engine.spritesheets as spritesheets  # (.-.)
            self._font_lookup = spritesheets.get_instance().get_sheet(spritesheets.DefaultFont.SHEET_ID)

        # this stuff is calculated by _build_character_sprites
        self._character_sprites = []
        self._bounding_rect = [0, 0, 0, 0]
        self._unused_sprites = []  # TODO delete

        self._build_character_sprites()

    def get_rect(self):
        return self._bounding_rect

    def get_size(self):
        return self._bounding_rect[2], self._bounding_rect[3]

    def _build_character_sprites(self):
        a_character = self._font_lookup.get_char("a")
        char_size = a_character.size()

        # we're going to reuse these if possible
        old_sprites = []
        old_sprites.extend(self._unused_sprites)
        self._unused_sprites.clear()

        self._character_sprites.reverse()
        old_sprites.extend(self._character_sprites)
        self._character_sprites.clear()

        self._bounding_rect = [self._x, self._y, 0, 0]

        cur_x = self._x
        cur_y = self._y

        for idx in range(0, len(self._text)):
            character = self._text[idx]
            if character == "\n":
                cur_x = self._x
                cur_y += math.ceil(char_size[1] * self._scale) + self._y_kerning
            else:
                char_model = self._font_lookup.get_char(character)
                if char_model is not None:
                    if len(old_sprites) > 0:
                        next_sprite = old_sprites.pop()
                    else:
                        next_sprite = ImageSprite.new_sprite(self.layer_id())

                    char_color = self._base_color if idx not in self._color_lookup else self._color_lookup[idx]

                    char_sprite = next_sprite.update(new_model=char_model, new_x=cur_x, new_y=cur_y,
                                                     new_scale=self._scale, new_depth=self._depth,
                                                     new_color=char_color)

                    self._character_sprites.append(char_sprite)

                    self._bounding_rect[2] = max(self._bounding_rect[2], char_sprite.x() + char_sprite.width() - self._bounding_rect[0])
                    self._bounding_rect[3] = max(self._bounding_rect[3], char_sprite.y() + char_sprite.height() - self._bounding_rect[1])
                    cur_x += char_sprite.width() + self._x_kerning
                else:
                    self._bounding_rect[2] = max(self._bounding_rect[2], cur_x + math.ceil(char_size[0] * self._scale) - self._bounding_rect[0])
                    self._bounding_rect[3] = max(self._bounding_rect[3], cur_y + math.ceil(char_size[1] * self._scale) - self._bounding_rect[1])
                    cur_x += math.ceil(char_size[0] * self._scale) + self._x_kerning

        for spr in old_sprites:
            spr = spr.update(new_model=False, new_x=self._bounding_rect[0], new_y=self._bounding_rect[1] + 16)
            self._unused_sprites.append(spr)

    def update(self, new_x=None, new_y=None, new_text=None, new_scale=None, new_depth=None,
               new_color=None, new_color_lookup=None, new_font_lookup=None,
               new_x_kerning=None, new_y_kerning=None):

        did_change = False

        if new_x is not None and new_x != self._x:
            did_change = True
            self._x = new_x
        if new_y is not None and new_y != self._y:
            did_change = True
            self._y = new_y
        if new_text is not None and new_text != self._text:
            did_change = True
            self._text = new_text
        if new_scale is not None and new_scale != self._scale:
            did_change = True
            self._scale = new_scale
        if new_depth is not None and new_depth != self._depth:
            did_change = True
            self._depth = new_depth
        if new_color is not None and new_color != self._base_color:
            did_change = True
            self._base_color = new_color
        if new_color_lookup is not None and new_color_lookup != self._color_lookup:
            did_change = True
            self._color_lookup = new_color_lookup
        if new_font_lookup is not None and new_font_lookup != self._font_lookup:
            did_change = True
            self._font_lookup = new_font_lookup
        if new_x_kerning is not None and new_x_kerning != self._x_kerning:
            did_change = True
            self._x_kerning = new_x_kerning
        if new_y_kerning is not None and new_y_kerning != self._y_kerning:
            did_change = True
            self._y_kerning = new_y_kerning

        if did_change:
            self._build_character_sprites()

        return self

    def all_sprites_nullable(self):
        for spr in self._character_sprites:
            yield spr
        for spr in self._unused_sprites:  # big yikes
            yield spr

    def __repr__(self):
        return type(self).__name__ + "({}, {}, {})".format(self._x, self._y, self._text.replace("\n", "\\n"))

    @staticmethod
    def wrap_text_to_fit(text, width, scale=1, font_lookup=None, x_kerning=DEFAULT_X_KERNING):
        if font_lookup is None:
            import src.engine.spritesheets as spritesheets  # (.-.)
            font_lookup = spritesheets.get_instance().get_sheet(spritesheets.DefaultFont.SHEET_ID)

        if "\n" in text:
            lines = text.split("\n")
            res = []
            for line in lines:
                for subline in TextSprite.wrap_text_to_fit(line, width, scale=scale, font_lookup=font_lookup, x_kerning=x_kerning):
                    res.append(subline)
            return res
        else:
            # at this point, text contains no newlines
            res = []
            letter_width = font_lookup.get_char("a").width() * scale + x_kerning

            words = text.split(" ")  # FYI if you have repeated spaces this will delete them
            cur_line = []
            cur_width = 0

            for w in words:
                if len(w) == 0:
                    continue
                else:
                    word_width = len(w) * letter_width
                    if len(cur_line) == 0:
                        cur_line.append(w)
                        cur_width = word_width
                    elif cur_width + letter_width + word_width > width / scale:
                        # gotta wrap
                        res.append(" ".join(cur_line))
                        cur_line.clear()
                        cur_line.append(w)
                        cur_width = word_width
                    else:
                        cur_line.append(w)
                        cur_width += letter_width + word_width

            if len(cur_line) > 0:
                res.append(" ".join(cur_line))

            return res


class TextBuilder:

    def __init__(self):
        self.text = ""
        self.colors = {}

    def add(self, new_text, color=None):
        if color is not None:
            for i in range(0, len(new_text)):
                self.colors[len(self.text) + i] = color
        self.text += new_text
        return self

    def addLine(self, new_text, color=None):
        return self.add(new_text + "\n", color=color)

    def __repr__(self):
        return "TextBuilder({}, {})".format(self.text, self.colors)


class BorderBoxSprite(MultiSprite):

    def __init__(self, layer_id, rect,
                 top_left=None, top=None, top_right=None,
                 left=None, center=None, right=None,
                 bottom_left=None, bottom=None, bottom_right=None,
                 all_borders=None,
                 scale=1, color=(1, 1, 1), depth=0, bg_color=None):
        """
        rect: the inner rectangle of the box
        """
        MultiSprite.__init__(self, SpriteTypes.IMAGE, layer_id)

        self._rect = rect
        self._color = color
        self._bg_color = color if bg_color is None else bg_color
        self._scale = scale
        self._depth = depth

        self._top_left_model = all_borders[0] if all_borders is not None else top_left
        self._top_model = all_borders[1] if all_borders is not None else top
        self._top_right_model = all_borders[2] if all_borders is not None else top_right

        self._left_model = all_borders[3] if all_borders is not None else left
        self._center_model = all_borders[4] if all_borders is not None else center
        self._right_model = all_borders[5] if all_borders is not None else right

        self._bottom_left_model = all_borders[6] if all_borders is not None else bottom_left
        self._bottom_model = all_borders[7] if all_borders is not None else bottom
        self._bottom_right_model = all_borders[8] if all_borders is not None else bottom_right

        self._top_left_sprite = None
        self._top_sprite = None
        self._top_right_sprite = None

        self._left_sprite = None
        self._center_sprite = None
        self._right_sprite = None

        self._bottom_left_sprite = None
        self._bottom_sprite = None
        self._bottom_right_sprite = None

        self._build_sprites()

    def _anchor_corner_to(self, corner_model, anchor_at, corner_sprite, pos):
        if corner_model is None and corner_sprite is None:
            return None
        elif corner_model is None:
            return corner_sprite.update(new_x=pos[0], new_y=pos[1], new_model=False)

        if corner_sprite is None:
            corner_sprite = ImageSprite.new_sprite(self.layer_id())

        sprite_x = pos[0] if anchor_at[0] == 0 else (pos[0] - corner_model.width() * self._scale)
        sprite_y = pos[1] if anchor_at[1] == 0 else (pos[1] - corner_model.height() * self._scale)

        return corner_sprite.update(new_model=corner_model, new_x=sprite_x, new_y=sprite_y, new_scale=self._scale,
                                    new_depth=self._depth, new_color=self._color)

    def _build_center_sprite(self, center_model, center_sprite):
        if center_model is None and center_sprite is None:
            return None
        elif center_model is None:
            return center_sprite.update(new_x=self._rect[0], new_y=self._rect[1], new_model=False)

        if center_sprite is None:
            center_sprite = ImageSprite.new_sprite(self.layer_id())

        x_ratio = self._rect[2] / center_model.width()
        y_ratio = self._rect[3] / center_model.height()

        return center_sprite.update(new_model=center_model, new_x=self._rect[0], new_y=self._rect[1],
                                    new_scale=1, new_depth=self._depth, new_color=self._bg_color,
                                    new_ratio=(x_ratio, y_ratio))

    def _anchor_vert_side_to(self, model, anchor_x_side, sprite, x_pos):
        if model is None and sprite is None:
            return None
        elif model is None:
            return sprite.update(new_x=x_pos, new_y=self._rect[1], new_model=False)

        if sprite is None:
            sprite = ImageSprite.new_sprite(self.layer_id())

        sprite_x = x_pos if anchor_x_side == 0 else (x_pos - model.width() * self._scale)
        y_ratio = self._rect[3] / model.height()

        return sprite.update(new_model=model, new_x=sprite_x, new_y=self._rect[1], new_scale=1, new_depth=self._depth,
                             new_ratio=(self._scale, y_ratio))

    def _anchor_horz_side_to(self, model, anchor_y_side, sprite, y_pos):
        if model is None and sprite is None:
            return None
        elif model is None:
            return sprite.update(new_x=self._rect[0], new_y=y_pos, new_model=False)

        if sprite is None:
            sprite = ImageSprite.new_sprite(self.layer_id())

        sprite_y = y_pos if anchor_y_side == 0 else (y_pos - model.height() * self._scale)
        x_ratio = self._rect[2] / model.width()

        return sprite.update(new_model=model, new_x=self._rect[0], new_y=sprite_y, new_scale=1, new_depth=self._depth,
                             new_ratio=(x_ratio, self._scale))

    def _build_sprites(self):
        x1 = self._rect[0]
        y1 = self._rect[1]
        x2 = self._rect[0] + self._rect[2]
        y2 = self._rect[1] + self._rect[3]

        self._top_left_sprite = self._anchor_corner_to(self._top_left_model, (1, 1), self._top_left_sprite, (x1, y1))
        self._top_right_sprite = self._anchor_corner_to(self._top_right_model, (0, 1), self._top_right_sprite, (x2, y1))
        self._bottom_left_sprite = self._anchor_corner_to(self._bottom_left_model, (1, 0), self._bottom_left_sprite, (x1, y2))
        self._bottom_right_sprite = self._anchor_corner_to(self._bottom_right_model, (0, 0), self._bottom_right_sprite, (x2, y2))

        self._center_sprite = self._build_center_sprite(self._center_model, self._center_sprite)

        self._left_sprite = self._anchor_vert_side_to(self._left_model, 1, self._left_sprite, x1)
        self._right_sprite = self._anchor_vert_side_to(self._right_model, 0, self._right_sprite, x2)

        self._top_sprite = self._anchor_horz_side_to(self._top_model, 1, self._top_sprite, y1)
        self._bottom_sprite = self._anchor_horz_side_to(self._bottom_model, 0, self._bottom_sprite, y2)

    def update(self, new_rect=None, new_scale=None, new_color=None, new_depth=None, new_bg_color=None):
        did_change = False
        if new_rect is not None and self._rect != new_rect:
            did_change = True
            self._rect = new_rect
        if new_scale is not None and self._scale != new_scale:
            did_change = True
            self._scale = new_scale
        if new_color is not None and self._color != new_color:
            did_change = True
            self._color = new_color
        if new_depth is not None and self._depth != new_depth:
            did_change = True
            self._depth = new_depth
        if new_bg_color is not None and self._bg_color != new_bg_color:
            did_change = True
            self._bg_color = new_bg_color

        if did_change:
            self._build_sprites()

        return self

    def all_sprites_nullable(self):
        yield self._top_left_sprite
        yield self._top_sprite
        yield self._top_right_sprite

        yield self._left_sprite
        yield self._center_sprite
        yield self._right_sprite

        yield self._bottom_left_sprite
        yield self._bottom_sprite
        yield self._bottom_right_sprite











