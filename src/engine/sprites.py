
import src.engine.globaltimer as globaltimer

import math
import typing

import src.utils.util as util


UNIQUE_ID_CTR = 0


def gen_unique_id():
    """Note: this ain't threadsafe"""
    global UNIQUE_ID_CTR
    UNIQUE_ID_CTR += 1
    return UNIQUE_ID_CTR - 1


class SpriteTypes:
    IMAGE = "IMAGE"
    TRIANGLE = "TRIANGLE"
    THREE_DEE = "THREE_DEE"


class AbstractSprite:

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
        return "{}({}, {}, {})".format(type(self).__name__, self.sprite_type(), self.layer_id(), self.uid())


class TriangleSprite(AbstractSprite):

    def __init__(self, layer_id, p1=(0, 0), p2=(0, 0), p3=(0, 0), color=(1, 1, 1), depth=1, uid=None):
        AbstractSprite.__init__(self, SpriteTypes.TRIANGLE, layer_id, uid=uid)

        # (._.)
        import src.engine.spritesheets as spritesheets
        self._model = spritesheets.get_instance().get_sheet(spritesheets.WhiteSquare.SHEET_ID).get_sprite()

        self._p1 = p1
        self._p2 = p2
        self._p3 = p3
        self._color = color
        self._depth = depth

    def all_sprites_nullable(self):
        yield self

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

        z = self.depth() / 1000000

        vertices[i * 9 + 0] = p1[0]
        vertices[i * 9 + 1] = p1[1]
        vertices[i * 9 + 2] = z

        vertices[i * 9 + 3] = p2[0]
        vertices[i * 9 + 4] = p2[1]
        vertices[i * 9 + 5] = z

        vertices[i * 9 + 6] = p3[0]
        vertices[i * 9 + 7] = p3[1]
        vertices[i * 9 + 8] = z

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
    

