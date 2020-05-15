
import src.utils.util as util
import src.engine.sprites as sprites
import src.engine.inputs as inputs
import src.engine.keybinds as keybinds

import src.game.spriteref as spriteref
import src.game.colors as colors
import src.game.globalstate as gs
import src.game.const as const


_ENT_ID = 0


def next_entity_id():
    global _ENT_ID
    _ENT_ID += 1
    return _ENT_ID - 1


class Entity:

    def __init__(self):
        self._ent_id = next_entity_id()

        self.world = None  # world sets this when entity is added / removed

        self._debug_sprites = {}

    def get_world(self):
        return self.world

    def get_rect(self):
        raise NotImplementedError()

    def is_dynamic(self):
        return False

    def get_x(self):
        return self.get_rect()[0]

    def get_y(self):
        return self.get_rect()[1]

    def get_w(self):
        return self.get_rect()[2]

    def get_h(self):
        return self.get_rect()[3]

    def get_xy(self):
        return (self.get_x(), self.get_y())

    def get_size(self):
        return (self.get_w(), self.get_h())

    def update(self):
        pass

    def all_colliders(self):
        return []

    def all_sprites(self):
        return []

    def all_debug_sprites(self):
        main_rect_key = "main_rect"
        if main_rect_key not in self._debug_sprites:
            self._debug_sprites[main_rect_key] = sprites.RectangleSprite(spriteref.POLYGON_LAYER)
        self._debug_sprites[main_rect_key].update(new_rect=self.get_rect(), new_color=self.get_debug_color(),
                                                  new_depth=20)
        yield self._debug_sprites[main_rect_key]

        colliders_key = "colliders"
        if colliders_key not in self._debug_sprites:
            self._debug_sprites[colliders_key] = []

        all_colliders = [c for c in self.all_colliders()]

        util.Utils.extend_or_empty_list_to_length(self._debug_sprites[colliders_key], len(all_colliders),
                                                  creator=lambda: sprites.RectangleOutlineSprite(spriteref.POLYGON_LAYER))
        for collider, rect_sprite in zip(all_colliders, self._debug_sprites[colliders_key]):
            color = collider.get_debug_color()
            rect = collider.get_rect(offs=self.get_xy())
            rect_sprite.update(new_rect=rect, new_color=color, new_outline=1, new_depth=5)
            yield rect_sprite

    def get_debug_color(self):
        return colors.WHITE

    def __eq__(self, other):
        if isinstance(other, Entity):
            return self._ent_id == other._ent_id
        else:
            return False

    def __hash__(self):
        return self._ent_id

    def __repr__(self):
        return "{}({}, {})".format(type(self).__name__, self._ent_id, self.get_rect())


class BlockEntity(Entity):

    def __init__(self, x, y, w, h):
        Entity.__init__(self)

        self._rect = [x, y, w, h]

        self._rect_collider = RectangleCollider([0, 0, w, h], mask=CollisionMasks.BLOCK)

    def get_rect(self):
        return self._rect

    def update(self):
        pass

    def get_debug_color(self):
        return colors.DARK_GRAY

    def all_sprites(self):
        return []

    def all_colliders(self):
        yield self._rect_collider


class DynamicEntity(Entity):

    def __init__(self, x, y, priority=0):
        Entity.__init__(self)
        self._priority = priority

        self._x = x
        self._y = y

        self._x_vel = 0  # pixels per tick
        self._y_vel = 0

    def is_dynamic(self):
        return True

    def get_collision_priority(self):
        return self._priority

    def get_vel(self):
        return (self._x_vel, self._y_vel)

    def set_vel(self, v_xy):
        self.set_x_vel(v_xy[0])
        self.set_y_vel(v_xy[1])

    def set_x_vel(self, x_vel):
        self._x_vel = x_vel

    def set_y_vel(self, y_vel):
        self._y_vel = y_vel

    def set_xy(self, xy):
        self._x = xy[0]
        self._y = xy[1]

    def calc_next_xy(self):
        return (self._x + self._x_vel, self._y + self._y_vel)


