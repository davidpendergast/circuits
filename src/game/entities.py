
import src.utils.util as util
import src.engine.sprites as sprites
import src.engine.inputs as inputs
import src.engine.keybinds as keybinds
import src.engine.globaltimer as globaltimer
import configs as configs

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
UNKNOWN_GROUP = -1
ENVIRONMENT_GROUP = 5
ACTOR_GROUP = 10


class Entity:

    def __init__(self, x, y, w=None, h=None):
        self._ent_id = next_entity_id()

        self._x = x
        self._y = y

        if w is not None and h is not None:
            w = util.assert_int(w, msg="width must be an integer: {}".format(w), error=True)
            h = util.assert_int(h, msg="height must be an integer: {}".format(h), error=True)
            self._size = w, h
        else:
            self._size = None

        self._x_vel = 0  # pixels per tick
        self._y_vel = 0

        self.world = None  # world sets this when entity is added / removed

        self._debug_sprites = {}

        self._colliders = []

        self._frame_of_reference_parent = None
        self._frame_of_reference_children = []

    def get_world(self):
        return self.world

    def get_rect(self, raw=False):
        xy = self.get_xy(raw=raw)
        size = self.get_size()
        return [xy[0], xy[1], size[0], size[1]]

    def get_center(self, raw=False):
        r = self.get_rect(raw=raw)
        pt = (r[0] + r[2] / 2, r[1] + r[3] / 2)
        if raw:
            return pt
        else:
            return (int(pt[0]), int(pt[1]))

    def get_xy(self, raw=False):
        if raw:
            return self._x, self._y
        else:
            return (int(self._x), int(self._y))

    def set_xy(self, xy, update_frame_of_reference=True):
        if xy[0] is not None:
            dx = xy[0] - self._x
            self._x = xy[0]

            if update_frame_of_reference:
                for child in self._frame_of_reference_children:
                    child.set_x(child.get_x(raw=True) + dx, update_frame_of_reference=True)

        if xy[1] is not None:
            dy = xy[1] - self._y
            self._y = xy[1]

            if update_frame_of_reference:
                for child in self._frame_of_reference_children:
                    child.set_y(child.get_y(raw=True) + dy, update_frame_of_reference=True)

    def set_x(self, x, update_frame_of_reference=True):
        self.set_xy((x, None), update_frame_of_reference=update_frame_of_reference)

    def set_y(self, y, update_frame_of_reference=True):
        self.set_xy((None, y), update_frame_of_reference=update_frame_of_reference)

    def is_dynamic(self):
        """whether this entity's movement is controlled by the physics system"""
        return False

    def get_physics_group(self):
        return UNKNOWN_GROUP

    def set_frame_of_reference_parent(self, parent):
        if parent == self._frame_of_reference_parent:
            return
        if self._frame_of_reference_parent is not None:
            if self in self._frame_of_reference_parent._frame_of_reference_children:  # family germs
                self._frame_of_reference_parent._frame_of_reference_children.remove(self)
        self._frame_of_reference_parent = parent
        if parent is not None:
            self._frame_of_reference_parent._frame_of_reference_children.append(self)

    def get_x(self, raw=False):
        return self.get_xy(raw=raw)[0]

    def get_y(self, raw=False):
        return self.get_xy(raw=raw)[1]

    def get_w(self):
        return self.get_size()[0]

    def get_h(self):
        return self.get_size()[1]

    def get_size(self):
        if self._size is None:
            raise NotImplementedError()
        else:
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

    def update_frame_of_reference_parent(self):
        pass

    def all_colliders(self, solid=None, sensor=None, enabled=True):
        for c in self._colliders:
            if enabled is not None and enabled != c.is_enabled():
                continue
            if solid is not None and solid != c.is_solid():
                continue
            if sensor is not None and sensor != c.is_sensor():
                continue
            yield c

    def set_colliders(self, colliders):
        self._colliders = [c for c in colliders]

    def all_sprites(self):
        return []

    def _update_main_body_debug_sprite(self, main_body_key):
        if main_body_key not in self._debug_sprites:
            self._debug_sprites[main_body_key] = sprites.RectangleSprite(spriteref.POLYGON_LAYER)
        self._debug_sprites[main_body_key].update(new_rect=self.get_rect(), new_color=self.get_debug_color(),
                                                  new_depth=20)

    def all_debug_sprites(self):
        main_body_key = "main_body"
        self._update_main_body_debug_sprite(main_body_key)
        if main_body_key in self._debug_sprites and self._debug_sprites[main_body_key] is not None:
            yield self._debug_sprites[main_body_key]

        rect_colliders_key = "rect_colliders"
        if rect_colliders_key not in self._debug_sprites:
            self._debug_sprites[rect_colliders_key] = []

        all_rect_colliders = [c for c in self.all_colliders() if isinstance(c, RectangleCollider) if c.is_enabled()]

        util.extend_or_empty_list_to_length(self._debug_sprites[rect_colliders_key], len(all_rect_colliders),
                                            creator=lambda: sprites.RectangleOutlineSprite(spriteref.POLYGON_LAYER))
        for collider, rect_sprite in zip(all_rect_colliders, self._debug_sprites[rect_colliders_key]):
            color = collider.get_debug_color()

            if collider.is_sensor() and len(self.get_world().get_sensor_state(collider.get_id())) <= 0:
                color = colors.PINK

            rect = collider.get_rect(offs=self.get_xy())
            rect_sprite.update(new_rect=rect, new_color=color, new_outline=1, new_depth=5)
            yield rect_sprite

        triangle_colliders_key = "triangle_colliders"
        if triangle_colliders_key not in self._debug_sprites:
            self._debug_sprites[triangle_colliders_key] = []

        all_triangle_colliders = [c for c in self.all_colliders() if isinstance(c, TriangleCollider) if c.is_enabled()]

        util.extend_or_empty_list_to_length(self._debug_sprites[triangle_colliders_key], len(all_triangle_colliders),
                                            creator=lambda: sprites.TriangleOutlineSprite(spriteref.POLYGON_LAYER))

        new_triangle_sprites = []
        for collider, triangle_sprite in zip(all_triangle_colliders, self._debug_sprites[triangle_colliders_key]):
            color = collider.get_debug_color()

            if collider.is_sensor() and len(self.get_world().get_sensor_state(collider.get_id())) <= 0:
                color = colors.PINK

            points = collider.get_points(offs=self.get_xy())
            new_triangle_sprites.append(triangle_sprite.update(new_points=points, new_outline=1,
                                                               new_color=color, new_depth=5))
            yield triangle_sprite

        self._debug_sprites[triangle_colliders_key] = new_triangle_sprites

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