class ImageSprite(AbstractSprite):

    @staticmethod
    def new_sprite(layer_id, scale=1, depth=0):
        return ImageSprite(None, 0, 0, layer_id, scale=scale, depth=depth)

    def __init__(self, model, x, y, layer_id, scale=1, depth=1, xflip=False, yflip=False, rotation=0, color=(1, 1, 1), ratio=(1, 1), raw_size=(-1, -1), uid=None):
        AbstractSprite.__init__(self, SpriteTypes.IMAGE, layer_id, uid=uid)
        self._model = model
        self._x = x
        self._y = y
        self._scale = scale
        self._depth = depth
        self._xflip = xflip
        self._yflip = yflip
        self._rotation = rotation
        self._color = color
        self._ratio = ratio
        self._raw_size = raw_size

    def all_sprites_nullable(self):
        yield self
            
    def update(self, new_model=None, new_x=None, new_y=None, new_scale=None, new_depth=None,
               new_xflip=None, new_yflip=None, new_color=None, new_rotation=None, new_ratio=None, new_raw_size=None):

        if isinstance(new_model, bool) and new_model is False:
            model = None
        else:
            model = self.model() if new_model is None else new_model

        x = self.x() if new_x is None else new_x
        y = self.y() if new_y is None else new_y
        scale = self.scale() if new_scale is None else new_scale
        depth = self.depth() if new_depth is None else new_depth
        xflip = self.xflip() if new_xflip is None else new_xflip
        yflip = self.yflip() if new_yflip is None else new_yflip
        color = self.color() if new_color is None else new_color
        rotation = self.rotation() if new_rotation is None else new_rotation
        ratio = self.ratio() if new_ratio is None else new_ratio
        raw_size = self.raw_size() if new_raw_size is None else new_raw_size
        
        if (model == self.model() and 
                x == self.x() and 
                y == self.y() and
                scale == self.scale() and
                depth == self.depth() and 
                xflip == self.xflip() and
                yflip == self.yflip() and
                color == self.color() and
                ratio == self.ratio() and
                rotation == self.rotation() and
                raw_size == self.raw_size()):
            return self
        else:
            res = ImageSprite(model, x, y, self.layer_id(), scale=scale, depth=depth, xflip=xflip, yflip=yflip,
                              rotation=rotation, color=color, ratio=ratio, raw_size=raw_size, uid=self.uid())
            return res
        
    def model(self):
        return self._model
    
    def x(self):
        return self._x
        
    def y(self):
        return self._y
        
    def width(self, with_rotations=True):
        if self.model() is None:
            return 0
        elif not with_rotations or self.rotation() % 2 == 0:
            raw_w = self.raw_size()[0]
            return raw_w if raw_w >= 0 else self.model().width() * self.scale() * self.ratio()[0]
        else:
            return self.height(with_rotations=False)
        
    def height(self, with_rotations=True):
        if self.model() is None:
            return 0
        elif not with_rotations or self.rotation() % 2 == 0:
            raw_h = self.raw_size()[1]
            return raw_h if raw_h >= 0 else self.model().height() * self.scale() * self.ratio()[1]
        else:
            return self.width(with_rotations=False)

    def size(self):
        return (self.width(), self.height())

    def rect(self):
        return (self.x(), self.y(), self.width(), self.height())

    def scale(self):
        return self._scale
        
    def depth(self):
        return self._depth
        
    def xflip(self):
        return self._xflip

    def yflip(self):
        return self._yflip

    def rotation(self):
        """returns: int: 0, 1, 2, or 3 representing a number of clockwise 90 degree rotations."""
        return self._rotation
        
    def color(self):
        return self._color

    def ratio(self):
        return self._ratio

    def raw_size(self):
        return self._raw_size
        
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

            raw_size = self.raw_size()
            if raw_size[0] >= 0: w = raw_size[0]
            if raw_size[1] >= 0: h = raw_size[1]

        if self.rotation() == 1 or self._rotation == 3:
            temp_w = w
            w = h
            h = temp_w

        z = self.depth() / 1000000

        vertices[i*12 + 0] = x
        vertices[i*12 + 1] = y
        vertices[i*12 + 2] = z

        vertices[i*12 + 3] = x
        vertices[i*12 + 4] = y + h
        vertices[i*12 + 5] = z

        vertices[i*12 + 6] = x + w
        vertices[i*12 + 7] = y + h
        vertices[i*12 + 8] = z

        vertices[i*12 + 9] = x + w
        vertices[i*12 + 10] = y
        vertices[i*12 + 11] = z

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

            if self.yflip():
                corners[1] = model.ty1
                corners[3] = model.ty2
                corners[5] = model.ty2
                corners[7] = model.ty1

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


_IMAGE_MODEL_UID_COUNTER = 0


def _get_next_model_uid():
    global _IMAGE_MODEL_UID_COUNTER
    _IMAGE_MODEL_UID_COUNTER += 1
    return _IMAGE_MODEL_UID_COUNTER - 1


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

        self._uid = _get_next_model_uid()
        
    def rect(self):
        return self._rect
        
    def size(self, scale=1):
        return (self.w * scale, self.h * scale)
        
    def width(self):
        return self.w
        
    def height(self):
        return self.h

    def uid(self):
        return self._uid
        
    def __repr__(self):
        return "ImageModel({}, {}, {}, {})".format(self.x, self.y, self.w, self.h)

    def __eq__(self, other):
        if isinstance(other, ImageModel):
            return self._uid == other._uid
        else:
            return False

    def __hash__(self):
        return hash(self._uid)


