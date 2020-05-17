
import src.utils.util as util
import src.engine.sprites as sprites
import src.engine.inputs as inputs
import src.engine.keybinds as keybinds
import src.engine.globaltimer as globaltimer

import src.game.spriteref as spriteref
import src.game.colors as colors
import src.game.globalstate as gs
import src.game.const as const


_ENT_ID = 0


def next_entity_id():
    global _ENT_ID
    _ENT_ID += 1
    return _ENT_ID - 1


# physics groups
_UNKNOWN_GROUP = -1
_ENVIRONMENT_GROUP = 5
_ACTOR_GROUP = 10


class Entity:

    def __init__(self, x, y, w, h):
        self._ent_id = next_entity_id()

        self._x = x
        self._y = y

        w = util.Utils.assert_int(w, msg="width must be an integer: {}".format(w), error=True)
        h = util.Utils.assert_int(h, msg="height must be an integer: {}".format(h), error=True)
        self._size = w, h

        self._x_vel = 0  # pixels per tick
        self._y_vel = 0

        self.world = None  # world sets this when entity is added / removed

        self._debug_sprites = {}

        self._colliders = []

    def get_world(self):
        return self.world

    def get_rect(self, raw=False):
        xy = self.get_xy(raw=raw)
        size = self.get_size()
        return [xy[0], xy[1], size[0], size[1]]

    def get_xy(self, raw=False):
        if raw:
            return self._x, self._y
        else:
            return (int(self._x), int(self._y))

    def set_xy(self, xy, update_vel=False):
        if update_vel:
            self.set_vel((xy[0] - self._x, xy[1] - self._y))

        self._x = xy[0]
        self._y = xy[1]

    def set_x(self, x):
        self._x = x

    def set_y(self, y):
        self._y = y

    def shift(self, raw=True, dx=0, dy=0):
        if raw:
            self._x += dx
            self._y += dy
        else:
            if dx != 0:
                self._x = int(self._x) + dx
                self._y = int(self._y) + dy

    def is_dynamic(self):
        """whether this entity's movement is controlled by the physics system"""
        return False

    def get_physics_group(self):
        return _UNKNOWN_GROUP

    def get_x(self, raw=False):
        return self.get_xy(raw=raw)[0]

    def get_y(self, raw=False):
        return self.get_xy(raw=raw)[1]

    def get_w(self):
        return self.get_size()[0]

    def get_h(self):
        return self.get_size()[1]

    def get_size(self):
        return self._size

    def get_vel(self):
        return (self._x_vel, self._y_vel)

    def get_x_vel(self):
        return self.get_vel()[0]

    def get_y_vel(self):
        return self.get_vel()[1]

    def set_vel(self, v_xy):
        self.set_x_vel(v_xy[0])
        self.set_y_vel(v_xy[1])

    def set_x_vel(self, x_vel):
        self._x_vel = x_vel

    def set_y_vel(self, y_vel):
        self._y_vel = y_vel

    def calc_next_xy(self, raw=False):
        new_xy = self.get_x(raw=True) + self.get_x_vel(), self.get_y(raw=True) + self.get_y_vel()
        if raw:
            return new_xy
        else:
            return int(new_xy[0]), int(new_xy[1])

    def calc_next_rect(self, raw=False):
        next_xy = self.calc_next_xy(raw=raw)
        size = self.get_size()
        return [next_xy[0], next_xy[1], size[0], size[1]]

    def update(self):
        pass

    def all_colliders(self, solid=None, sensor=None):
        for c in self._colliders:
            if solid is not None and solid != c.is_solid():
                continue
            if sensor is not None and sensor != c.is_sensor():
                continue
            yield c

    def set_colliders(self, colliders):
        self._colliders = [c for c in colliders]

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

            if collider.is_sensor() and len(self.get_world().get_sensor_state(collider.get_id())) <= 0:
                color = colors.PINK

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
        Entity.__init__(self, x, y, w, h)

        self.set_colliders([RectangleCollider([0, 0, w, h], CollisionMasks.BLOCK)])

    def update(self):
        pass

    def is_dynamic(self):
        return False

    def get_debug_color(self):
        return colors.DARK_GRAY

    def all_sprites(self):
        return []

    def get_physics_group(self):
        return _ENVIRONMENT_GROUP


class MovingBlockEntity(BlockEntity):

    def __init__(self, w, h, pts, period=90, loop=True):
        BlockEntity.__init__(self, pts[0][0], pts[0][1], w, h)
        self._pts = pts
        self._period = period
        self._loop = loop

    def is_dynamic(self):
        return False

    def update(self):
        tick_count = globaltimer.tick_count()  # TODO - hook up a real timer

        step = tick_count // self._period
        cycle = step // len(self._pts)

        if self._loop or cycle % 2 == 0:
            # we're going forward
            p1 = self._pts[step % len(self._pts)]
            p2 = self._pts[(step + 1) % len(self._pts)]
        else:
            # backwards
            p1 = self._pts[(-step) % len(self._pts)]
            p2 = self._pts[(-step - 1) % len(self._pts)]

        prog = (tick_count % self._period) / self._period
        pos = util.Utils.smooth_interp(p1, p2, prog)

        self.set_xy(pos, update_vel=True)