class AbstractBlockEntity(Entity):

    def __init__(self, x, y, w=None, h=None):
        Entity.__init__(self, x, y, w=w, h=h)

    def update(self):
        pass

    def is_dynamic(self):
        return False

    def get_debug_color(self):
        return colors.DARK_GRAY

    def all_sprites(self):
        return []

    def all_blocks(self, recurse=False):
        yield self

    def get_physics_group(self):
        return ENVIRONMENT_GROUP


class BlockEntity(AbstractBlockEntity):
    """basic rectangular block."""

    def __init__(self, x, y, w, h):
        AbstractBlockEntity.__init__(self, x, y, w=w, h=h)

        self.set_colliders([RectangleCollider([0, 0, w, h], CollisionMasks.BLOCK)])


class CompositeBlockEntity(AbstractBlockEntity):

    def __init__(self, blocks):
        if len(blocks) == 0:
            raise ValueError("blocks is empty")

        self._blocks = blocks
        xy = self.get_xy(raw=False)
        AbstractBlockEntity.__init__(self, xy[0], xy[1])

    def all_blocks(self, recurse=False):
        for b in self._blocks:
            if recurse:
                for sub_block in b.all_blocks(recurse=True):
                    yield sub_block
            else:
                yield b

    def get_xy(self, raw=False):
        min_x = float('inf')
        min_y = float('inf')
        for b in self.all_blocks():
            b_xy = b.get_xy(raw=raw)
            min_x = min(min_x, b_xy[0])
            min_y = min(min_y, b_xy[1])
        return (min_x, min_y)

    def get_size(self, raw=True):
        min_x = float('inf')
        max_x = -float('inf')
        min_y = float('inf')
        max_y = -float('inf')
        for b in self.all_blocks():
            b_xy = b.get_xy()
            b_size = b.get_size()
            min_x = min(min_x, b_xy[0])
            max_x = max(max_x, b_xy[0] + b_size[0])  # XXX could have some raw / not raw issues here
            min_y = min(min_y, b_xy[1])
            max_y = max(max_y, b_xy[1] + b_size[1])  # XXX could have some raw / not raw issues here
        return (max_x - min_x, max_y - min_y)

    def update(self):
        for b in self.all_blocks():
            b.update()

    def all_sprites(self):
        for b in self.all_blocks():
            for spr in b.all_sprites():
                yield spr

    def all_colliders(self, solid=None, sensor=None, enabled=True):
        for b in self.all_blocks():
            for c in b.all_colliders():
                yield c

    def all_debug_sprites(self):
        for b in self.all_blocks():
            for spr in b.all_debug_sprites():
                yield spr


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
        pos = util.smooth_interp(p1, p2, prog)

        pos = int(pos[0]), int(pos[1])  # otherwise it's super jerky when the player rides it

        old_xy = self.get_xy(raw=True)

        self.set_xy(pos)
        self.set_vel(util.sub(old_xy, pos))