class PlayerEntity(DynamicEntity):

    def __init__(self, x, y):
        DynamicEntity.__init__(self, x, y)

        self._w = gs.get_instance().cell_size * 1
        self._h = gs.get_instance().cell_size * 2

        self._y_vel_max = 5 * gs.get_instance().cell_size
        self._x_vel_max_grounded = 0.1 * gs.get_instance().cell_size

        self._x_accel_grounded = 0.25

        self._gravity = 0.10  # TODO figure out the units on this

        self._vert_collider = RectangleCollider([self._w * 0.1, 0, self._w * 0.8, self._h],
                                                mask=CollisionMasks.ACTOR, ignore_horz=True, color=colors.WHITE)
        self._horz_collider = RectangleCollider([0, self._h * 0.1, self._w, self._h * 0.8],
                                                mask=CollisionMasks.ACTOR, ignore_vert=True, color=colors.WHITE)

    def get_rect(self):
        return [int(self._x), int(self._y), self._w, self._h]

    def all_colliders(self):
        return [
            self._vert_collider,
            self._horz_collider
        ]

    def update(self):
        self._handle_inputs()

        self._y_vel += self._gravity

        if self._y_vel > self._y_vel_max:
            self._y_vel = self._y_vel_max

    def _handle_inputs(self):
        keys = keybinds.get_instance()
        request_left = inputs.get_instance().is_held(keys.get_keys(const.MOVE_LEFT))
        request_right = inputs.get_instance().is_held(keys.get_keys(const.MOVE_RIGHT))
        request_jump = inputs.get_instance().was_pressed(keys.get_keys(const.JUMP))

        dx = 0
        if request_left:
            dx -= 1
        if request_right:
            dx += 1

        self._x_vel = dx * self._x_vel_max_grounded

        if request_jump:
            self._y_vel -= 4

    def get_debug_color(self):
        return colors.BLUE


class CollisionMask:

    def __init__(self, name, collides_with=()):
        self._name = name
        self._collides_with = collides_with

    def get_name(self) -> str:
        return self._name

    def collides_with(self, mask) -> bool:
        if mask is None:
            return False
        else:
            return mask.get_name() in self._collides_with


class CollisionMasks:

    BLOCK = CollisionMask("block")
    ACTOR = CollisionMask("actor", collides_with=("block"))


_COLLIDER_ID = 0


def _next_collider_id():
    global _COLLIDER_ID
    _COLLIDER_ID += 1
    return _COLLIDER_ID - 1


class PolygonCollider:

    def __init__(self, points, mask=None, dynamic=True, ignore_horz=False, ignore_vert=False, color=colors.RED):
        self._mask = mask
        self._dynamic = dynamic
        self._points = points

        self._is_horz = not ignore_horz
        self._is_vert = not ignore_vert

        self._debug_color = color
        self._id = _next_collider_id()

    def get_mask(self):
        return self._mask

    def collides_with(self, other):
        if not self.get_mask().collides_with(other.get_mask()):
            return False
        else:
            if self.is_horz() and other.is_horz():
                return True
            elif self.is_vert() and other.is_vert():
                return True
            else:
                return False

    def is_colliding_with(self, offs, other, other_offs):
        raise NotImplementedError()  # TODO general polygon collisions

    def is_dynamic(self):
        return self._dynamic

    def is_horz(self):
        return self._is_horz

    def is_vert(self):
        return self._is_vert

    def get_points(self, offs=(0, 0)):
        return [(p[0] + offs[0], p[1] + offs[1]) for p in self._points]

    def get_rect(self, offs=(0, 0)):
        pts = self.get_points(offs=offs)
        if len(pts) == 0:
            return [0, 0, 0, 0]
        else:
            return util.Utils.get_rect_containing_points(pts)

    def get_debug_color(self):
        return self._debug_color

    def __eq__(self, other):
        if isinstance(other, PolygonCollider):
            return self._id == other._id
        else:
            return False

    def __hash__(self):
        return self._id


class RectangleCollider(PolygonCollider):

    def __init__(self, rect, mask=None, ignore_horz=False, ignore_vert=False, color=colors.RED):
        points = [p for p in util.Utils.all_rect_corners(rect, inclusive=False)]
        PolygonCollider.__init__(self, points, mask=mask,
                                 ignore_horz=ignore_horz, ignore_vert=ignore_vert, color=color)

    def is_colliding_with(self, offs, other, other_offs):
        if not self.collides_with(other):
            return False
        elif not isinstance(other, RectangleCollider):
            return super().is_colliding_with(offs, other, other_offs)
        else:
            return util.Utils.get_rect_intersect(self.get_rect(offs=offs), other.get_rect(offs=other_offs)) is not None