class PlayerEntity(Entity):

    def __init__(self, x, y):
        w = int(gs.get_instance().cell_size * 1)
        h = int(gs.get_instance().cell_size * 2)

        Entity.__init__(self, x, y, w, h)

        self._y_vel_max = 5 * gs.get_instance().cell_size
        self._x_vel_max_grounded = 0.1 * gs.get_instance().cell_size

        self._x_accel_grounded = 0.25

        self._gravity = 0.10  # TODO figure out the units on this

        w_inset = int(self.get_w() * 0.15)
        h_inset = int(self.get_h() * 0.10)

        vert_env_collider = RectangleCollider([w_inset, 0, self.get_w() - (w_inset * 2), self.get_h()],
                                              CollisionMasks.ACTOR, resolution_hint=CollisionResolutionHints.VERT_ONLY,
                                              color=colors.WHITE)
        horz_env_collider = RectangleCollider([0, 0, self.get_w(), self.get_h() - h_inset],
                                              CollisionMasks.ACTOR, resolution_hint=CollisionResolutionHints.HORZ_ONLY,
                                              color=colors.WHITE)

        foot_sensor = RectangleCollider([0, self.get_h(), self.get_w(), 1],
                                        CollisionMasks.BLOCK_SENSOR, color=colors.GREEN)

        left_sensor = RectangleCollider([-1, h_inset, 1, self.get_h() - (h_inset * 2)],
                                        CollisionMasks.BLOCK_SENSOR, color=colors.GREEN)

        right_sensor = RectangleCollider([self.get_w(), h_inset, 1, self.get_h() - (h_inset * 2)],
                                         CollisionMasks.BLOCK_SENSOR, color=colors.GREEN)

        self.foot_sensor_id = foot_sensor.get_id()
        self.left_sensor_id = left_sensor.get_id()
        self.right_sensor_id = right_sensor.get_id()

        self.set_colliders([vert_env_collider, horz_env_collider, foot_sensor, left_sensor, right_sensor])

    def is_dynamic(self):
        return True

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

        self.set_x_vel(dx * self._x_vel_max_grounded)

        if request_jump and len(self.get_world().get_sensor_state(self.foot_sensor_id)) > 0:
            self.set_y_vel(self._y_vel - 3)

    def get_debug_color(self):
        return colors.BLUE


class CollisionMask:

    def __init__(self, name, is_solid=True, is_sensor=False, collides_with=()):
        self._name = name
        self._is_solid = is_solid
        self._is_sensor = is_sensor
        self._collides_with = collides_with

    def get_name(self) -> str:
        return self._name

    def is_solid(self) -> bool:
        return self._is_solid

    def is_sensor(self) -> bool:
        return self._is_sensor

    def collides_with(self, mask) -> bool:
        if mask is None:
            return False
        else:
            return mask.get_name() in self._collides_with


class CollisionMasks:

    BLOCK = CollisionMask("block")
    ACTOR = CollisionMask("actor", collides_with=("block"))

    BLOCK_SENSOR = CollisionMask("block_sensor", is_solid=False, is_sensor=True, collides_with=("block"))


class CollisionResolutionHint:

    def __init__(self, ident, allow_horz, allow_vert):
        self._ident = ident
        self._allow_horz = allow_horz
        self._allow_vert = allow_vert

    def allows_horz(self):
        return self._allow_horz

    def allows_vert(self):
        return self._allow_vert

    def __eq__(self, other):
        if isinstance(other, CollisionResolutionHint):
            return self._ident == other._ident
        else:
            return False

    def __hash__(self):
        return hash(self._ident)


class CollisionResolutionHints:
    HORZ_ONLY = CollisionResolutionHint("horz_only", True, False)
    VERT_ONLY = CollisionResolutionHint("vert_only", False, True)
    BOTH = CollisionResolutionHint("both", True, True)


_COLLIDER_ID = 0


def _next_collider_id():
    global _COLLIDER_ID
    _COLLIDER_ID += 1
    return _COLLIDER_ID - 1


class PolygonCollider:

    def __init__(self, points, mask, resolution_hint=None, color=colors.RED):
        self._mask = mask
        self._points = points
        self._resolution_hint = resolution_hint if resolution_hint is not None else CollisionResolutionHints.BOTH

        self._debug_color = color
        self._id = _next_collider_id()

    def get_id(self):
        return self._id

    def get_mask(self):
        return self._mask

    def get_resolution_hint(self):
        return self._resolution_hint

    def collides_with(self, other):
        return self.get_mask().collides_with(other.get_mask())

    def is_overlapping(self, offs, other, other_offs):
        raise NotImplementedError()  # TODO general polygon collisions

    def is_colliding_with(self, offs, other, other_offs):
        return self.collides_with(other) and self.is_overlapping(offs, other, other_offs)

    def is_solid(self):
        return self._mask.is_solid()

    def is_sensor(self):
        return self._mask.is_sensor()

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

    def __init__(self, rect, mask=None, resolution_hint=None, color=colors.RED):
        points = [p for p in util.Utils.all_rect_corners(rect, inclusive=False)]
        PolygonCollider.__init__(self, points, mask=mask, resolution_hint=resolution_hint, color=color)

    def is_overlapping(self, offs, other, other_offs):
        if not isinstance(other, RectangleCollider):
            return super().is_overlapping(offs, other, other_offs)
        else:
            return util.Utils.get_rect_intersect(self.get_rect(offs=offs), other.get_rect(offs=other_offs)) is not None