class SlopeOrientation:
    def __init__(self, pts):
        self.pts = pts

    def is_horz(self):
        # making the assumption here that all slopes are 1x2 or 2x1
        return any(p[0] == 2 for p in self.pts)

    def is_vert(self):
        return not self.is_horz()


class SlopeBlockEntity(AbstractBlockEntity):

    """
        up/down = side the angled part is on
        left/right = side of the thicker part of the slope
        w x h = total dims of the block
    """
    UPWARD_LEFT_2x1 = [(0, 0), (0, 1), (2, 1)]
    UPWARD_RIGHT_2x1 = [(0, 1), (2, 0), (2, 1)]

    UPWARD_LEFT_1x2 = [(0, 0), (0, 2), (1, 2)]
    UPWARD_RIGHT_1x2 = [(1, 0), (1, 2), (0, 2)]

    DOWNWARD_LEFT_2x1 = [(0, 0), (2, 0), (0, 1)]
    DOWNWARD_RIGHT_2x1 = [(0, 0), (2, 0), (2, 1)]

    DOWNWARD_LEFT_1x2 = [(0, 0), (0, 2), (1, 0)]
    DOWNWARD_RIGHT_1x2 = [(0, 0), (1, 2), (1, 0)]

    @staticmethod
    def make_slope(x, y, triangle, triangle_scale=1):
        scaled_triangle = [util.add((x, y), util.mult(pt, triangle_scale)) for pt in triangle]
        return SlopeBlockEntity(scaled_triangle)

    def __init__(self, triangle):
        rect = util.get_rect_containing_points(triangle)
        super().__init__(rect[0], rect[1], w=rect[2], h=rect[3])

        self._points = util.shift_bounding_rect_to(triangle, pos=(0, 0))

        if rect[2] <= rect[3]:
            self.set_colliders([TriangleCollider(self.get_points(origin=(0, 0)), CollisionMasks.SLOPE_BLOCK_VERT)])
        else:
            self.set_colliders([TriangleCollider(self.get_points(origin=(0, 0)), CollisionMasks.SLOPE_BLOCK_HORZ)])

    def get_points(self, origin=None):
        if origin is None:
            origin = self.get_xy(raw=False)
        res = []
        for pt in self._points:
            pt_x = origin[0] + pt[0]
            pt_y = origin[1] + pt[1]
            res.append((pt_x, pt_y))
        return res

    def _update_main_body_debug_sprite(self, main_body_key):
        if main_body_key not in self._debug_sprites:
            self._debug_sprites[main_body_key] = sprites.TriangleSprite(spriteref.POLYGON_LAYER)
        pts = self.get_points()
        spr = self._debug_sprites[main_body_key]
        self._debug_sprites[main_body_key] = spr.update(new_points=pts, new_color=self.get_debug_color(), new_depth=20)