class MultiSprite(AbstractSprite):

    def __init__(self, sprite_type, layer_id):
        AbstractSprite.__init__(self, sprite_type, layer_id)

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

            line_vec = util.sub(p2, p1)
            ortho_up = util.set_length(util.rotate(line_vec, 3.141529 / 2), thickness // 2)
            ortho_down = util.set_length(util.rotate(line_vec, -3.141529 / 2), int(0.5 + thickness / 2))

            #  r1-------r2
            #  p1     - p2
            #  |  -      |
            #  r4-------r3
            r1 = util.sum_vecs([p1, ortho_up])
            r2 = util.sum_vecs([p1, line_vec, ortho_up])
            r3 = util.sum_vecs([p1, line_vec, ortho_down])
            r4 = util.sum_vecs([p1, ortho_down])

            self._triangle1 = self._triangle1.update(new_points=(r1, r2, r4), new_color=color, new_depth=self.depth())
            self._triangle2 = self._triangle2.update(new_points=(r3, r4, r2), new_color=color, new_depth=self.depth())

    def __repr__(self):
        return type(self).__name__ + "({}, {})".format(self.p1(), self.p2())


class RectangleSprite(MultiSprite):

    def __init__(self, layer_id, rect=None, x=0, y=0, w=0, h=0, color=(1, 1, 1), depth=1):
        MultiSprite.__init__(self, SpriteTypes.TRIANGLE, layer_id)
        if rect is not None:
            x = rect[0]
            y = rect[1]
            w = rect[2]
            h = rect[3]
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

    def update(self, new_rect=None, new_x=None, new_y=None, new_w=None, new_h=None, new_color=None, new_depth=None):
        did_change = False

        if new_rect is not None:
            new_x = new_rect[0]
            new_y = new_rect[1]
            new_w = new_rect[2]
            new_h = new_rect[3]

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


class RectangleOutlineSprite(MultiSprite):

    def __init__(self, layer_id, rect=None, x=0, y=0, w=0, h=0, outline=1, color=(1, 1, 1), depth=1):
        MultiSprite.__init__(self, SpriteTypes.TRIANGLE, layer_id)
        if rect is not None:
            x = rect[0]
            y = rect[1]
            w = rect[2]
            h = rect[3]
        self._x = x
        self._y = y
        self._w = w
        self._h = h
        self._outline = outline
        self._color = color
        self._depth = depth

        self._top_sprite = None
        self._bottom_sprite = None
        self._left_sprite = None
        self._right_sprite = None

        self._build_sprites()

    def _build_sprites(self):
        if self._outline <= 0:
            self._top_sprite = None
            self._bottom_sprite = None
            self._left_sprite = None
            self._right_sprite = None

        elif self._outline * 2 >= self._w or self._outline * 2 >= self._h:
            # outline is so thick that it fills the entire rectangle
            if self._top_sprite is None:
                self._top_sprite = RectangleSprite(self.layer_id())
            self._top_sprite.update(new_rect=[self._x, self._y, self._w, self._h],
                                    new_depth=self._depth, new_color=self._color)
            self._bottom_sprite = None
            self._left_sprite = None
            self._right_sprite = None

        else:
            if self._top_sprite is None:
                self._top_sprite = RectangleSprite(self.layer_id())
            if self._bottom_sprite is None:
                self._bottom_sprite = RectangleSprite(self.layer_id())
            if self._left_sprite is None:
                self._left_sprite = RectangleSprite(self.layer_id())
            if self._right_sprite is None:
                self._right_sprite = RectangleSprite(self.layer_id())
            """ 
            like this:
            *--------------------*
            |        TOP         |
            *---*------------*---*
            |   |            |   |
            | L |            | R |
            |   |            |   |
            *---*------------*---*
            |       BOTTOM       |
            *--------------------*
            """
            self._top_sprite.update(new_rect=[self._x, self._y, self._w, self._outline],
                                    new_depth=self._depth, new_color=self._color)
            self._bottom_sprite.update(new_rect=[self._x, self._y + self._h - self._outline, self._w, self._outline],
                                       new_depth=self._depth, new_color=self._color)
            self._left_sprite.update(new_x=self._x, new_y=self._y + self._outline,
                                     new_w=self._outline, new_h=self._h - 2 * self._outline,
                                     new_depth=self._depth, new_color=self._color)
            self._right_sprite.update(new_x=self._x + self._w - self._outline,
                                      new_y=self._y + self._outline,
                                      new_w=self._outline, new_h=self._h - 2 * self._outline,
                                      new_depth=self._depth, new_color=self._color)

    def all_sprites_nullable(self):
        yield self._top_sprite
        yield self._bottom_sprite
        yield self._left_sprite
        yield self._right_sprite

    def update(self, new_rect=None, new_x=None, new_y=None, new_w=None, new_h=None, new_outline=None, new_color=None, new_depth=None):
        did_change = False

        if new_rect is not None:
            new_x = new_rect[0]
            new_y = new_rect[1]
            new_w = new_rect[2]
            new_h = new_rect[3]

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
        if new_outline is not None and new_outline != self._outline:
            did_change = True
            self._outline = new_outline
        if new_color is not None and new_color != self._color:
            did_change = True
            self._color = new_color
        if new_depth is not None and new_depth != self._depth:
            did_change = True
            self._depth = new_depth

        if did_change:
            self._build_sprites()

        return self


class TriangleOutlineSprite(MultiSprite):

    def __init__(self, layer_id, p1=(0, 0), p2=(0, 0), p3=(0, 0), outline=1, color=(1, 1, 1), depth=1):
        MultiSprite.__init__(self, SpriteTypes.TRIANGLE, layer_id)
        self._p1 = p1
        self._p2 = p2
        self._p3 = p3
        self._outline = outline
        self._color = color
        self._depth = depth

        self._sub_triangles = []

    def all_sprites_nullable(self):
        for spr in self._sub_triangles:
            yield spr

    def update(self, new_points=None, new_p1=None, new_p2=None, new_p3=None, new_outline=None, new_color=None, new_depth=None):
        points = new_points if new_points is not None else (self._p1, self._p2, self._p3)
        new_p1 = new_p1 if new_p1 is not None else points[0]
        new_p2 = new_p2 if new_p2 is not None else points[1]
        new_p3 = new_p3 if new_p3 is not None else points[2]

        did_change = False

        if new_p1 != self._p1:
            did_change = True
            self._p1 = new_p1
        if new_p2 != self._p2:
            did_change = True
            self._p2 = new_p2
        if new_p3 != self._p3:
            did_change = True
            self._p3 = new_p3
        if new_outline is not None and new_outline != self._outline:
            did_change = True
            self._outline = new_outline
        if new_color is not None and new_color != self._color:
            did_change = True
            self._color = new_color
        if new_depth is not None and new_depth != self._depth:
            did_change = True
            self._depth = new_depth

        if did_change:
            self._build_sprites()

        return self

    def _build_sprites(self):
        if self._outline <= 0:
            self._sub_triangles = []
            return

        heights = [
            util.dist_from_point_to_line(self._p1, self._p2, self._p3),
            util.dist_from_point_to_line(self._p2, self._p1, self._p3),
            util.dist_from_point_to_line(self._p3, self._p1, self._p2)
        ]

        if min(heights) <= self._outline:
            # outline fills entire triangle
            util.extend_or_empty_list_to_length(self._sub_triangles, 1, creator=lambda: TriangleSprite(self.layer_id()))
            self._sub_triangles[0] = self._sub_triangles[0].update(new_p1=self._p1, new_p2=self._p2, new_p3=self._p3,
                                                                   new_color=self._color, new_depth=self._depth)
            return
        else:
            util.extend_or_empty_list_to_length(self._sub_triangles, 6, creator=lambda: TriangleSprite(self.layer_id()))
            pts = [self._p1, self._p2, self._p3]

            for i in range(0, 3):
                A = pts[i]
                B = pts[(i + 1) % 3]
                C = pts[(i + 2) % 3]

                """
                 A    l1
                 |    ab .
                 |t1/  |       .
                 |/ t2 |              . 
                 C----cb/l2----------------B
                """

                B_to_AC = util.vector_from_point_to_line(B, A, C)
                AC_to_B = util.sub((0, 0), B_to_AC)
                AC_to_B_with_outline_len = util.set_length(AC_to_B, self._outline)

                l1 = util.add(A, AC_to_B_with_outline_len)
                l2 = util.add(C, AC_to_B_with_outline_len)
                ab = util.line_line_intersection(l1, l2, A, B)
                cb = util.line_line_intersection(l1, l2, C, B)

                t1 = (A, ab, C)
                t2 = (C, ab, cb)

                old_t1_spr = self._sub_triangles[i * 2]
                old_t2_spr = self._sub_triangles[i * 2 + 1]

                self._sub_triangles[i * 2] = old_t1_spr.update(new_points=t1, new_color=self._color, new_depth=self._depth)
                self._sub_triangles[i * 2 + 1] = old_t2_spr.update(new_points=t2, new_color=self._color, new_depth=self._depth)


class TextSprite(MultiSprite):

    DEFAULT_X_KERNING = 0
    DEFAULT_Y_KERNING = 0

    # Alignments
    LEFT = 0
    CENTER = 1
    RIGHT = 2

    def __init__(self, layer_id, x, y, text, scale=1.0, depth=0, color=(1, 1, 1), color_lookup=None, font_lookup=None,
                 x_kerning=DEFAULT_X_KERNING, y_kerning=DEFAULT_Y_KERNING, alignment=LEFT,
                 outline_thickness=0, outline_color=(0, 0, 0)):

        MultiSprite.__init__(self, SpriteTypes.IMAGE, layer_id)
        self._x = x
        self._y = y
        self._text = text
        self._scale = scale
        self._depth = depth
        self._base_color = color
        self._color_lookup = color_lookup if color_lookup is not None else {}
        self._alignment = alignment
        self._outline_thickness = outline_thickness
        self._outline_color = outline_color
        self._x_kerning = x_kerning
        self._y_kerning = y_kerning

        if font_lookup is not None:
            self._font_lookup = font_lookup
        else:
            import src.engine.spritesheets as spritesheets  # (.-.)
            self._font_lookup = spritesheets.get_default_font()

        # this stuff is calculated by _build_character_sprites
        self._character_sprites = []
        self._bounding_rect = [0, 0, 0, 0]
        self._unused_sprites = []  # TODO delete

        self._build_character_sprites()

    def get_rect(self):
        return self._bounding_rect

    def size(self):
        return self._bounding_rect[2], self._bounding_rect[3]

    def _build_character_sprites(self):
        a_character = self._font_lookup.get_char("o")
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

        outline_offsets = [(0, 0)]
        if self._outline_thickness > 0:
            thick = self._outline_thickness
            outline_offsets.extend([(-thick, 0), (0, -thick), (thick, 0), (0, thick)])

        for idx in range(0, len(self._text)):
            character = self._text[idx]
            if character == "\n":
                cur_x = self._x
                cur_y += math.ceil(char_size[1] * self._scale) + self._y_kerning
            else:
                char_model = self._font_lookup.get_char(character)
                if char_model is not None:
                    for offs in outline_offsets:
                        is_outline = offs != (0, 0)
                        if len(old_sprites) > 0:
                            next_sprite = old_sprites.pop()
                        else:
                            next_sprite = ImageSprite.new_sprite(self.layer_id())

                        if not is_outline:
                            char_color = self._base_color if idx not in self._color_lookup else self._color_lookup[idx]
                        else:
                            char_color = self._outline_color

                        char_sprite = next_sprite.update(new_model=char_model,
                                                         new_x=cur_x + offs[0],
                                                         new_y=cur_y + offs[1],
                                                         new_scale=self._scale,
                                                         new_depth=self._depth + 0.1 * (1 if is_outline else 0),
                                                         new_color=char_color)

                        if not is_outline:
                            base_char_sprite = char_sprite

                        self._character_sprites.append(char_sprite)

                    self._bounding_rect[2] = max(self._bounding_rect[2], base_char_sprite.x() + base_char_sprite.width() - self._bounding_rect[0])
                    self._bounding_rect[3] = max(self._bounding_rect[3], base_char_sprite.y() + base_char_sprite.height() - self._bounding_rect[1])
                    cur_x += base_char_sprite.width() + self._x_kerning
                else:
                    self._bounding_rect[2] = max(self._bounding_rect[2], cur_x + math.ceil(char_size[0] * self._scale) - self._bounding_rect[0])
                    self._bounding_rect[3] = max(self._bounding_rect[3], cur_y + math.ceil(char_size[1] * self._scale) - self._bounding_rect[1])
                    cur_x += math.ceil(char_size[0] * self._scale) + self._x_kerning

        if self._alignment != TextSprite.LEFT:
            self._realign_characters()

        for spr in old_sprites:
            spr = spr.update(new_model=False, new_x=self._bounding_rect[0], new_y=self._bounding_rect[1] + 16)
            self._unused_sprites.append(spr)

    def _realign_characters(self):
        row_to_chars = {}
        for idx, c in enumerate(self._character_sprites):
            # Dividing up character sprites by row is a little complicated due to outline sprites
            # having an offset from their line's 'true y'. But we can just divide and round.
            row = round((c.y() - self.get_rect()[1]) / c.height())
            if row not in row_to_chars:
                row_to_chars[row] = []
            row_to_chars[row].append((c, idx))

        x_min = self._bounding_rect[0]
        x_max = x_min + self._bounding_rect[2]

        for row in row_to_chars:
            row_to_chars[row].sort(key=lambda c_idx: c_idx[0].x())
            line_length = row_to_chars[row][-1][0].x() + row_to_chars[row][-1][0].width() - row_to_chars[row][0][0].x()
            if self._alignment == TextSprite.RIGHT:
                dx = x_max - x_min - line_length
            elif self._alignment == TextSprite.CENTER:
                dx = (self._bounding_rect[2] - line_length) // 2
            else:
                dx = 0

            for c, idx in row_to_chars[row]:
                self._character_sprites[idx] = c.update(new_x=c.x() + dx)

    def update(self, new_x=None, new_y=None, new_text=None, new_scale=None, new_depth=None,
               new_color=None, new_color_lookup=None, new_font_lookup=None, new_alignment=None,
               new_outline_thickness=None, new_outline_color=None,
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
        if new_alignment is not None and new_alignment != self._alignment:
            did_change = True
            self._alignment = new_alignment
        if new_outline_thickness is not None and new_outline_thickness != self._outline_thickness:
            did_change = True
            self._outline_thickness = new_outline_thickness
        if new_outline_color is not None and new_outline_color != self._outline_color:
            did_change = True
            self._outline_color = new_outline_color
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
        for spr in self._unused_sprites:  # big yikes.. why?
            yield spr

    def __repr__(self):
        return type(self).__name__ + "({}, {}, {})".format(self._x, self._y, self._text.replace("\n", "\\n"))

    @staticmethod
    def _get_char_width(c, font_lookup, scale):
        char_sprite = font_lookup.get_char(c)
        if char_sprite is None:
            char_sprite = font_lookup.get_char("o")
            if char_sprite is None:
                return 0
        return char_sprite.width() * scale

    @staticmethod
    def _get_line_width(text, font_lookup, scale, x_kerning):
        res = 0
        for i in range(0, len(text)):
            res += TextSprite._get_char_width(text[i], font_lookup, scale)
            if i < len(text) - 1:
                res += x_kerning
        return res

    @staticmethod
    def wrap_text_to_fit(text, width, scale=1, font_lookup=None, x_kerning=DEFAULT_X_KERNING):
        """
        text: str or TextBuilder
        returns: list of strings or TextBuilders, one per line.
        """
        if font_lookup is None:
            import src.engine.spritesheets as spritesheets  # (.-.)
            font_lookup = spritesheets.get_instance().get_sheet(spritesheets.DefaultFont.SHEET_ID)

        using_tbs = isinstance(text, TextBuilder)

        if "\n" in text:
            lines = text.split("\n")
            res = []
            for line in lines:
                for subline in TextSprite.wrap_text_to_fit(line, width, scale=scale, font_lookup=font_lookup, x_kerning=x_kerning):
                    res.append(subline)
            return res
        else:
            # at this point, text contains no newlines
            words = text.split(" ")  # FYI if you have repeated spaces this will delete them
            cur_line = []
            cur_width = 0

            if len(words) == 1 and len(words[0]) == 0:
                # probably an intentional empty line, so preserve it.
                return [""] if not using_tbs else [TextBuilder()]

            res = []

            for w in words:
                if len(w) == 0:
                    continue
                else:
                    word_width = TextSprite._get_line_width(w, font_lookup, scale, x_kerning)
                    space_width = TextSprite._get_char_width(" ", font_lookup, scale) + x_kerning
                    if len(cur_line) == 0:
                        cur_line.append(w)
                        cur_width = word_width
                    elif cur_width + space_width + word_width > width / scale:
                        # gotta wrap
                        res.append(" ".join(cur_line) if not using_tbs else TextBuilder.join(cur_line, sep=" "))
                        cur_line.clear()
                        cur_line.append(w)
                        cur_width = word_width + x_kerning
                    else:
                        cur_line.append(w)
                        cur_width += space_width + word_width + x_kerning

            if len(cur_line) > 0:
                res.append(" ".join(cur_line) if not using_tbs else TextBuilder.join(cur_line, sep=" "))

            return res


class TextBuilder:

    def __init__(self, text="", colors=None):
        self.text = text
        self.colors = {} if colors is None else colors

    def add(self, new_text, color=None):
        if color is not None:
            for i in range(0, len(new_text)):
                self.colors[len(self.text) + i] = color
        self.text += new_text
        return self

    def get_color_at(self, idx):
        if idx in self.colors:
            return self.colors[idx]
        else:
            return None

    def addLine(self, new_text, color=None):
        return self.add(new_text + "\n", color=color)

    def recolor_chars(self, chars, new_color) -> 'TextBuilder':
        res = self.copy()
        for i, c in enumerate(res.text):
            if c in chars:
                res.colors[i] = new_color
        return res

    def recolor_chars_between(self, start_chars, end_chars, new_color, preserve_outer_chars=False) -> 'TextBuilder':
        res = TextBuilder()

        recoloring = False
        for i, c in enumerate(self.text):
            if c in start_chars:
                recoloring = True
                if preserve_outer_chars:
                    res.add(c, color=self.get_color_at(i))
            elif c in end_chars:
                recoloring = False
                if preserve_outer_chars:
                    res.add(c, color=self.get_color_at(i))
            else:
                res.add(c, color=new_color if recoloring else self.get_color_at(i))

        return res

    def copy(self) -> 'TextBuilder':
        return TextBuilder(self.text, dict(self.colors))

    def split(self, sep) -> typing.List['TextBuilder']:
        res = []
        orig_idx = 0
        for text in self.text.split(sep):
            split_colors = {}
            for c_idx in range(len(text)):
                if orig_idx in self.colors:
                    split_colors[c_idx] = self.colors[orig_idx]
                orig_idx += 1
            orig_idx += len(sep)
            res.append(TextBuilder(text, colors=split_colors))
        return res

    @staticmethod
    def join(sequence, sep="", sep_color=None) -> 'TextBuilder':
        """
        Joins a sequence of str or TextBuilders into a single TextBuilder.
        """
        res = TextBuilder()
        for s_idx_in_seq, s in enumerate(sequence):
            if s_idx_in_seq > 0:
                res.add(sep, color=sep_color)
            if isinstance(s, TextBuilder):
                start_idx = len(res)
                res.text += s.text
                for i in range(len(s)):
                    s_color = s.get_color_at(i)
                    if s_color is not None:
                        res.colors[start_idx + i] = s_color
            else:
                res.add(str(s))
        return res

    def __iter__(self):
        return self.text

    def __getitem__(self, key):
        return self.text[key]

    def __len__(self):
        return len(self.text)

    def __contains__(self, item):
        return item in self.text

    def __repr__(self):
        return "TextBuilder({}, {})".format(self.text, self.colors)


class BorderBoxSprite(MultiSprite):

    def __init__(self, layer_id, rect,
                 top_left=None, top=None, top_right=None,
                 left=None, center=None, right=None,
                 bottom_left=None, bottom=None, bottom_right=None,
                 all_borders=None, hollow_center=False,
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
        self._center_model = (all_borders[4] if all_borders is not None else center) if not hollow_center else None
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
                             new_ratio=(self._scale, y_ratio), new_color=self._color)

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
                             new_ratio=(x_ratio, self._scale), new_color=self._color)

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