class PlayerEntity(Entity):

    def __init__(self, x, y):
        w = int(gs.get_instance().cell_size * 1)
        h = int(gs.get_instance().cell_size * 1.75)

        Entity.__init__(self, x, y, w=w, h=h)

        self._y_vel_max = 20 * gs.get_instance().cell_size / configs.target_fps
        self._x_vel_max = 7.2 * gs.get_instance().cell_size / configs.target_fps

        self._wall_cling_y_vel_max = 4 * gs.get_instance().cell_size / configs.target_fps

        self._gravity = 0.15  # TODO split this into max_jump_height and jump_duration
        self._jump_y_vel = 4  # TODO units
        self._snap_down_dist = 4

        self._bonus_y_fric_on_let_go = 0.85

        self._wall_jump_x_vel = 1.5
        self._wall_jump_y_vel = self._jump_y_vel

        self._ground_accel = 0.65
        self._ground_reverse_dir_bonus_accel = 0.3

        self._air_accel = 0.15

        self._air_x_friction = 0.85
        self._ground_x_friction = 0.60

        self._wall_cling_time = 14   # how long you have to hold the direction to break the wall cling
        self._wall_cling_count = 0

        self._air_time = 0
        self._last_jump_time = 1000

        self._jump_cooldown = 10

        w_inset = int(self.get_w() * 0.15)  # 0.15
        h_inset = int(self.get_h() * 0.10)

        vert_env_collider = RectangleCollider([w_inset, 0, self.get_w() - (w_inset * 2), self.get_h()],
                                              CollisionMasks.ACTOR,
                                              collides_with=CollisionMasks.BLOCK,
                                              resolution_hint=CollisionResolutionHints.VERT_ONLY,
                                              color=colors.WHITE)

        horz_env_collider = RectangleCollider([0, 0, self.get_w(), self.get_h() - h_inset],
                                              CollisionMasks.ACTOR,
                                              collides_with=CollisionMasks.BLOCK,
                                              resolution_hint=CollisionResolutionHints.HORZ_ONLY,
                                              color=colors.WHITE)

        foot_sensor_rect = [0, self.get_h(), self.get_w(), 1]
        self.foot_sensor = RectangleCollider(foot_sensor_rect,
                                             CollisionMasks.SENSOR,
                                             collides_with=CollisionMasks.BLOCK,
                                             color=colors.GREEN)

        left_sensor = RectangleCollider([-1, h_inset, 1, self.get_h() - (h_inset * 2)],
                                        CollisionMasks.SENSOR,
                                        collides_with=CollisionMasks.BLOCK,
                                        color=colors.GREEN)

        right_sensor = RectangleCollider([self.get_w(), h_inset, 1, self.get_h() - (h_inset * 2)],
                                         CollisionMasks.SENSOR,
                                         collides_with=CollisionMasks.BLOCK,
                                         color=colors.GREEN)

        self.foot_sensor_id = self.foot_sensor.get_id()
        self.left_sensor_id = left_sensor.get_id()
        self.right_sensor_id = right_sensor.get_id()

        # pulls you to the ground when you're grounded
        snap_down_rect = [w_inset, self.get_h(), self.get_w() - w_inset * 2, self._snap_down_dist]
        self.snap_down_sensor = RectangleCollider(snap_down_rect,
                                                  CollisionMasks.SNAP_DOWN_SENSOR,
                                                  collides_with=(CollisionMasks.SLOPE_BLOCK_HORZ, CollisionMasks.BLOCK),
                                                  color=colors.YELLOW)

        # slope sensors
        slope_collider_main_horz = RectangleCollider([w_inset // 2, 1, self.get_w() - (w_inset), self.get_h() - h_inset],
                                                     CollisionMasks.ACTOR,
                                                     collides_with=(CollisionMasks.SLOPE_BLOCK_VERT),
                                                     resolution_hint=CollisionResolutionHints.HORZ_ONLY,
                                                     color=colors.OFF_WHITE)

        slope_collider_main_top = RectangleCollider([w_inset // 2, 1, self.get_w() - (w_inset), self.get_h() // 2],
                                                    CollisionMasks.ACTOR,
                                                    collides_with=(CollisionMasks.SLOPE_BLOCK_HORZ),
                                                    resolution_hint=CollisionResolutionHints.VERT_ONLY,
                                                    color=colors.OFF_WHITE)

        slope_collider_top = self.get_h() - h_inset
        slope_collider_bot = self.get_h() - 1
        slope_collider_left = w_inset
        slope_collider_right = self.get_w() - w_inset

        foot_slope_triangle_left = [(slope_collider_left, slope_collider_top),
                                   (self.get_w() // 2, slope_collider_top),
                                   (self.get_w() // 2, slope_collider_bot)]

        foot_slope_triangle_right = [(slope_collider_right, slope_collider_top),
                                    (self.get_w() // 2 + 1, slope_collider_top),
                                    (self.get_w() // 2 + 1, slope_collider_bot)]

        slope_env_collider_left = TriangleCollider(foot_slope_triangle_left,
                                                   CollisionMasks.ACTOR,
                                                   collides_with=CollisionMasks.SLOPE_BLOCK_HORZ,
                                                   resolution_hint=CollisionResolutionHints.VERT_ONLY,
                                                   color=colors.OFF_WHITE)

        slope_env_collider_right = TriangleCollider(foot_slope_triangle_right,
                                                    CollisionMasks.ACTOR,
                                                    collides_with=CollisionMasks.SLOPE_BLOCK_HORZ,
                                                    resolution_hint=CollisionResolutionHints.VERT_ONLY,
                                                    color=colors.OFF_WHITE)

        foot_slope_sensor_left = TriangleCollider([(p[0], p[1] + 1) for p in foot_slope_triangle_left],
                                                  CollisionMasks.SENSOR,
                                                  collides_with=CollisionMasks.SLOPE_BLOCK_HORZ,
                                                  color=colors.GREEN)

        foot_slope_sensor_right = TriangleCollider([(p[0], p[1] + 1) for p in foot_slope_triangle_right],
                                                   CollisionMasks.SENSOR,
                                                   collides_with=CollisionMasks.SLOPE_BLOCK_HORZ,
                                                   color=colors.GREEN)

        self.foot_slope_sensor_left_id = foot_slope_sensor_left.get_id()
        self.foot_slope_sensor_right_id = foot_slope_sensor_right.get_id()

        self.set_colliders([vert_env_collider, horz_env_collider,
                            self.foot_sensor, left_sensor, right_sensor,  self.snap_down_sensor,
                            slope_collider_main_horz, slope_collider_main_top,
                            slope_env_collider_left, slope_env_collider_right,
                            foot_slope_sensor_left, foot_slope_sensor_right])

    def is_dynamic(self):
        return True

    def get_physics_group(self):
        return ACTOR_GROUP

    def update(self):
        self._handle_inputs()

        if self.is_grounded():
            if self._y_vel > 0:
                self._y_vel = 0
        else:
            self._y_vel += self._gravity

        max_y_vel = self._y_vel_max if not self.is_clinging_to_wall() else self._wall_cling_y_vel_max
        if self._y_vel > max_y_vel:
            self._y_vel = max_y_vel

        if self.is_grounded():
            self._air_time = 0
        else:
            self._air_time += 1

        should_snap_down = self._last_jump_time > 3 and self._air_time <= 1 and self._y_vel >= 0
        self.snap_down_sensor.set_enabled(should_snap_down)

        self._last_jump_time += 1

    def is_grounded(self):
        return (len(self.get_world().get_sensor_state(self.foot_sensor_id)) > 0 or
                len(self.get_world().get_sensor_state(self.foot_slope_sensor_left_id)) > 0 or
                len(self.get_world().get_sensor_state(self.foot_slope_sensor_right_id)) > 0)

    def is_left_walled(self):
        return len(self.get_world().get_sensor_state(self.left_sensor_id)) > 0

    def is_right_walled(self):
        return len(self.get_world().get_sensor_state(self.right_sensor_id)) > 0

    def is_on_left_slope(self):
        return len(self.get_world().get_sensor_state(self.foot_slope_sensor_left_id)) > 0

    def is_on_right_slope(self):
        return len(self.get_world().get_sensor_state(self.foot_slope_sensor_right_id)) > 0

    def is_on_flat_ground(self):
        return len(self.get_world().get_sensor_state(self.foot_sensor_id)) > 0

    def is_clinging_to_wall(self):
        return not self.is_grounded() and (self.is_left_walled() or self.is_right_walled())

    def _handle_inputs(self):
        keys = keybinds.get_instance()
        request_left = inputs.get_instance().is_held(keys.get_keys(const.MOVE_LEFT))
        request_right = inputs.get_instance().is_held(keys.get_keys(const.MOVE_RIGHT))
        request_jump = inputs.get_instance().was_pressed(keys.get_keys(const.JUMP))  # TODO add some buffer
        holding_jump = inputs.get_instance().is_held(keys.get_keys(const.JUMP))

        dx = 0
        if request_left:
            dx -= 1
        if request_right:
            dx += 1

        # wall cling stuff
        if not self.is_grounded() and (self.is_left_walled() or self.is_left_walled()):
            if (dx == 1 and self.is_left_walled()) or (dx == -1 and self.is_right_walled()):
                if self._wall_cling_count < self._wall_cling_time:
                    dx = 0
                self._wall_cling_count += 1
            else:
                dx = 0
                self._wall_cling_count = 0
        else:
            self._wall_cling_count = 0

        if dx != 0:
            accel = 0
            if self.is_grounded():
                if self._x_vel <= 0 < dx or dx < 0 <= self._x_vel:
                    accel += self._ground_reverse_dir_bonus_accel
                accel += self._ground_accel
            else:
                accel += self._air_accel

            x_accel = dx * accel
            y_accel = 0

            # alter the angle of motion if we're on a slope
            if self.is_on_left_slope() and not self.is_on_flat_ground() and not self.is_on_right_slope():
                x_accel, y_accel = util.rotate((x_accel, y_accel), util.to_rads(22.5))
            elif self.is_on_right_slope() and not self.is_on_flat_ground() and not self.is_on_left_slope():
                x_accel, y_accel = util.rotate((x_accel, y_accel), util.to_rads(-22.5))

            new_x_vel = self._x_vel + x_accel
            new_x_vel_bounded = util.bound(new_x_vel, -self._x_vel_max, self._x_vel_max)

            self.set_x_vel(new_x_vel_bounded)

            if y_accel != 0:
                new_y_vel = self._y_vel + y_accel
                self.set_y_vel(new_y_vel)
        else:
            fric = self._ground_x_friction if self.is_grounded() else self._air_x_friction
            self.set_x_vel(self._x_vel * fric)

        if request_jump and self._last_jump_time >= self._jump_cooldown:
            if self.is_grounded():
                self.set_y_vel(self._y_vel - self._jump_y_vel)
                self._last_jump_time = 0
            else:
                if self.is_left_walled() or self.is_right_walled():
                    self.set_y_vel(-self._wall_jump_y_vel)
                    self._last_jump_time = 0

                    if self.is_left_walled():
                        self.set_x_vel(self._x_vel + self._wall_jump_x_vel)
                    if self.is_right_walled():
                        self.set_x_vel(self._x_vel - self._wall_jump_x_vel)

        if self._y_vel < 0 and not holding_jump:
            # short hopping
            self._y_vel *= self._bonus_y_fric_on_let_go

    def update_frame_of_reference_parent(self):
        blocks_upon = self.get_world().get_sensor_state(self.foot_sensor_id)
        if len(blocks_upon) == 0:
            self.set_frame_of_reference_parent(None)
        elif len(blocks_upon) == 1:
            self.set_frame_of_reference_parent(blocks_upon[0])
        else:
            # figure out which one we're on more
            xy = self.get_xy(raw=False)
            collider_rect = self.foot_sensor.get_rect(xy)
            max_overlap = -1
            max_overlap_block = None
            for block in blocks_upon:
                for block_collider in block.all_colliders():
                    block_collider_rect = block_collider.get_rect(block.get_xy(raw=False))
                    overlap_rect = util.get_rect_intersect(collider_rect, block_collider_rect)
                    if overlap_rect is None:
                        continue  # ??
                    elif overlap_rect[2] * overlap_rect[3] > max_overlap:
                        max_overlap = overlap_rect[2] * overlap_rect[3]
                        max_overlap_block = block

            if max_overlap_block is not None:
                self.set_frame_of_reference_parent(max_overlap_block)

    def get_debug_color(self):
        return colors.BLUE


class CollisionMask:

    def __init__(self, name, is_solid=True, is_sensor=False):
        self._name = name
        self._is_solid = is_solid
        self._is_sensor = is_sensor

    def get_name(self) -> str:
        return self._name

    def is_solid(self) -> bool:
        return self._is_solid

    def is_sensor(self) -> bool:
        return self._is_sensor


class CollisionMasks:

    BLOCK = CollisionMask("block")

    SLOPE_BLOCK_HORZ = CollisionMask("slope_block_horz")
    SLOPE_BLOCK_VERT = CollisionMask("slope_block_vert")

    ACTOR = CollisionMask("actor")

    SENSOR = CollisionMask("block_sensor", is_solid=False, is_sensor=True)

    SNAP_DOWN_SENSOR = CollisionMask("snap_down_sensor", is_solid=False, is_sensor=True)


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

    def __init__(self, points, mask, collides_with=None, resolution_hint=None, color=colors.RED):
        self._mask = mask
        self._collides_with = [] if collides_with is None else util.listify(collides_with)
        self._points = points
        self._resolution_hint = resolution_hint if resolution_hint is not None else CollisionResolutionHints.BOTH

        self._debug_color = color
        self._id = _next_collider_id()

        self._is_enabled = True

    def get_id(self):
        return self._id

    def set_enabled(self, val):
        self._is_enabled = val

    def is_enabled(self):
        return self._is_enabled

    def get_mask(self):
        return self._mask

    def get_resolution_hint(self):
        return self._resolution_hint

    def collides_with(self, other):
        return other.get_mask() in self._collides_with

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
            return util.get_rect_containing_points(pts)

    def get_debug_color(self):
        return self._debug_color

    def __eq__(self, other):
        if isinstance(other, PolygonCollider):
            return self._id == other._id
        else:
            return False

    def __hash__(self):
        return self._id


class TriangleCollider(PolygonCollider):

    def __init__(self, points, mask, collides_with=None, resolution_hint=None, color=colors.RED):
        if len(points) != 3:
            raise ValueError("must have 3 points, instead got: {}".format(points))
        PolygonCollider.__init__(self, points, mask, collides_with=collides_with, resolution_hint=resolution_hint, color=color)

    def is_overlapping(self, offs, other, other_offs):
        if isinstance(other, TriangleCollider):
            return util.triangles_intersect(self.get_points(offs=offs), other.get_points(offs=other_offs))
        elif isinstance(other, RectangleCollider):
            return util.rect_intersects_triangle(other.get_rect(offs=other_offs), self.get_points(offs=offs))
        else:
            return super().is_overlapping(offs, other, other_offs)


class RectangleCollider(PolygonCollider):

    def __init__(self, rect, mask, collides_with=None, resolution_hint=None, color=colors.RED):
        points = [p for p in util.all_rect_corners(rect, inclusive=False)]
        PolygonCollider.__init__(self, points, mask, collides_with=collides_with, resolution_hint=resolution_hint, color=color)

    def is_overlapping(self, offs, other, other_offs):
        if isinstance(other, RectangleCollider):
            return util.get_rect_intersect(self.get_rect(offs=offs), other.get_rect(offs=other_offs)) is not None
        elif isinstance(other, TriangleCollider):
            return util.rect_intersects_triangle(self.get_rect(offs=offs), other.get_points(offs=other_offs))
        else:
            return super().is_overlapping(offs, other, other_offs)


