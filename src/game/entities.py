
import math
import random
import typing
from typing import Union, List, Iterable

import src as src  # for typing~

import src.utils.util as util
import src.engine.sprites as sprites
import src.engine.spritesheets as spritesheets
import src.engine.inputs as inputs
import src.engine.keybinds as keybinds
import configs as configs

import src.game.spriteref as spriteref
import src.game.playertypes as playertypes
import src.game.colors as colors
import src.game.globalstate as gs
import src.game.const as const
import src.game.debug as debug
import src.game.dialog as dialog
import src.game.particles as particles


_ENT_ID = 0


def next_entity_id():
    global _ENT_ID
    _ENT_ID += 1
    return _ENT_ID - 1


# physics groups
UNKNOWN_GROUP = -1
ENVIRONMENT_GROUP = 5
ACTOR_GROUP = 10
DECORATION_GROUP = 20


# depths
WORLD_UI_DEPTH = -5
PLAYER_DEPTH = 0
PARTICLE_DEPTH = 2
BLOCK_DEPTH = 10


class Entity:

    def __init__(self, x, y, w=None, h=None):
        self._ent_id = next_entity_id()

        self._x = x
        self._y = y

        if w is not None and h is not None:
            # wtf is all this (-_-)
            w = util.assert_int(w, msg="width must be an integer: {}".format(w), error=True)
            h = util.assert_int(h, msg="height must be an integer: {}".format(h), error=True)
            self._size = w, h
        else:
            self._size = None

        self._x_vel = 0  # pixels per tick
        self._y_vel = 0

        self._world = None  # world sets this when entity is added / removed
        self._spec = None   # bp sets this when it creates the entity

        self._color_override = None
        self._is_selected_in_editor = False

        self._debug_sprites = {}

        self._colliders = []

        self._frame_of_reference_parents = []
        self._frame_of_reference_parent_do_horz = True
        self._frame_of_reference_parent_do_vert = True
        self._frame_of_reference_children = []

        # used to let entities "hold" other entities
        self._held_parent = None
        self._held_child = None

        self._perturbs = []

        self._last_updated_at = -1  # should only be set by World

    def get_world(self) -> 'src.game.worlds.World':
        return self._world

    def get_ent_id(self) -> int:
        return self._ent_id

    def get_spec(self):
        return self._spec

    def set_world(self, world):
        self._world = world

    def set_color_override(self, val):
        self._color_override = val

    def get_color_override(self):
        return self._color_override

    def is_color_baked_into_sprites(self):
        return False

    def set_selected_in_editor(self, val):
        self._is_selected_in_editor = val

    def is_selected_in_editor(self):
        return self._is_selected_in_editor

    def about_to_remove_from_world(self):
        pass

    def all_sub_entities(self):
        """All the entities that should be added/removed to World along with this one."""
        return []

    def set_xy_perturbs(self, shake_points):
        self._perturbs = shake_points

    def get_xy_perturb(self):
        if len(self._perturbs) > 0:
            return self._perturbs[-1]
        else:
            return (0, 0)

    def get_rect(self, raw=False, with_xy_perturbs=False):
        xy = self.get_xy(raw=raw, with_xy_perturbs=with_xy_perturbs)
        size = self.get_size()
        return [xy[0], xy[1], size[0], size[1]]

    def get_center(self, raw=False, with_xy_perturbs=False):
        r = self.get_rect(raw=raw, with_xy_perturbs=with_xy_perturbs)
        pt = (r[0] + r[2] / 2, r[1] + r[3] / 2)
        if raw:
            return pt
        else:
            return (int(pt[0]), int(pt[1]))

    def get_xy(self, raw=False, with_xy_perturbs=False):
        res = [self._x, self._y]

        if with_xy_perturbs:
            perturb = self.get_xy_perturb()
            res[0] += perturb[0]
            res[1] += perturb[1]

        if not raw:
            return (int(res[0]), int(res[1]))
        else:
            return tuple(res)

    def set_xy(self, xy, update_frame_of_reference=True):
        old_x = self._x
        old_y = self._y

        if xy[0] is not None:
            self._x = xy[0]
        if xy[1] is not None:
            self._y = xy[1]

        # for the purpose of moving FOR children, we only care about visible motion
        dx = int(self._x) - int(old_x)
        dy = int(self._y) - int(old_y)

        if update_frame_of_reference and (dx != 0 or dy != 0):
            for child in self._frame_of_reference_children:
                child_dx = 0 if not child._frame_of_reference_parent_do_horz else dx
                child_dy = 0 if not child._frame_of_reference_parent_do_vert else dy
                if child_dx == 0 and child_dy == 0:
                    continue
                else:
                    child_dx /= len(child._frame_of_reference_parents)
                    child_dy /= len(child._frame_of_reference_parents)

                    if child_dx == 0:
                        child.set_y(child.get_y(raw=True) + child_dy, update_frame_of_reference=True)
                    elif child_dy == 0:
                        child.set_x(child.get_x(raw=True) + child_dx, update_frame_of_reference=True)
                    else:
                        child.set_xy((child.get_x(raw=True) + child_dx, child.get_y(raw=True) + child_dy),
                                     update_frame_of_reference=True)

        world = self.get_world()
        if world is not None:
            world.rehash_entity(self)

    def set_x(self, x, update_frame_of_reference=True):
        self.set_xy((x, None), update_frame_of_reference=update_frame_of_reference)

    def set_y(self, y, update_frame_of_reference=True):
        self.set_xy((None, y), update_frame_of_reference=update_frame_of_reference)

    def is_dynamic(self):
        """whether this entity's movement is controlled by the physics system"""
        return False

    def get_physics_group(self):
        return UNKNOWN_GROUP

    def is_breaking(self):
        """whether this entity has any BREAKING colliders, or whether it possibly could"""
        return False

    def is_swappable(self):
        """whether this entity is a valid target for 'swap' actions"""
        return False

    def set_frame_of_reference_parents(self, parents, horz=True, vert=True):
        parents = [] if parents is None else util.listify(parents)
        for p in parents:
            if p is not None and p.is_frame_of_reference_child_of(self):
                print("WARN: attempted to create circular frame of reference chain from "
                             "parent ({}) to child ({}), skipping".format(p, self))
                return

        self._frame_of_reference_parent_do_horz = horz
        self._frame_of_reference_parent_do_vert = vert

        if parents == self._frame_of_reference_parents:
            return
        if len(self._frame_of_reference_parents) > 0:
            for p in self._frame_of_reference_parents:
                if self in p._frame_of_reference_children:  # family germs
                    p._frame_of_reference_children.remove(self)

        self._frame_of_reference_parents = []
        for p in parents:
            self._frame_of_reference_parents.append(p)
            p._frame_of_reference_children.append(self)

    def is_frame_of_reference_child_of(self, other, max_depth=-1):
        if max_depth == 0:
            return False
        for p in self._frame_of_reference_parents:
            parent = p
            if other == parent:
                return True
            else:
                if parent.is_frame_of_reference_child_of(other, max_depth=max_depth-1):
                    return True
        return False

    def get_x(self, raw=False, with_xy_perturbs=False):
        return self.get_xy(raw=raw, with_xy_perturbs=with_xy_perturbs)[0]

    def get_y(self, raw=False, with_xy_perturbs=False):
        return self.get_xy(raw=raw, with_xy_perturbs=with_xy_perturbs)[1]

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
        if len(self._perturbs) > 0:
            self._perturbs.pop(-1)

    def update_sprites(self):
        pass

    def update_frame_of_reference_parents(self):
        pass

    def pickup_entity(self, ent):
        if self._held_child is not None:
            # detach own child
            self._held_child._held_parent = None
        if ent is not None:
            if ent._held_parent is not None:
                # detach ent from old parent
                ent._held_parent._held_child = None
            ent._held_parent = self
        self._held_child = ent

    def break_free_from_parent(self):
        parent = self.get_held_by()
        if parent is not None:
            parent.pickup_entity(None)

    def is_held(self):
        return self._held_parent is not None

    def get_held_by(self):
        return self._held_parent

    def get_held_entity(self):
        return self._held_child

    def is_holding_an_entity(self):
        return self.get_held_entity() is not None

    def get_held_entity_position(self, entity, raw=True):
        rect = self.get_rect(raw=raw)
        erect = entity.get_rect()
        return [rect[0] + rect[2] // 2 - erect[2] // 2, rect[1] - erect[3]]

    def get_weight(self):
        if self.is_holding_an_entity():
            return 1 + self.get_held_entity().get_weight()
        else:
            return 1

    def all_colliders(self, solid=None, sensor=None, enabled=True) -> typing.Iterable['PolygonCollider']:
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

    def add_collider(self, collider):
        self._colliders.append(collider)

    def was_crushed(self):
        pass

    def fell_out_of_bounds(self):
        print("INFO: entity fell out of bounds: {}".format(self))
        self.get_world().remove_entity(self)

    def all_sprites(self):
        return []

    def _update_main_body_debug_sprites(self, main_body_key):
        if main_body_key not in self._debug_sprites:
            self._debug_sprites[main_body_key] = sprites.RectangleSprite(spriteref.POLYGON_LAYER)

        self._debug_sprites[main_body_key].update(new_rect=self.get_rect(), new_color=self.get_debug_color(),
                                                  new_depth=30)

    def all_debug_sprites(self):
        main_body_key = "main_body"
        self._update_main_body_debug_sprites(main_body_key)
        if main_body_key in self._debug_sprites and self._debug_sprites[main_body_key] is not None:
            body_sprites = util.listify(self._debug_sprites[main_body_key])
            for spr in body_sprites:
                if spr is not None:
                    yield spr

        rect_colliders_key = "rect_colliders"
        if rect_colliders_key not in self._debug_sprites:
            self._debug_sprites[rect_colliders_key] = []

        all_colliders = [c for c in self.all_colliders() if debug.should_show_debug_sprite_with_name(c.get_name())]

        all_rect_colliders = [c for c in all_colliders if isinstance(c, RectangleCollider) if c.is_enabled()]

        util.extend_or_empty_list_to_length(self._debug_sprites[rect_colliders_key], len(all_rect_colliders),
                                            creator=lambda: sprites.RectangleOutlineSprite(spriteref.POLYGON_LAYER))
        for collider, rect_sprite in zip(all_rect_colliders, self._debug_sprites[rect_colliders_key]):
            color = collider.get_debug_color()

            if collider.is_sensor() and len(self.get_world().get_sensor_state(collider.get_id())) <= 0:
                color = colors.PERFECT_PINK

            rect = collider.get_rect(offs=self.get_xy())
            rect_sprite.update(new_rect=rect, new_color=color, new_outline=1,
                               new_depth=collider.get_mask().get_render_depth())
            yield rect_sprite

        triangle_colliders_key = "triangle_colliders"
        if triangle_colliders_key not in self._debug_sprites:
            self._debug_sprites[triangle_colliders_key] = []

        all_triangle_colliders = [c for c in all_colliders if isinstance(c, TriangleCollider) if c.is_enabled()]

        util.extend_or_empty_list_to_length(self._debug_sprites[triangle_colliders_key], len(all_triangle_colliders),
                                            creator=lambda: sprites.TriangleOutlineSprite(spriteref.POLYGON_LAYER))

        new_triangle_sprites = []
        for collider, triangle_sprite in zip(all_triangle_colliders, self._debug_sprites[triangle_colliders_key]):
            color = collider.get_debug_color()

            if collider.is_sensor() and len(self.get_world().get_sensor_state(collider.get_id())) <= 0:
                color = colors.PERFECT_PINK

            points = collider.get_points(offs=self.get_xy())
            depth = collider.get_mask().get_render_depth()
            new_triangle_sprites.append(triangle_sprite.update(new_points=points, new_outline=1,
                                                               new_color=color, new_depth=depth))
            yield triangle_sprite

        self._debug_sprites[triangle_colliders_key] = new_triangle_sprites

    def get_debug_color(self):
        return colors.PERFECT_WHITE

    def get_color_id(self):
        return None

    def get_color(self, ignore_override=False):
        """return: the tint applied to this entity's sprites"""
        if not ignore_override and self.get_color_override() is not None:
            return self.get_color_override()
        elif self.get_color_id() is not None and not self.is_color_baked_into_sprites():
            return spriteref.get_color(self.get_color_id())
        else:
            return colors.PERFECT_WHITE

    def dir_facing(self):
        """return: -1 or 1"""
        return 1

    def is_block(self):
        return isinstance(self, AbstractBlockEntity)

    def is_end_block(self):
        return isinstance(self, EndBlock)

    def is_start_block(self):
        return isinstance(self, StartBlock)

    def is_player(self):
        return isinstance(self, PlayerEntity)

    def is_teleporter(self):
        return isinstance(self, TeleporterBlock)

    def is_camera_bound_marker(self):
        return isinstance(self, CameraBoundMarker)

    def can_be_picked_up(self):
        # might add more pick-uppdable things later, but for now it's just players
        return self.is_player() and self.get_player_type().can_be_grabbed()

    def is_actor(self):
        return self.is_player()

    def __eq__(self, other):
        if isinstance(other, Entity):
            return self._ent_id == other._ent_id
        else:
            return False

    def __lt__(self, other):
        if isinstance(other, Entity):
            return self._ent_id < other._ent_id
        else:
            return True

    def __hash__(self):
        return self._ent_id

    def __repr__(self):
        return "{}({}, {})".format(type(self).__name__, self._ent_id, self.get_rect())

    @classmethod
    def this_and_all_entity_superclasses(cls, _res=None):
        if _res is None:
            _res = set()
        _res.add(cls)
        for c in cls.__mro__:
            if c is not cls and c not in _res and (c is Entity or issubclass(c, Entity)):
                _res.add(c)
                for _ in c.this_and_all_entity_superclasses(_res=_res):
                    pass
        return _res


class DynamicEntity(Entity):

    def is_dynamic(self):
        return True


class HasLightSourcesEntity(Entity):

    def get_light_sources(self):
        """returns: list of ((x, y), radius, (r, g, b))"""
        return []


class AbstractBlockEntity(Entity):

    def __init__(self, x, y, w=None, h=None):
        Entity.__init__(self, x, y, w=w, h=h)

        # lighting calculations are a bit expensive, so we only update each block once per X frames,
        # and we apply a random offset so they aren't all updating on the same frame.
        self._cached_color_this_frame = [-1, colors.WHITE]
        self._color_recalc_period = 10
        self._color_recalc_offset = random.randint(0, self._color_recalc_period)

    def update(self):
        super().update()

    def get_debug_color(self):
        return colors.PERFECT_DARK_GRAY

    def get_color_id(self):
        return 0

    def is_color_baked_into_sprites(self):
        return False

    def get_color(self, ignore_override=False, include_lighting=True):
        base_color = super().get_color(ignore_override=ignore_override)
        if not ignore_override and self.get_color_override() is not None:
            return base_color
        elif not include_lighting or not gs.get_instance().settings().get(gs.Settings.SHOW_LIGHTING):
            return base_color
        else:
            cur_tick = gs.get_instance().tick_count()
            last_recalc_tick = self._cached_color_this_frame[0]
            if last_recalc_tick < 0 or (last_recalc_tick != cur_tick
                                        and (cur_tick - self._color_recalc_offset) % self._color_recalc_period == 0):
                w = self.get_world()
                dark_color = colors.darken(base_color, 0.333)
                bright_color = colors.lighten(base_color, 0.333)
                if w is not None:
                    light_sources = w.all_light_sources_at_pt(self.get_center(), exact=False)
                    max_dist_factor = 0
                    for l in light_sources:
                        light_center, radius, color, strength = l
                        # dist = util.dist_from_point_to_rect(light_center, self.get_rect())
                        dist = util.dist(light_center, self.get_center())
                        dist_factor = min(1, (1 - (dist / radius) ** 2) * strength)
                        max_dist_factor = max(max_dist_factor, dist_factor)

                    color = util.linear_interp(dark_color, bright_color, max_dist_factor)
                    dark_color = colors.to_floatn(colors.to_intn(color))
                self._cached_color_this_frame[0] = gs.get_instance().tick_count()
                self._cached_color_this_frame[1] = dark_color

            return self._cached_color_this_frame[1]

    def all_sprites(self):
        for spr in self.all_debug_sprites():
            yield spr

    def get_physics_group(self):
        return ENVIRONMENT_GROUP

    def is_breakable(self):
        return False


class BlockEntity(AbstractBlockEntity):
    """basic rectangular block."""

    @staticmethod
    def build_colliders_for_rect(rect):
        return [RectangleCollider(rect, CollisionMasks.BLOCK, color=colors.PERFECT_RED)]

    def __init__(self, x, y, w, h, art_id=0, color_id=0):
        AbstractBlockEntity.__init__(self, x, y, w=w, h=h)
        self.set_colliders(BlockEntity.build_colliders_for_rect([0, 0, w, h]))

        self._art_id = art_id if art_id >= 0 else int(random.random() * 100)
        self._color_id = color_id if color_id >= 0 else int(random.random() * 5)

        self._sprite = None

    def update(self):
        super().update()

    def get_color_id(self):
        return self._color_id

    def get_main_model(self):
        if self._art_id is not None:
            x_size = self.get_w() / gs.get_instance().cell_size
            y_size = self.get_h() / gs.get_instance().cell_size
            return spriteref.block_sheet().get_block_sprite((x_size, y_size), self._art_id)
        else:
            return None

    def update_sprites(self):
        img = self.get_main_model()

        if img is not None:
            if self._sprite is None or not isinstance(self._sprite, sprites.ImageSprite):
                self._sprite = sprites.ImageSprite.new_sprite(spriteref.BLOCK_LAYER)
            ratio = (self.get_w() / img.width(), self.get_h() / img.height())
            self._sprite = self._sprite.update(new_model=img,
                                               new_x=self.get_x(with_xy_perturbs=True),
                                               new_y=self.get_y(with_xy_perturbs=True),
                                               new_scale=1, new_depth=0, new_color=self.get_color(),
                                               new_ratio=ratio)
        else:
            scale = 1
            inner_rect = util.rect_expand(self.get_rect(with_xy_perturbs=True),
                                          all_expand=-spriteref.block_sheet().border_inset * scale)
            if self._sprite is None or not isinstance(self._sprite, sprites.BorderBoxSprite):
                self._sprite = sprites.BorderBoxSprite(spriteref.BLOCK_LAYER, inner_rect,
                                                       all_borders=spriteref.block_sheet().border_sprites)
            self._sprite = self._sprite.update(new_rect=inner_rect, new_scale=scale,
                                               new_color=self.get_color(), new_bg_color=self.get_color())

    def all_sprites(self):
        if self._sprite is not None:
            yield self._sprite
        else:
            for spr in super().all_debug_sprites():
                yield spr


class BreakableBlockEntity(BlockEntity):

    def __init__(self, x, y, w, h, art_id=0, color_id=0):
        super().__init__(x, y, w, h, art_id=art_id, color_id=color_id)

        for c in self.all_colliders():
            if c.get_mask() == CollisionMasks.BLOCK:
                c.set_mask(CollisionMasks.BREAKABLE)

        breaking_sensor = RectangleCollider([0, 0, w, h], CollisionMasks.SENSOR,
                                            collides_with=(CollisionMasks.BREAKING,))
        self._breaking_sensor_id = breaking_sensor.get_id()
        self._sensor_ent = SensorEntity([0, 0, w, h], breaking_sensor, parent=self)

    def all_sub_entities(self):
        yield self._sensor_ent

    def is_breakable(self):
        return True

    def _add_broken_particles(self):
        model_size = spriteref.object_sheet().thin_block_broken_pieces_horz[0].size()
        particles = []
        positions = []
        if self.get_w() >= self.get_h():
            anims = spriteref.object_sheet().thin_block_broken_pieces_horz
            for i in range(0, self.get_w() // model_size[0] + 1):
                positions.append((self.get_x() + i * model_size[0], self.get_y() + self.get_h() // 2 - model_size[1] // 2))
        else:
            anims = spriteref.object_sheet().thin_block_broken_pieces_vert
            for i in range(0, self.get_h() // model_size[1] + 1):
                positions.append((self.get_x() + model_size[0] // 2, self.get_y() + i * model_size[1]))

        for xy in positions:
            particles.append(RotatingParticleEntity(xy[0], xy[1], anims, color=self.get_color(), duration=45, initial_phasing=60))

        w = self.get_world()
        if w is not None:
            for p in particles:
                w.add_entity(p)

    def update(self):
        super().update()

        w = self.get_world()
        if w is not None:
            if len(w.get_sensor_state(self._breaking_sensor_id)) > 0:
                self._add_broken_particles()
                w.remove_entity(self)
                print("INFO: breakable block broke! {}".format(self))
                # TODO sound


class FallingBlockEntity(BlockEntity, DynamicEntity):

    def __init__(self, x, y, w, h, weight_thresh=1, color_id=0):
        super().__init__(x, y, w, h, color_id=color_id)

        all_colliders = []

        # so players collide with it
        all_colliders.extend(BlockEntity.build_colliders_for_rect([0, 0, w, h]))

        # avoids other blocks
        self.vert_block_avoider = RectangleCollider([2, 0, w - 4, h],
                                                    CollisionMasks.ACTOR,
                                                    collides_with=CollisionMasks.BLOCK,
                                                    resolution_hint=CollisionResolutionHints.VERT_ONLY)
        self.vert_block_avoider.set_ignore_collisions_with(all_colliders)  # no self-collisions
        self.vert_block_avoider.set_enabled(False)
        all_colliders.append(self.vert_block_avoider)

        # so that breakables can sense us while falling
        self.breaking_collider = RectangleCollider([0, 0, w, h], CollisionMasks.BREAKING)
        all_colliders.append(self.breaking_collider)

        # stops or prevents us from falling if we're on something solid
        ground_sensor = RectangleCollider([2, 0, w - 4, h + 1], CollisionMasks.SENSOR,
                                          collides_with=(CollisionMasks.BLOCK, CollisionMasks.BREAKABLE))

        # if it falls onto a slope, it dies
        slope_sensor = RectangleCollider([0, 0, w, h], CollisionMasks.SENSOR,
                                         collides_with=(
                                         CollisionMasks.SLOPE_BLOCK_VERT, CollisionMasks.SLOPE_BLOCK_HORZ))

        # used to detect actors standing on top of it, which triggers it to start falling
        actor_sensor = RectangleCollider([0, -2, w, 2], CollisionMasks.SENSOR, collides_with=(CollisionMasks.ACTOR))

        self.ground_sensor_id = ground_sensor.get_id()
        self.slope_sensor_id = slope_sensor.get_id()
        self.actor_sensor_id = actor_sensor.get_id()

        all_sensors = [ground_sensor, slope_sensor, actor_sensor]

        super().__init__(x, y, w, h, color_id=color_id)

        for c in all_colliders + all_sensors:
            # XXX collisions with moving blocks are just too messy
            c.add_entity_ignore_condition(lambda e: isinstance(e, MovingBlockEntity) or e is self)

        self.set_colliders(all_colliders)
        self._sensor_ent = SensorEntity([0, 0, w, h], all_sensors, parent=self)

        self.fall_speed = 2
        self.weight_thresh = weight_thresh

        self._is_primed_to_fall = False
        self._is_falling = False

    def is_color_baked_into_sprites(self):
        return True

    def get_main_model(self):
        if self._art_id is not None:
            x_size = self.get_w() / gs.get_instance().cell_size
            y_size = self.get_h() / gs.get_instance().cell_size
            return spriteref.object_sheet().get_pushable_block_sprite((x_size, y_size), self.get_color_id())
        else:
            return super().get_main_model()

    def all_sub_entities(self):
        for e in super().all_sub_entities():
            yield e
        yield self._sensor_ent

    def was_crushed(self):
        # TODO sound, particles
        self.get_world().remove_entity(self)

    def update(self):
        super().update()

        if self.get_world().is_waiting():
            return
        else:
            ground_collisions = self.get_world().get_sensor_state(self.ground_sensor_id)

            if self.get_world().get_sensor_state(self.slope_sensor_id):
                self.was_crushed()
            elif self._is_falling:
                if ground_collisions:
                    self.stop_falling()
            else:
                current_weight_on_top = 0
                for a in self.get_world().get_sensor_state(self.actor_sensor_id):
                    if isinstance(a, PlayerEntity) and a.is_grounded():
                        current_weight_on_top += a.get_weight()
                if ground_collisions:
                    self._is_primed_to_fall = False
                elif current_weight_on_top >= self.weight_thresh and not self._is_primed_to_fall:
                    self.set_primed_to_fall()
                elif current_weight_on_top == 0 and self._is_primed_to_fall:
                    self.start_falling()

    def _calc_is_grounded(self):
        for b in self.get_world().get_sensor_state(self.ground_sensor_id):
            if b is not self:
                return True
        return False

    def set_primed_to_fall(self):
        if not self._is_primed_to_fall:
            self._is_primed_to_fall = True
            self.set_xy_perturbs(util.get_shake_points(2, 10))
            # TODO sound?

    def start_falling(self):
        # TODO shake again?
        self._is_falling = True
        self._is_primed_to_fall = False
        self.set_y_vel(self.fall_speed)

        self.vert_block_avoider.set_enabled(True)
        self._adjust_colliders_for_breaking(True)

        self.set_xy_perturbs(util.get_shake_points(3, 60, freq=2))

    def stop_falling(self):
        self._is_falling = False
        self._is_primed_to_fall = False
        self.set_y_vel(0)

        self.vert_block_avoider.set_enabled(False)
        self._adjust_colliders_for_breaking(False)

        self.set_xy_perturbs([])

    def _adjust_colliders_for_breaking(self, breaking):
        self._is_currently_breaking = breaking
        self.breaking_collider.set_enabled(breaking)
        all_colliders = [c for c in self.all_colliders()]
        all_colliders.extend([c for c in self._sensor_ent.all_colliders(sensor=True)])

        for c in all_colliders:
            if c.collides_with_masks((CollisionMasks.BLOCK,)):
                new_collides_with = [m for m in c.get_collides_with() if m != CollisionMasks.BREAKABLE]
                if not breaking:
                    # if we're breaking, we want to move through breaking blocks, so we can break them
                    new_collides_with.append(CollisionMasks.BREAKABLE)
                c.set_collides_with(new_collides_with)


class SensorEntity(DynamicEntity):

    def __init__(self, rect, sensors, parent=None):
        self.parent = parent
        super().__init__(0, 0, w=rect[2], h=rect[3])

        if self.parent is not None:
            self.set_xy((self.parent.get_x() + rect[0], self.parent.get_y() + rect[1]))
            self.set_frame_of_reference_parents(self.parent)
        else:
            self.set_xy((rect[0], rect[1]))

        self.set_colliders(util.listify(sensors))

    def get_physics_group(self):
        return ACTOR_GROUP


class CompositeBlockEntity(AbstractBlockEntity):

    class BlockSpriteInfo:
        def __init__(self, model_provider=lambda: None, color_provider=lambda: None, xy_offs=(0, 0), rotation=0, scale=1, xflip=False):
            self.model_provider = model_provider
            self.color_provider = color_provider
            self.xy_offs = xy_offs
            self.rotation = rotation
            self.xflip = xflip
            self.scale = scale

    def __init__(self, x, y, colliders, sprite_infos, color_id=0):
        """
        colliders: list of colliders in block
        sprite_infos: list of sprites in block
        color_id: block color
        """
        AbstractBlockEntity.__init__(self, x, y)
        self.set_colliders(colliders)
        self._sprite_infos = sprite_infos

        self._color_id = color_id if color_id >= 0 else int(random.random() * 5)

        self._sprites = []

    def get_color_id(self):
        return self._color_id

    def get_size(self):
        all_rects = [c.get_rect(offs=(0, 0)) for c in self.all_colliders()]
        total_rect = util.rect_union(all_rects)
        if total_rect is None:
            return (0, 0)
        else:
            return (total_rect[2], total_rect[3])

    def update_sprites(self):
        util.extend_or_empty_list_to_length(self._sprites, len(self._sprite_infos),
                                            creator=lambda: sprites.ImageSprite.new_sprite(spriteref.BLOCK_LAYER))
        for i in range(0, len(self._sprite_infos)):
            info = self._sprite_infos[i]
            spr = self._sprites[i]
            spr_color = info.color_provider()

            x = self.get_x()
            y = self.get_y()
            self._sprites[i] = spr.update(new_model=info.model_provider(),
                                          new_x=x + info.xy_offs[0], new_y=y + info.xy_offs[1],
                                          new_scale=info.scale, new_xflip=info.xflip,
                                          new_color=spr_color if spr_color is not None else self.get_color(),
                                          new_rotation=info.rotation)

    def all_sprites(self):
        if len(self._sprites) > 0:
            for spr in self._sprites:
                yield spr
        else:
            for spr in super().all_sprites():
                yield spr

    def _update_main_body_debug_sprites(self, main_body_key):
        all_colliders = [c for c in self.all_colliders()]
        if main_body_key not in self._debug_sprites:
            self._debug_sprites[main_body_key] = []
        util.extend_or_empty_list_to_length(self._debug_sprites[main_body_key], len(all_colliders), creator=None)
        for i in range(0, len(all_colliders)):
            c = all_colliders[i]
            spr = self._debug_sprites[main_body_key][i]
            if isinstance(c, TriangleCollider):
                if spr is None or not isinstance(spr, sprites.TriangleSprite):
                    spr = sprites.TriangleSprite(spriteref.POLYGON_LAYER)
                spr = spr.update(new_points=c.get_points(offs=self.get_xy()),
                                 new_color=self.get_debug_color(), new_depth=30)
            elif isinstance(c, RectangleCollider):
                if spr is None or not isinstance(spr, sprites.RectangleSprite):
                    spr = sprites.RectangleSprite(spriteref.POLYGON_LAYER)
                spr = spr.update(new_rect=c.get_rect(offs=self.get_xy()),
                                 new_color=self.get_debug_color(), new_depth=30)
            else:
                spr = None

            self._debug_sprites[main_body_key][i] = spr


def _update_point_sprites_for_editor(show, sprite_list, points, size):
    if not show:
        sprite_list.clear()
    else:
        util.extend_or_empty_list_to_length(sprite_list, len(points),
                                            creator=lambda: sprites.RectangleOutlineSprite(spriteref.POLYGON_LAYER))
        for i in range(0, len(points)):
            pt = points[i]
            pt_sprite = sprite_list[i]
            sprite_list[i] = pt_sprite.update(new_rect=[pt[0], pt[1], size[0], size[1]],
                                              new_outline=1, new_color=colors.PERFECT_YELLOW,
                                              new_depth=-500)


class MoveBetweenPointsController:

    def __init__(self, obj, pts, period=90, loop=True):
        self.obj = obj

        self._pts = pts
        self._period = period
        self._loop = loop

        self._point_sprites_for_editor = []

    def update(self):
        tick_count = self.obj.get_world().get_tick()

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

        old_xy = self.obj.get_xy(raw=True)

        self.obj.set_xy(pos)
        self.obj.set_vel(util.sub(old_xy, pos))

    def all_sprites(self):
        for spr in self._point_sprites_for_editor:
            yield spr

    def update_sprites(self):
        _update_point_sprites_for_editor(self.obj.is_selected_in_editor(), self._point_sprites_for_editor,
                                         self._pts, self.obj.get_size())


class MovingBlockEntity(BlockEntity):

    def __init__(self, w, h, pts, period=90, loop=True, art_id=0, color_id=0):
        super().__init__(pts[0][0], pts[0][1], w, h, art_id=art_id, color_id=color_id)

        self.controller = MoveBetweenPointsController(self, pts, period=period, loop=loop)

    def update(self):
        super().update()
        self.controller.update()

    def update_sprites(self):
        super().update_sprites()
        self.controller.update_sprites()

    def all_sprites(self):
        for spr in super().all_sprites():
            yield spr
        for spr in self.controller.all_sprites():
            yield spr


class DoorBlock(BlockEntity, HasLightSourcesEntity):

    def __init__(self, x, y, w, h, toggle_idx, inverted=False):
        BlockEntity.__init__(self, x, y, w, h)
        self._toggle_idx = toggle_idx
        self._is_solid = True
        self._inverted = inverted

    def get_toggle_idx(self):
        return self._toggle_idx

    def update(self):
        super().update()
        should_be_solid = (not self.get_world().is_door_unlocked(self._toggle_idx)) ^ self._inverted
        if self._is_solid != should_be_solid:
            if should_be_solid:
                # TODO kill any player within bounds after becoming solid
                players = [p for p in self.get_world().all_entities_in_rect(self.get_rect(), cond=lambda e: e.is_player())]
                if len(players) > 0:
                    print("INFO: crushed players: {}".format(players))
            self.set_solid(should_be_solid)

    def is_solid(self):
        return self._is_solid

    def set_solid(self, val):
        self._is_solid = val
        for c in self.all_colliders(solid=True, enabled=None):
            c.set_enabled(val)

    def get_main_model(self):
        w, h = self.get_size()
        return spriteref.object_sheet().get_toggle_block_sprite(self.get_toggle_idx(), w, h, self.is_solid())

    def get_light_sources(self):
        strength = 0.75 if self.is_solid() else 0.5
        return [(self.get_center(), gs.get_instance().cell_size * 5, colors.WHITE, strength)]


class KeyEntity(Entity):

    @staticmethod
    def make_at_cell(grid_x, grid_y, toggle_idx):
        cs = gs.get_instance().cell_size
        return KeyEntity(int(cs * grid_x + cs // 4), int(cs * grid_y), toggle_idx)

    def __init__(self, x, y, toggle_idx):
        cs = gs.get_instance().cell_size
        Entity.__init__(self, x, y, cs // 2, cs)
        self._toggle_idx = toggle_idx
        self._icon_sprite = None
        self._base_sprite = None

        self._bob_height_min = 4
        self._bob_height_max = 12
        self._bob_tick_period = 90
        self._bob_tick_count = int(random.random() * self._bob_tick_period)

        self._player_colliding_tick_count = 0
        self._player_collide_thresh = 15
        self._player_collide_max = self._player_collide_thresh + 20

        player_collider = RectangleCollider([0, 0, cs // 2, cs], CollisionMasks.SENSOR,
                                            collides_with=(CollisionMasks.ACTOR, CollisionMasks.BLOCK))
        self.player_sensor_id = player_collider.get_id()
        self._sensor_ent = SensorEntity([0, 0, cs // 2, cs], player_collider, parent=self)

    def all_sub_entities(self):
        yield self._sensor_ent

    def is_satisfied(self):
        return self._player_colliding_tick_count >= self._player_collide_thresh

    def all_sprites(self):
        yield self._icon_sprite
        yield self._base_sprite

    def get_toggle_idx(self):
        return self._toggle_idx

    def update(self):
        super().update()

        is_colliding = False
        for s in self.get_world().get_sensor_state(self.player_sensor_id):
            if s.is_player() or isinstance(s, (FallingBlockEntity, MovingBlockEntity, DoorBlock)):
                is_colliding = True
                break

        if is_colliding:
            self._player_colliding_tick_count = min(self._player_collide_max, self._player_colliding_tick_count + 1)
        else:
            self._player_colliding_tick_count = max(0, self._player_colliding_tick_count - 1)

        if self.is_satisfied():
            # reset the cycle so it starts at the bottom when it resumes bobbing
            self._bob_tick_count = int(3 / 4 * self._bob_tick_period)

        self._update_sprites()

    def _update_sprites(self):
        rect = self.get_rect()
        if self._icon_sprite is None:
            self._icon_sprite = sprites.ImageSprite.new_sprite(spriteref.ENTITY_LAYER, depth=-5)
        key_model = spriteref.object_sheet().toggle_block_icons[self.get_toggle_idx()]
        base_model = spriteref.object_sheet().toggle_block_bases[self.get_toggle_idx()]

        bob_prog = (1 + math.cos(2 * 3.141529 * self._bob_tick_count / self._bob_tick_period)) / 2
        bob_height = int(self._bob_height_min + (self._bob_height_max - self._bob_height_min) * bob_prog)

        color = self.get_color()

        if self.is_satisfied():
            bob_height = 0
        else:
            bob_height = int(bob_height * (1 - self._player_colliding_tick_count / self._player_collide_thresh))

        self._icon_sprite = self._icon_sprite.update(new_model=key_model,
                                                     new_x=rect[0] + rect[2] // 2 - key_model.width() // 2,
                                                     new_y=rect[1] + rect[3] - bob_height - key_model.height(),
                                                     new_color=color)
        self._bob_tick_count += 1

        if self._base_sprite is None:
            self._base_sprite = sprites.ImageSprite.new_sprite(spriteref.ENTITY_LAYER, depth=-3)
        self._base_sprite = self._base_sprite.update(new_model=base_model,
                                                     new_x=rect[0] + rect[2] // 2 - base_model.width() // 2,
                                                     new_y=rect[1] + rect[3] - base_model.height(),
                                                     new_color=color)


class StartBlock(BlockEntity, HasLightSourcesEntity):

    def __init__(self, x, y, w, h, player_type, facing_dir=1, color_id=-1):
        cs = gs.get_instance().cell_size
        if w != cs and w != cs * 2:
            raise ValueError("illegal width for start block: {}".format(w))
        if h != cs:
            raise ValueError("illegal height for start block: {}".format(h))

        self._player_type = player_type
        self._facing_dir = 1 if facing_dir >= 0 else -1

        if color_id < 0:
            color_id = player_type.get_color_id()

        BlockEntity.__init__(self, x, y, w, h, color_id=color_id)

    def get_player_type(self):
        return self._player_type

    def get_facing_dir(self):
        return self._facing_dir

    def get_light_sources(self):
        return [(self.get_center(), 3 * gs.get_instance().cell_size, colors.PERFECT_WHITE, 0.5)]

    def get_main_model(self):
        cs = gs.get_instance().cell_size
        size = (self.get_w() // cs, self.get_h() // cs)
        return spriteref.block_sheet().get_start_block_sprite(size, self.get_player_type().get_id())


class AbstractActorSensorBlock(CompositeBlockEntity):

    def __init__(self, x, y, w, h, dip_h=3, nub_w=2, color_id=-1, sensor_name="unnamed_player_sensor_block"):
        colliders = []
        colliders.extend(BlockEntity.build_colliders_for_rect([nub_w, dip_h, w - nub_w * 2, h - dip_h]))  # center
        colliders.extend(BlockEntity.build_colliders_for_rect([0, 0, nub_w, h]))                          # left
        colliders.extend(BlockEntity.build_colliders_for_rect([w - nub_w, 0, nub_w, h]))                  # right

        CompositeBlockEntity.__init__(self, x, y, colliders, self.get_sprite_infos(), color_id=color_id)

        # this is what it uses to detect the player (normally blocks can't have sensors)
        player_collider = RectangleCollider([0, 0, w - nub_w * 2, h // 2], CollisionMasks.SENSOR,
                                            collides_with=CollisionMasks.ACTOR,
                                            name=sensor_name)
        self._player_sensor_id = player_collider.get_id()
        self._sensor_ent = SensorEntity([nub_w, 0, w - nub_w * 2, dip_h + 2], player_collider, parent=self)

    def all_sub_entities(self):
        yield self._sensor_ent

    def get_sensor_id(self):
        return self._player_sensor_id

    def get_sprite_infos(self) -> List[CompositeBlockEntity.BlockSpriteInfo]:
        raise NotImplementedError()

    def all_actors_currently_in_sensor(self):
        for a in self.get_world().get_sensor_state(self.get_sensor_id()):
            if self.should_accept(a):
                yield a

    def should_accept(self, actor):
        return True


class EndBlock(AbstractActorSensorBlock, HasLightSourcesEntity):

    def __init__(self, x, y, w, h, player_type, color_id=-1):
        cs = gs.get_instance().cell_size
        if w != cs * 2:
            raise ValueError("illegal width for end block: {}".format(w))
        if h != cs:
            raise ValueError("illegal height for end block: {}".format(h))

        self._player_type = player_type
        if color_id < 0:
            color_id = player_type.get_color_id()
        self._is_satisfied = False
        self._ent_ids_satisfying = []

        self._player_stationary_in_sensor_count = 0
        self._player_stationary_in_sensor_limit = 10

        super().__init__(x, y, w, h, color_id=color_id, sensor_name="level_end_{}".format(self._player_type))

    def get_sprite_infos(self):
        return [CompositeBlockEntity.BlockSpriteInfo(model_provider=lambda: self.get_main_model(), xy_offs=(0, 0))]

    def should_accept(self, actor):
        return (isinstance(actor, PlayerEntity)
                and actor.get_player_type() == self._player_type
                and not actor.is_crouching()
                and util.mag(actor.get_vel()) < 2)

    def update(self):
        super().update()
        self._ent_ids_satisfying.clear()

        ents_in_sensor = [e.get_ent_id() for e in self.all_actors_currently_in_sensor()]
        if len(ents_in_sensor) == 1:  # must have exactly ONE copy of a player in it to be satisfied.
            self._player_stationary_in_sensor_count += 1
            self._ent_ids_satisfying.extend(ents_in_sensor)
        else:
            self._player_stationary_in_sensor_count = 0

        was_satisfied = self._is_satisfied
        self._is_satisfied = self._player_stationary_in_sensor_count >= self._player_stationary_in_sensor_limit

        if not was_satisfied and self._is_satisfied:
            print("INFO: satisfied end block for player: {}".format(self.get_player_type()))

    def is_satisfied(self, by=None):
        return self._is_satisfied and (by is None or by.get_ent_id() in self._ent_ids_satisfying)

    def get_player_type(self):
        return self._player_type

    def get_light_sources(self):
        return [(self.get_center(), 3 * gs.get_instance().cell_size, colors.PERFECT_WHITE, 0.5)]

    def get_main_model(self):
        cs = gs.get_instance().cell_size
        size = (self.get_w() // cs, self.get_h() // cs)
        return spriteref.block_sheet().get_end_block_sprite(size, self.get_player_type().get_id())

    def __repr__(self):
        return type(self).__name__ + "({}, {})".format(self.get_rect(), self.get_player_type())


class TeleporterBlock(AbstractActorSensorBlock):
    # XXX with ONE_WAY teleporters, it's possible to create infinite player-duplication machines.
    # I'm not going to prevent that, but levels need to be built in a SANE and RESPONSIBLE manner.

    ONE_WAY = "one_way"
    TWO_WAY = "two_way"

    def __init__(self, x, y, w, h, channel, sending, mode):
        cs = gs.get_instance().cell_size
        if w != cs * 2:
            raise ValueError("illegal width for teleporter: {}".format(w))
        if h != cs:
            raise ValueError("illegal height for teleporter: {}".format(h))

        super().__init__(x, y, w, h, color_id=channel, sensor_name="teleporter_{}".format(channel))

        self._channel = channel
        self._sending = sending
        self._mode = mode

        self._arrow_rot = 0.0

        self._pulse_offset = 10
        self._pulse_colors = ((colors.WHITE, 15), (colors.LIGHT_GRAY, 15), (colors.DARK_GRAY, 60))
        self._pulse_interval = sum([x[1] for x in self._pulse_colors])
        self._pulse_ticks = (channel * self._pulse_interval) // 5

        self._activation_thresh = 30
        self._players_in_sensor = {}  # entity_id -> ticks in sensor (while stationary / not crouching)

        self._post_tele_max_cooldown = 120
        self._post_tele_countdown = 0

        def make_particle(xy):
            if self._sending:
                return FloatingDustParticleEntity(xy, particles.ParticleTypes.CROSS_TINY, 60,
                                                  (0, -1),
                                                  self.get_color(include_lighting=False),
                                                  end_color=colors.PERFECT_BLACK,
                                                  anim_rate=4,
                                                  fric=0.01,
                                                  accel=(0, 0.025),
                                                  max_speed=3,
                                                  max_sway_per_second=3.1415 / 8)
            else:
                return None

        self._particle_emitter = ParticleEmitterZone([0, 3, w, 1], make_particle, 2,
                                                     parent=self,
                                                     xy_provider=lambda: (util.sample_triangular(0.2, 0.8), 1))

    def all_linked_teleporters(self) -> 'Iterable[TeleporterBlock]':
        return self.get_world().all_entities(cond=lambda t: t.get_channel() == self.get_channel() and t.is_sending() is not self.is_sending(), types=(TeleporterBlock,))

    def all_bro_teleporters(self) -> 'Iterable[TeleporterBlock]':
        return self.get_world().all_entities(cond=lambda t: t is not self and t.get_channel() == self.get_channel() and t.is_sending() is self.is_sending(), types=(TeleporterBlock,))

    def all_sub_entities(self):
        for s in super().all_sub_entities():
            yield s
        yield self._particle_emitter

    def is_sending(self):
        return self._sending

    def set_sending(self, val):
        self._sending = val

    def get_channel(self):
        return self._channel

    def get_mode(self):
        return self._mode

    def get_prog(self, for_anim=False):
        if for_anim and not self.is_two_way():
            return 0
        elif self._sending:
            max_time_in_sensor = max(self._players_in_sensor.values(), default=0)
            if max_time_in_sensor >= self._activation_thresh:
                return 1.0
            else:
                return max(0.0, max_time_in_sensor / self._activation_thresh)
        else:
            return 0

    def reset_prog(self):
        self._players_in_sensor.clear()

    def is_two_way(self):
        return self.get_mode() == TeleporterBlock.TWO_WAY

    def get_actors_ready_to_send(self) -> List[int]:
        if self._sending and self._post_tele_countdown <= 0:
            return [p_id for p_id in self._players_in_sensor if self._players_in_sensor[p_id] >= self._activation_thresh]
        else:
            return []

    def is_ready_to_teleport(self):
        if self._sending:
            return len(self.get_actors_ready_to_send()) == 1
        else:
            return True

    def update(self):
        super().update()

        self._pulse_ticks += 1

        if self.get_world().is_waiting():
            return

        if self._post_tele_countdown > 0:
            self._post_tele_countdown -= 1
        else:
            seen = set()
            for p in self.all_actors_currently_in_sensor():
                p_id = p.get_ent_id()
                seen.add(p_id)
                if p_id not in self._players_in_sensor:
                    self._players_in_sensor[p_id] = 0
                else:
                    if (isinstance(p, PlayerEntity)
                            and not p.is_crouching()
                            and util.mag(p.get_vel()) < 2):
                        self._players_in_sensor[p_id] = min(self._activation_thresh, self._players_in_sensor[p_id] + 1)

            to_rem = []
            for p_id in self._players_in_sensor:
                if p_id not in seen:
                    self._players_in_sensor[p_id] -= 1
                    if self._players_in_sensor[p_id] < 0:
                        to_rem.append(p_id)
            for p_id in to_rem:
                del self._players_in_sensor[p_id]

            self._handle_actual_teleports_if_last_to_update()

    def _handle_actual_teleports_if_last_to_update(self):
        if not self.is_ready_to_teleport():
            return
        linked_teles = []
        for linked in self.all_linked_teleporters():
            if self._last_updated_at < linked._last_updated_at and linked.is_ready_to_teleport():
                linked_teles.append(linked)
            else:
                return  # we aren't last, or linked isn't ready
        bro_teles = []
        for bro in self.all_bro_teleporters():
            if self._last_updated_at < bro._last_updated_at and bro.is_ready_to_teleport():
                bro_teles.append(bro)
            else:
                return  # not last, or bro isn't ready

        types_to_send = set()
        actors_to_send = set()
        senders = []
        receivers = []

        for t in linked_teles + bro_teles + [self]:
            if t.is_sending():
                actor_to_send = self.get_world().get_entity_by_id(t.get_actors_ready_to_send()[0])
                if actor_to_send is None:
                    return  # actor no longer exists..?
                elif actor_to_send in actors_to_send:
                    return  # another teleporter is already sending this actor
                else:
                    types_to_send.add(actor_to_send.get_player_type())
                    if len(types_to_send) > 1:
                        return  # multiple types of players are queued to be sent
                    actors_to_send.add(actor_to_send)
                    senders.append((t, actor_to_send))
            else:
                receivers.append(t)

        if len(senders) == 0 or len(receivers) == 0 or len(types_to_send) > 1:
            return

        xy_offs = (0, 0)  # all actors end up in the same location relative to the receiver block
        for tele_block, actor in senders:
            xy_offs = util.add(xy_offs, util.sub(actor.get_xy(raw=True), tele_block.get_xy()))
        xy_offs = util.mult(xy_offs, 1 / len(senders))

        final_positions = []
        for tele_block in receivers:
            final_positions.append(util.add(tele_block.get_xy(), xy_offs))

        # it shouldn't matter which one we copy, but just to be safe we do it deterministically
        proto_actor = min(actors_to_send, key=lambda a: a.get_ent_id())
        other_actors = [a for a in actors_to_send if a is not proto_actor]

        new_actors = proto_actor.copy_for_teleport(final_positions, and_combine_with=other_actors)
        for a in actors_to_send:
            a.prepare_for_teleport()
            self.get_world().remove_entity(a)
        for a in new_actors:
            self.get_world().add_entity(a)

        for t in linked_teles + bro_teles + [self]:
            # XXX Using a mixture of two-way and non two-way teleporters can create a bizarre (but not necessarily
            # incorrect) situation after teleporting, might consider disallowing this. Hmm.
            if t.get_mode() == TeleporterBlock.TWO_WAY:
                t.set_sending(not t.is_sending())
            t.reset_prog()
            t._post_tele_countdown = t._post_tele_max_cooldown

        print("INFO: teleported {} to {}.".format(actors_to_send, new_actors))

    def get_sprite_infos(self):

        def get_sprite_and_color(idx):
            if self._sending:
                spr = spriteref.object_sheet().get_teleporter_sprites(self.get_prog(for_anim=True) / 2)[idx]
            else:
                if self.is_two_way():
                    anim_prog = min([t.get_prog() for t in self.all_linked_teleporters()], default=0)
                else:
                    anim_prog = 0
                spr = spriteref.object_sheet().get_teleporter_sprites(0.5 + anim_prog / 2)[idx]

            if idx == 0:
                return (spr, None)
            else:
                ticks = (self._pulse_ticks - (idx - 1) * self._pulse_offset) % self._pulse_interval
                color = self._pulse_colors[-1][0]
                for color_and_duration in self._pulse_colors:
                    if ticks <= color_and_duration[1]:
                        color = color_and_duration[0]
                        break
                    else:
                        ticks -= color_and_duration[1]
                return (spr, color)

        return [CompositeBlockEntity.BlockSpriteInfo(
            model_provider=lambda idx=i: get_sprite_and_color(idx)[0],
            color_provider=lambda idx=i: get_sprite_and_color(idx)[1],
            xy_offs=(0, 0)) for i in range(4)
        ]


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

    @staticmethod
    def build_colliders_for_points(pts):
        colliders = []

        rect = util.get_rect_containing_points(pts)
        if rect[2] <= rect[3]:
            colliders.append(TriangleCollider(pts, CollisionMasks.SLOPE_BLOCK_VERT, color=colors.PERFECT_YELLOW))
        else:
            colliders.append(TriangleCollider(pts, CollisionMasks.SLOPE_BLOCK_HORZ, color=colors.PERFECT_YELLOW))

        # add some block colliders to make the non-slope parts of the triangle act like regular walls
        for i in range(0, len(pts)):
            p1 = pts[i]
            p2 = pts[(i + 1) % len(pts)]
            # TODO shorten the collider a little bit if it's near an acute angle
            if p1[0] == p2[0]:
                y = min(p1[1], p2[1])
                h = abs(p1[1] - p2[1])
                x = p1[0] if p1[0] < rect[2] else p1[0] - 1

                colliders.append(RectangleCollider([x, y, 1, h], CollisionMasks.BLOCK, color=colors.PERFECT_BLUE))
            elif p1[1] == p2[1]:
                x = min(p1[0], p2[0])
                w = abs(p1[0] - p2[0])
                y = p1[1] if p1[1] < rect[3] else p1[1] - 1
                colliders.append(RectangleCollider([x, y, w, 1], CollisionMasks.BLOCK, color=colors.PERFECT_BLUE))

        return colliders

    def __init__(self, triangle):
        rect = util.get_rect_containing_points(triangle)
        super().__init__(rect[0], rect[1], w=rect[2], h=rect[3])

        self._points = [util.sub(pt, (rect[0], rect[1])) for pt in triangle]

        self.set_colliders(SlopeBlockEntity.build_colliders_for_points(self._points))

    def get_points(self, origin=None):
        if origin is None:
            origin = self.get_xy(raw=False)
        res = []
        for pt in self._points:
            pt_x = origin[0] + pt[0]
            pt_y = origin[1] + pt[1]
            res.append((pt_x, pt_y))
        return res

    def _update_main_body_debug_sprites(self, main_body_key):
        if main_body_key not in self._debug_sprites:
            self._debug_sprites[main_body_key] = sprites.TriangleSprite(spriteref.POLYGON_LAYER)
        pts = self.get_points()
        spr = self._debug_sprites[main_body_key]
        self._debug_sprites[main_body_key] = spr.update(new_points=pts, new_color=self.get_debug_color(), new_depth=30)


class PlayerInputs:

    # 2 = pressed, 1 = held, 0 = neutral
    def __init__(self, jump=0, left=0, down=0, right=0, act=0):
        self.jump = jump
        self.left = left
        self.down = down
        self.right = right
        self.act = act

    def __repr__(self):
        "[{}{}{}{}{}]".format(
            "W" if self.jump == 2 else ("w" if self.jump == 1 else "_"),
            "A" if self.left == 2 else ("a" if self.left == 1 else "_"),
            "S" if self.down == 2 else ("s" if self.down == 1 else "_"),
            "D" if self.right == 2 else ("d" if self.right == 1 else "_"),
            "J" if self.act == 2 else ("j" if self.act == 1 else "_"),
        )

    def is_jump_held(self):
        return self.jump > 0

    def was_jump_pressed(self):
        return self.jump == 2

    def is_left_held(self):
        return self.left > 0

    def is_down_held(self):
        return self.down > 0

    def is_right_held(self):
        return self.right > 0

    def is_act_held(self):
        return self.act > 0

    def was_act_pressed(self):
        return self.act == 2

    def to_ints(self):
        return (self.jump, self.left, self.down, self.right, self.act)

    @staticmethod
    def from_ints(ints):
        return PlayerInputs(jump=ints[0], left=ints[1], down=ints[2], right=ints[3], act=ints[4])

    def __eq__(self, other):
        if not isinstance(other, PlayerInputs):
            return False
        else:
            return self.to_ints() == other.to_ints()

    def __hash__(self):
        return hash(self.to_ints())


class PlayerController:

    EMPTY_INPUT = PlayerInputs()

    def get_inputs(self, tick) -> PlayerInputs:
        keys = keybinds.get_instance()
        keys_we_care_about = [keys.get_keys(const.JUMP),
                              keys.get_keys(const.MOVE_LEFT),
                              keys.get_keys(const.CROUCH),
                              keys.get_keys(const.MOVE_RIGHT),
                              keys.get_keys(const.ACTION_1)]
        ints = []
        for k in keys_we_care_about:
            if inputs.get_instance().was_pressed(k):
                val = 2
            elif inputs.get_instance().is_held(k):
                val = 1
            else:
                val = 0
            ints.append(val)

        return PlayerInputs.from_ints(ints)

    def get_recording(self):
        return None

    def is_active(self):
        return True


class RecordingPlayerController(PlayerController):

    HARD_LIMIT = 216000  # = 60 * 60 * 60 (an hour of gameplay)

    def __init__(self):
        self._pool = {}
        self._recorded_inputs = []

        self._did_print_warning = False

    def store(self, tick, player_inputs):
        # conserve objects
        if player_inputs == PlayerController.EMPTY_INPUT:
            player_inputs = PlayerController.EMPTY_INPUT
        elif player_inputs in self._pool:
            player_inputs = self._pool[player_inputs]
        else:
            self._pool[player_inputs] = player_inputs

        if 0 <= tick <= RecordingPlayerController.HARD_LIMIT:
            if len(self._recorded_inputs) == tick:
                self._recorded_inputs.append(player_inputs)
            elif len(self._recorded_inputs) > tick:
                self._recorded_inputs[tick] = player_inputs
            else:
                util.extend_or_empty_list_to_length(self._recorded_inputs, tick,
                                                    creator=lambda: PlayerController.EMPTY_INPUT)
                self._recorded_inputs.append(player_inputs)
        else:
            if not self._did_print_warning:
                print("ERROR: number of player actions is over the limit: {}".format(tick))
                self._did_print_warning = True

    def is_full(self):
        return len(self._recorded_inputs) >= RecordingPlayerController.HARD_LIMIT

    def __len__(self):
        return len(self._recorded_inputs)

    def get_inputs(self, tick) -> PlayerInputs:
        res = super().get_inputs(tick)
        self.store(tick, res)
        return res

    def get_recording(self) -> 'PlaybackPlayerController':
        recording = list(self._recorded_inputs)
        return PlaybackPlayerController(recording)


class PlaybackPlayerController(PlayerController):

    def __init__(self, input_list):
        self._input_list = input_list

    def __len__(self):
        return len(self._input_list)

    def get_inputs(self, tick):
        if 0 <= tick < len(self._input_list):
            return self._input_list[tick]
        else:
            return PlayerController.EMPTY_INPUT

    def is_finished(self, tick):
        return tick >= len(self._input_list)

    def is_active(self):
        return False


def choose_best_frames_of_reference(entity, candidate_list, sensor, max_n=1):
    """
    :param entity:
    :param candidate_list:
    :param sensor:
    :param max_n:
    :return: tuple (list of best FORs, map: Entity -> int overlap amount)
    """

    if len(candidate_list) == 0:
        return [], {}
    elif len(candidate_list) == 1:
        return candidate_list, {candidate_list[0]: 1}
    else:
        candidate_list = list(candidate_list)
        candidate_list.sort(key=lambda b: b.get_rect())  # for consistency

        overlaps = {}

        # figure out which ones we're on most
        xy = entity.get_xy(raw=False)
        collider_rect = sensor.get_rect(xy)
        for block in candidate_list:
            for block_collider in block.all_colliders():
                block_collider_rect = block_collider.get_rect(block.get_xy(raw=False))
                overlap_rect = util.get_rect_intersect(collider_rect, block_collider_rect)
                if overlap_rect is None:
                    overlaps[block] = -1
                else:
                    overlaps[block] = overlap_rect[2] * overlap_rect[3]

        candidate_list = [c for c in candidate_list if overlaps[c] > 0]
        candidate_list.sort(reverse=True, key=lambda b: overlaps[b])
        if max_n < len(candidate_list):
            return candidate_list[:max_n], overlaps
        else:
            return candidate_list, overlaps


class PlayerEntity(DynamicEntity, HasLightSourcesEntity):

    LIGHT_RADIUS = 8 * gs.get_instance().cell_size

    def __init__(self, x, y, player_type: playertypes.PlayerType, controller=None, align_to_cells=True):
        cs = gs.get_instance().cell_size
        w = int(cs * player_type.get_size()[0])
        h = int(cs * player_type.get_size()[1])

        super().__init__(0, 0, w=w, h=h)

        self._player_type = player_type
        self._controller = controller if controller is not None else PlayerController()

        self._sprites = {}  # id -> Sprite
        self._dir_facing = 1
        self._anim_frame_offset = 0

        self._y_vel_max = 20 * cs / configs.target_fps
        self._x_vel_max = player_type.get_move_speed() * cs / configs.target_fps
        self._x_vel_max_crouching = self._x_vel_max / 2

        self._wall_cling_y_vel_max = 4 * cs / configs.target_fps

        jump_info = player_type.get_jump_info()

        self._gravity = -cs * jump_info.g
        self._jump_y_vel = -cs * jump_info.vel
        self._fly_y_vel = -cs * jump_info.vel * 0.666  # TODO this value is kinda arbitrary

        self._snap_down_dist = 4

        self._bonus_y_fric_on_let_go = 0.85

        self._wall_jump_x_vel = 1.5
        self._wall_jump_y_vel = self._jump_y_vel

        self._ground_accel = 0.65
        self._ground_reverse_dir_bonus_accel = 0.3

        self._air_accel = 0.15

        self._air_x_friction = 0.85
        self._ground_x_friction = 0.60

        self._wall_cling_release_threshold = 14  # how long you have to hold the direction to break the wall cling
        self._wall_cling_release_time = 0

        self._air_time = 0          # how long it's been since player was grounded
        self._wall_cling_time = 0   # how long you've been sliding

        self._last_jump_time = 1000          # time since last jump
        self._last_jump_request_time = 1000  # time since jump key was pressed last

        self._pre_jump_buffer = 5   # how early you can press jump and still have it fire
        self._post_jump_buffer = 5  # if you press jump within X ticks of walking off a platform, you still jump

        self._jump_cooldown = 15

        self._holding_crouch = False
        self._holding_left = False
        self._holding_right = False

        self._has_ever_moved = False
        self._was_breaking_last_frame = False

        self._death_reason = None  # if this gets set, the player will die and be removed at the end of that update cycle

        w_inset = int(self.get_w() * 0.2)  # 0.15

        h_inset_upper = int(self.get_h() * 0.15)
        h_inset_lower = max(4, int(self.get_h() * 0.15))  # 0.1

        vert_env_collider = RectangleCollider([w_inset, 0, self.get_w() - (w_inset * 2), self.get_h()],
                                              CollisionMasks.ACTOR,
                                              collides_with=CollisionMasks.BLOCK,
                                              resolution_hint=CollisionResolutionHints.VERT_ONLY,
                                              color=colors.PERFECT_WHITE,
                                              name="main_vert_rect_collider")

        horz_env_collider = RectangleCollider([0, 0, self.get_w(), self.get_h() - h_inset_lower],
                                              CollisionMasks.ACTOR,
                                              collides_with=CollisionMasks.BLOCK,
                                              resolution_hint=CollisionResolutionHints.HORZ_ONLY,
                                              color=colors.PERFECT_WHITE,
                                              name="main_horz_rect_collider")

        foot_sensor_rect = [w_inset, self.get_h(), self.get_w() - w_inset * 2, 1]
        self.foot_sensor = RectangleCollider(foot_sensor_rect,
                                             CollisionMasks.SENSOR,
                                             collides_with=CollisionMasks.BLOCK,
                                             color=colors.PERFECT_GREEN,
                                             name="foot_rect_sensor")

        wall_sensor_y = self.get_h() // 4
        wall_sensor_h = int(self.get_h() * 3 / 4) - h_inset_lower
        self.left_sensor = RectangleCollider([-1, wall_sensor_y, 1, wall_sensor_h],
                                             CollisionMasks.SENSOR,
                                             collides_with=CollisionMasks.BLOCK,
                                             color=colors.PERFECT_GREEN,
                                             name="left_rect_sensor")

        self.right_sensor = RectangleCollider([self.get_w(), wall_sensor_y, 1, wall_sensor_h],
                                              CollisionMasks.SENSOR,
                                              collides_with=CollisionMasks.BLOCK,
                                              color=colors.PERFECT_GREEN,
                                              name="right_rect_sensor")

        self.foot_sensor_id = self.foot_sensor.get_id()
        self.left_sensor_id = self.left_sensor.get_id()
        self.right_sensor_id = self.right_sensor.get_id()

        # pulls you to the ground when you're grounded
        snap_down_rect = [w_inset, self.get_h(), self.get_w() - w_inset * 2, self._snap_down_dist]
        self.snap_down_sensor = RectangleCollider(snap_down_rect,
                                                  CollisionMasks.SNAP_DOWN_SENSOR,
                                                  collides_with=(CollisionMasks.SLOPE_BLOCK_HORZ, CollisionMasks.BLOCK),
                                                  color=colors.PERFECT_LIGHT_GRAY,
                                                  name="snap_down_rect_and_slope_sensor")

        w_inset_slope = int(self.get_w() * 0.2)
        h_inset_slope_top = int(self.get_h() * 0.1)
        h_inset_slope_bot = int(self.get_h() * 0.1)

        # slope colliders
        slope_collider_main_horz_rect = [0, h_inset_slope_top,
                                         self.get_w(),
                                         self.get_h() - h_inset_slope_top - h_inset_slope_bot]
        slope_collider_main_horz = RectangleCollider(slope_collider_main_horz_rect,
                                                     CollisionMasks.ACTOR,
                                                     collides_with=(CollisionMasks.SLOPE_BLOCK_VERT),
                                                     resolution_hint=CollisionResolutionHints.HORZ_ONLY,
                                                     color=colors.WHITE,
                                                     name="main_horz_slope_collider")

        slope_collider_main_top_rect = [w_inset_slope, 0,
                                        self.get_w() - (2 * w_inset_slope),
                                        self.get_h() - h_inset_slope_bot]
        slope_collider_main_top = RectangleCollider(slope_collider_main_top_rect,
                                                    CollisionMasks.ACTOR,
                                                    collides_with=(CollisionMasks.SLOPE_BLOCK_HORZ),
                                                    resolution_hint=CollisionResolutionHints.VERT_ONLY,
                                                    color=colors.WHITE,
                                                    name="main_vert_top_slope_collider")

        foot_slope_collider_triangle = [(w_inset_slope, self.get_h() - h_inset_slope_bot),
                                        (self.get_w() // 2, self.get_h()),
                                        (self.get_w() - w_inset_slope, self.get_h() - h_inset_slope_bot)]

        foot_slope_env_collider = TriangleCollider(foot_slope_collider_triangle,
                                                   CollisionMasks.ACTOR,
                                                   collides_with=CollisionMasks.SLOPE_BLOCK_HORZ,
                                                   resolution_hint=CollisionResolutionHints.VERT_ONLY,
                                                   color=colors.WHITE,
                                                   name="main_bottom_vert_slope_collider")

        foot_slope_sensor = TriangleCollider([(p[0], p[1] + 1) for p in foot_slope_collider_triangle],
                                             CollisionMasks.SENSOR,
                                             collides_with=CollisionMasks.SLOPE_BLOCK_HORZ,
                                             color=colors.PERFECT_GREEN,
                                             name="bottom_slope_sensor")

        self.foot_slope_sensor_id = foot_slope_sensor.get_id()

        # this is just so that breakable things can sense us
        self.breaking_collider = RectangleCollider([0, 0, w, h], CollisionMasks.BREAKING, collides_with=None)
        self.breaking_collider.set_enabled(False)

        self.set_colliders([vert_env_collider, horz_env_collider,
                            self.foot_sensor, self.left_sensor, self.right_sensor,  self.snap_down_sensor,
                            slope_collider_main_horz, slope_collider_main_top,
                            foot_slope_env_collider, foot_slope_sensor,
                            self.breaking_collider])

        if align_to_cells:
            cell_w = math.ceil(w / cs)
            cell_h = math.ceil(h / cs)

            aligned_x = int(x + (cs * cell_w - w) / 2)  # center the player across the cells it overlaps
            aligned_y = int(y - (cs * (cell_h - 1)) + (cs * cell_h - h))  # ground the player in the y-cell
            self.set_xy((aligned_x, aligned_y))
        else:
            self.set_xy((x, y))

        self._adjust_colliders_for_breaking(self._was_breaking_last_frame)

    def get_player_type(self):
        return self._player_type

    def get_controller(self):
        return self._controller

    def has_inputs_at_tick(self, world_tick):
        return self.get_controller().get_inputs(world_tick) != RecordingPlayerController.EMPTY_INPUT

    def is_active(self):
        return self._controller.is_active()

    def is_breaking(self):
        return self.get_player_type().can_break_blocks() and not self.is_grounded()

    def is_swappable(self):
        return self.get_player_type().can_be_swapped_with()

    def _adjust_colliders_for_breaking(self, breaking):
        self.breaking_collider.set_enabled(breaking)
        for c in self.all_colliders():
            if c.collides_with_masks((CollisionMasks.BLOCK,)):
                new_collides_with = [m for m in c.get_collides_with() if m != CollisionMasks.BREAKABLE]
                if not breaking:
                    # if we're breaking, we want to move through breaking blocks, so we can break them
                    new_collides_with.append(CollisionMasks.BREAKABLE)
                c.set_collides_with(new_collides_with)

    def get_physics_group(self):
        return ACTOR_GROUP

    def update(self):
        super().update()
        self._handle_inputs()

        if self.is_grounded():
            if self._y_vel > 0:
                self._y_vel = 0
        else:
            self._y_vel += self._gravity

        max_y_vel = self._y_vel_max if not self.is_clinging_to_wall() else self._wall_cling_y_vel_max
        if self._y_vel > max_y_vel:
            self._y_vel = max_y_vel

        should_snap_down = self._last_jump_time > 3 and self._air_time <= 1 and self._y_vel >= 0
        self.snap_down_sensor.set_enabled(should_snap_down)

        self._last_jump_time += 1

        if self.get_x_vel() < -0.1:
            self._dir_facing = -1
        elif self.get_x_vel() > 0.1:
            self._dir_facing = 1

        parent_entity = self
        held_entity = self.get_held_entity()
        while held_entity is not None:
            pos = parent_entity.get_held_entity_position(held_entity, raw=True)
            held_entity.set_xy(pos)
            held_entity.set_y_vel(parent_entity.get_y_vel())

            parent_entity = held_entity
            held_entity = parent_entity.get_held_entity()

        currently_breaking = self.is_breaking()
        if currently_breaking != self._was_breaking_last_frame:
            self._was_breaking_last_frame = currently_breaking
            self._adjust_colliders_for_breaking(currently_breaking)

        self._handle_death_by_crowding()

    def is_grounded(self):
        return self.is_on_flat_ground() or self.is_on_sloped_ground()

    def is_left_walled(self):
        return len(self.get_world().get_sensor_state(self.left_sensor_id)) > 0

    def is_right_walled(self):
        return len(self.get_world().get_sensor_state(self.right_sensor_id)) > 0

    def is_on_sloped_ground(self):
        return len(self.get_world().get_sensor_state(self.foot_slope_sensor_id)) > 0

    def is_on_flat_ground(self):
        return len(self.get_world().get_sensor_state(self.foot_sensor_id)) > 0

    def is_clinging_to_wall(self):
        if self.get_player_type().can_walljump():
            return not self.is_grounded() and (self.is_left_walled() or self.is_right_walled())
        else:
            return False

    def is_moving(self):
        return abs(self.get_x_vel()) > 0.1

    def is_holding_left_or_right(self):
        return self._holding_left or self._holding_right

    def is_crouching(self):
        # TODO crouch jumps? forced to crouch?
        return self.is_grounded() and self._holding_crouch

    def has_ever_moved(self):
        return self._has_ever_moved

    def dir_facing(self):
        if self.is_clinging_to_wall():
            if self.is_left_walled() and self.is_right_walled():
                return -self._dir_facing  # i promise this makes sense TODO does it?
            else:
                return 1 if self.is_left_walled() else -1
        else:
            return self._dir_facing

    def get_pickup_range(self):
        return self.get_rect(raw=False)

    def get_held_entity_position(self, entity, raw=True):
        self.update_sprites()  # XXX hack

        body_spr: sprites.ImageSprite = self.get_body_sprite()
        if body_spr is None:
            return super().get_held_entity_position(entity, raw=raw)
        else:
            carrying_rect = spriteref.object_sheet().get_carrying_position(body_spr.model())
            if body_spr.xflip():
                carrying_rect = [body_spr.model().w - (carrying_rect[0] + carrying_rect[2]),
                                 carrying_rect[1],
                                 carrying_rect[2], carrying_rect[3]]

            cx = self.get_center(raw=raw, with_xy_perturbs=False)[0]
            y_bot = self.get_y(raw=raw, with_xy_perturbs=False) + self.get_h()

            x = cx - body_spr.width() // 2 + (carrying_rect[0] + carrying_rect[2] // 2) * body_spr.scale() - entity.get_w() // 2
            y = y_bot - body_spr.height() + (carrying_rect[1] + carrying_rect[3]) * body_spr.scale() - entity.get_h()
            return (x, y)

    def _handle_inputs(self):
        if self.get_world().get_game_state() is not None and self.get_world().get_game_state().get_status().can_player_control:
            cur_inputs = self.get_controller().get_inputs(self.get_world().get_tick())
        else:
            cur_inputs = self.get_controller().EMPTY_INPUT

        request_left = cur_inputs.is_left_held()
        request_right = cur_inputs.is_right_held()
        request_jump = cur_inputs.was_jump_pressed()
        request_action = cur_inputs.was_act_pressed()
        holding_jump = cur_inputs.is_jump_held()
        holding_crouch = cur_inputs.is_down_held()

        if not self._has_ever_moved:
            self._has_ever_moved = cur_inputs != PlayerController.EMPTY_INPUT

        self._holding_left = request_left
        self._holding_right = request_right
        self._holding_crouch = self.get_player_type().can_crouch() and holding_crouch

        if request_jump:
            self._last_jump_request_time = 0
        else:
            self._last_jump_request_time += 1

        if request_action:
            self._try_to_alert()
            if self.get_player_type().can_grab():
                self._try_to_grab_or_drop()
            if self.get_player_type().can_swap():
                self._try_to_swap()

        if self.is_grounded():
            self._air_time = 0
        else:
            self._air_time += 1

        if self.is_clinging_to_wall():
            self._wall_cling_time += 1
        else:
            self._wall_cling_time = 0

        dx = 0
        if request_left:
            dx -= 1
        if request_right:
            dx += 1

        if self.is_clinging_to_wall():
            if (dx == 1 and self.is_left_walled()) or (dx == -1 and self.is_right_walled()):
                if self._wall_cling_release_time < self._wall_cling_release_threshold:
                    dx = 0
                self._wall_cling_release_time += 1
            else:
                dx = 0
                self._wall_cling_release_time = 0
        else:
            self._wall_cling_release_time = 0

        if dx != 0:
            accel = 0
            if self.is_grounded():
                if self._x_vel <= 0 < dx or dx < 0 <= self._x_vel:
                    accel += self._ground_reverse_dir_bonus_accel
                accel += self._ground_accel
            else:
                # XXX this boost here is actually a very delicate solution to a subtle bug. If the player is airborne
                # and holding left or right, and lands perfectly on the corner of a block, they can get stuck
                # (until they release the key) as their horizontal and vertical velocities repeatedly loop
                # from 0.15 -> 0.3 -> 0.6 -> 0.15 -> and so on. Without the 2x multiplier, the x and y velocity loops
                # have the same period and thus the collision resolver always resolves the horizontal and vertical
                # collisions on the same frame (resetting both vels to 0) and shifting the player back to the spot.
                # This "fix" makes the x_vel increase slightly faster to prevent the loop from occurring.
                # (A keen observer may notice that the player can still get "stuck" in this way for a couple frames
                # if they land exactly on a corner. I think it's almost beneficial though because it lets the player
                # know that they made the jump by exactly one pixel. Like a phantom hit).
                accel += self._air_accel if abs(self.get_x_vel()) >= 1 else self._air_accel * 2

            x_accel = dx * accel

            # reduce x speed if we're on a slope
            if self.is_on_sloped_ground() and not self.is_on_flat_ground():
                x_accel *= math.cos(util.to_rads(22.5))

            x_vel_max = self._x_vel_max if not self.is_crouching() else self._x_vel_max_crouching
            new_x_vel_bounded = util.bound(self._x_vel + x_accel, -x_vel_max, x_vel_max)

            self.set_x_vel(new_x_vel_bounded)
        else:
            fric = self._ground_x_friction if self.is_grounded() else self._air_x_friction
            self.set_x_vel(self._x_vel * fric)

        try_to_jump = (self._last_jump_request_time <= self._pre_jump_buffer and
                       holding_jump and
                       self._last_jump_time >= self._jump_cooldown)

        if try_to_jump:
            if self.is_grounded() or self.is_held():
                self.break_free_from_parent()
                self.set_y_vel(self._jump_y_vel)
                self._last_jump_time = 0

            elif self.is_clinging_to_wall():
                self.set_y_vel(self._wall_jump_y_vel)
                self._last_jump_time = 0
                # TODO add some way to cancel the x_vel on a wall jump?
                if self.is_left_walled():
                    self.set_x_vel(self._wall_jump_x_vel)
                if self.is_right_walled():
                    self.set_x_vel(-self._wall_jump_x_vel)

            elif self.get_player_type().can_fly():
                if self._fly_y_vel < self.get_y_vel():
                    self.set_y_vel(self._fly_y_vel)
                    self._last_jump_time = 0

            elif self._air_time < self._post_jump_buffer:
                # if you jumped too late, you get a penalty
                jump_penalty = (1 - 0.5 * self._air_time / self._post_jump_buffer)
                self.set_y_vel(self._jump_y_vel * jump_penalty)
                self._last_jump_time = 0

        # short hopping
        if self._y_vel < 0 and not holding_jump:
            self._y_vel *= self._bonus_y_fric_on_let_go

        # TODO just for testing
        import pygame
        player_id = self.get_player_type().get_id()
        if inputs.get_instance().was_pressed(pygame.K_k) and spriteref.object_sheet().num_broken_player_parts(player_id) > 0:
            part_idx = random.randint(0, spriteref.object_sheet().num_broken_player_parts(player_id) - 1)
            new_particle = PlayerBodyPartParticle(self.get_x(), self.get_y(), self.get_player_type().get_id(), part_idx)
            self.get_world().add_entity(new_particle)

    def _try_to_grab_or_drop(self):
        if self.get_held_entity() is not None:
            self.pickup_entity(None)  # dropping held item
            # TODO dropping sound / animation
        else:
            can_be_picked_up = []
            for e in self.get_world().all_entities_in_rect(self.get_pickup_range(),
                                                           cond=lambda x: x.can_be_picked_up()):
                if e is not self:
                    can_be_picked_up.append(e)

            if len(can_be_picked_up) > 0:
                # prioritize stuff that's closer and not already held
                my_center = self.get_center()
                can_be_picked_up.sort(
                    key=lambda x: util.dist(my_center, x.get_center()) + 100 if x.is_held() else 0)

                to_pick_up = can_be_picked_up[0]
                self.pickup_entity(to_pick_up)

    def _try_to_swap(self, target: Entity=None):
        # TODO not used, delete?
        if target is None:
            other_actors_in_level = list(self.get_world().all_entities(
                cond=lambda e: e.is_swappable() and e is not self and not e.is_held()))

            if len(other_actors_in_level) > 0:
                my_center = self.get_center()
                other_actors_in_level.sort(key=lambda e: util.dist(my_center, e.get_center()))
                target = other_actors_in_level[0]

        if target is not None:
            # TODO *poof* animations and sound
            my_bottom_center = (self.get_center()[0], self.get_y() + self.get_h())
            target_bottom_center = (target.get_center()[0], target.get_y() + target.get_h())

            my_new_xy = (target_bottom_center[0] - self.get_w() // 2, target_bottom_center[1] - self.get_h())
            self.set_xy(my_new_xy)

            other_new_xy = (my_bottom_center[0] - target.get_w() // 2, my_bottom_center[1] - target.get_h())
            target.set_xy(other_new_xy)

    def _try_to_alert(self):
        color_id = self.get_player_type().get_color_id()
        color = spriteref.get_color(color_id)
        # TODO play alert sound

        top_center_xy = (self.get_x() + self.get_w() // 2, self.get_y() - 2)
        alert_entity = FloatingTextAlertEntity(top_center_xy, "!", color, colors.darken(color, 0.4),
                                               depth=WORLD_UI_DEPTH, fadeout_time=15, fadeout_dir=(0, -4))
        self.get_world().add_entity(alert_entity)

    def copy_for_teleport(self, positions, and_combine_with=()):
        res = []
        all_players_to_avg = [self] + list(and_combine_with)
        avg_vel = util.average([p.get_vel() for p in all_players_to_avg])
        avg_dir = -1 if sum([p.dir_facing() for p in all_players_to_avg]) < 0 else 1
        for xy in positions:
            new_player = PlayerEntity(xy[0], xy[1], self.get_player_type(),
                                      controller=self.get_controller(),
                                      align_to_cells=False)
            new_player.set_vel(avg_vel)
            new_player._dir_facing = avg_dir
            res.append(new_player)
        return res

    def prepare_for_teleport(self):
        if self.is_holding_an_entity():
            self._try_to_grab_or_drop()

    def _handle_death_by_crowding(self):
        """
        When you have two copies of the same player type directly on top of each other, it bricks the level
        in a potentially confusing way (since there's no way to separate them). So we just kill both players.
        """
        for p in self.get_world().all_players(must_be_active=False,
                                              with_type=self.get_player_type(),
                                              in_rect=self.get_rect(with_xy_perturbs=False)):
            if p is not self and p.get_rect(with_xy_perturbs=False) == self.get_rect(with_xy_perturbs=False):
                if util.mag(util.sub(p.get_vel(), self.get_vel())) <= 0.001:
                    self.set_death_reason(DeathReason.CROWDING)
                    p.set_death_reason(DeathReason.CROWDING)

    def update_frame_of_reference_parents(self):
        # TODO should we care about slope blocks? maybe? otherwise you could get scooped up by a moving platform
        # TODO touching your toe as you're (mostly) standing on a slop
        blocks_upon = self.get_world().get_sensor_state(self.foot_sensor_id)
        best_upon, _ = choose_best_frames_of_reference(self, blocks_upon, self.foot_sensor, max_n=1)
        if len(best_upon) > 0:
            self.set_frame_of_reference_parents(best_upon)
        else:
            blocks_on_left = self.get_world().get_sensor_state(self.left_sensor_id)
            blocks_on_right = self.get_world().get_sensor_state(self.right_sensor_id)

            best_on_left, left_overlaps = choose_best_frames_of_reference(self, blocks_on_left, self.left_sensor, max_n=1)
            best_on_right, right_overlaps = choose_best_frames_of_reference(self, blocks_on_right, self.right_sensor, max_n=1)

            if len(best_on_left) > 0 and len(best_on_right) > 0:
                if left_overlaps[best_on_left[0]] <= right_overlaps[best_on_right[0]]:
                    self.set_frame_of_reference_parents(best_on_left[0], vert=False)
                else:
                    self.set_frame_of_reference_parents(best_on_right[0], vert=False)
            elif len(best_on_left) > 0:
                self.set_frame_of_reference_parents(best_on_left[0], vert=False)
            elif len(best_on_right) > 0:
                self.set_frame_of_reference_parents(best_on_right[0], vert=False)
            else:
                self.set_frame_of_reference_parents([])

    def get_debug_color(self):
        return colors.PERFECT_BLUE

    def get_light_sources(self):
        return [(self.get_center(), PlayerEntity.LIGHT_RADIUS, colors.PERFECT_WHITE, 1.0)]

    def get_player_state(self):
        if (self.is_grounded() or self.is_held()) and (self._last_jump_time <= 1 or self.get_y_vel() > -0.1):
            if self.is_moving() or self.is_holding_left_or_right():
                if not self.is_crouching():
                    res = spriteref.PlayerStates.WALKING
                else:
                    res = spriteref.PlayerStates.CROUCH_WALKING
            else:
                if not self.is_crouching():
                    res = spriteref.PlayerStates.IDLE
                else:
                    res = spriteref.PlayerStates.CROUCH_IDLE

        elif (not self.is_left_walled() and not self.is_right_walled()) or not self.get_player_type().can_walljump():
            res = spriteref.PlayerStates.AIRBORNE
        else:
            res = spriteref.PlayerStates.WALLSLIDE

        if self.is_holding_an_entity():
            res = res.as_carrying()

        return res

    def _get_current_img(self):
        state = self.get_player_state()
        anim_rate = self.get_player_type().get_anim_rate(state, self)

        return self._player_type.get_player_img(state, frame=gs.get_instance().anim_tick() // anim_rate)

    def update_sprites(self):
        body_id = "body"
        cur_img = self._get_current_img()
        if cur_img is not None:
            if body_id not in self._sprites or self._sprites[body_id] is None:
                self._sprites[body_id] = sprites.ImageSprite.new_sprite(spriteref.ENTITY_LAYER)
        else:
            self._sprites[body_id] = None

        body_spr = self._sprites[body_id]
        if body_spr is not None:
            rect = self.get_rect()

            if not self.is_clinging_to_wall():
                spr_x = rect[0] + rect[2] // 2 - cur_img.width() // 2
            elif self.dir_facing() < 0:
                spr_x = rect[0] + rect[2] - cur_img.width()  # anchor right
            else:
                spr_x = rect[0]  # anchor left

            spr_y = rect[1] + rect[3] - cur_img.height()

            can_xflip = self.get_player_type().should_ever_xflip()

            self._sprites[body_id] = body_spr.update(new_model=cur_img,
                                                     new_x=spr_x,
                                                     new_y=spr_y,
                                                     new_depth=PLAYER_DEPTH,
                                                     new_xflip=can_xflip and self.dir_facing() < 0,
                                                     # new_yflip=self.is_held(),  # TODO not sure if I like this
                                                     new_color=self.get_color())

    def all_sprites(self):
        for spr_id in self._sprites:
            if self._sprites[spr_id] is not None:
                yield self._sprites[spr_id]

    def get_body_sprite(self):
        if "body" in self._sprites:
            return self._sprites["body"]
        else:
            return None

    def was_crushed(self):
        self.set_death_reason(DeathReason.CRUSHED)

    def fell_out_of_bounds(self):
        self.set_death_reason(DeathReason.OUT_OF_BOUNDS)

    def set_death_reason(self, reason):
        self._death_reason = reason

    def handle_death_if_necessary(self, silent=False):
        if self._death_reason is not None:
            player_id = self.get_player_type().get_id()
            if not silent:
                cx, cy = self.get_center()
                for i in range(0, spriteref.object_sheet().num_broken_player_parts(player_id)):
                    self.get_world().add_entity(PlayerBodyPartParticle(cx, cy, player_id, i))
            self.get_world().remove_entity(self)
            # TODO tell gs or someone we died?
            print("INFO: player {} {}.".format(player_id, self._death_reason))
            return True
        else:
            return False

    def spawn_fadeout_animation(self, duration):
        anim = PlayerFadeAnimation(self.get_center()[0], self.get_y() + self.get_h(),
                                   self.dir_facing() > 0, self.get_player_type(), duration, True)
        self.get_world().add_entity(anim)

    def __repr__(self):
        return "{}({}, {})".format(type(self).__name__, self.get_player_type().get_id(), self.get_rect())


class DeathReason:
    CRUSHED = "was crushed"
    OUT_OF_BOUNDS = "fell out of bounds"
    SPIKED = "was spiked"
    CROWDING = "became one with itself"
    UNKNOWN = "was killed by the guardians"


class ParticleEntity(DynamicEntity):

    def __init__(self, x, y, w, h, vel, duration=-1, initial_phasing=-1, color=colors.PERFECT_WHITE):
        super().__init__(x, y, w, h)
        self._x_vel = vel[0]
        self._y_vel = vel[1]
        self._initial_phasing = initial_phasing
        self._duration = duration
        self._color = color
        self._ticks_alive = 0

        self._gravity = 0.15
        self._bounciness = 0.8
        self._friction = 0.97

        self.max_vel = 20 * gs.get_instance().cell_size / configs.target_fps

        self._x_flip = self._x_vel < 0

        self._img = None

        self._block_collider = RectangleCollider([0, 0, w, h], CollisionMasks.PARTICLE,
                                                 collides_with=(CollisionMasks.BLOCK,))
        self._block_collider.set_enabled(False)
        self._is_phasing = True

        # detects when the particle isn't overlapping blocks anymore
        body_sensor = RectangleCollider([0, 0, w, h], CollisionMasks.SENSOR, collides_with=(CollisionMasks.BLOCK,
                                                                                            CollisionMasks.SLOPE_BLOCK_HORZ,
                                                                                            CollisionMasks.SLOPE_BLOCK_VERT))
        self._body_sensor_id = body_sensor.get_id()

        foot_sensor = RectangleCollider([0, h, w, 1], CollisionMasks.SENSOR, collides_with=(CollisionMasks.BLOCK,
                                                                                            CollisionMasks.SLOPE_BLOCK_HORZ))
        self._foot_sensor_id = foot_sensor.get_id()

        left_sensor = RectangleCollider([-1, 0, 1, h-2], CollisionMasks.SENSOR, collides_with=(CollisionMasks.BLOCK,
                                                                                               CollisionMasks.SLOPE_BLOCK_VERT))
        self._left_sensor_id = left_sensor.get_id()

        right_sensor = RectangleCollider([w, 0, 1, h-2], CollisionMasks.SENSOR, collides_with=(CollisionMasks.BLOCK,
                                                                                               CollisionMasks.SLOPE_BLOCK_VERT))
        self._right_sensor_id = right_sensor.get_id()

        self.set_colliders([self._block_collider, body_sensor, foot_sensor, left_sensor, right_sensor])

    def get_sprite(self):
        return None

    def get_physics_group(self):
        return ACTOR_GROUP  # TODO add particle group?

    def is_grounded(self):
        return not self._is_phasing and len(self.get_world().get_sensor_state(self._foot_sensor_id)) > 0

    def is_left_walled(self):
        return not self._is_phasing and len(self.get_world().get_sensor_state(self._left_sensor_id)) > 0

    def is_right_walled(self):
        return not self._is_phasing and len(self.get_world().get_sensor_state(self._right_sensor_id)) > 0

    def was_crushed(self):
        # if it gets crushed again after leaving phasing mode, just bail to save the physics engine some work
        self.get_world().remove_entity(self)

    def update(self):
        super().update()
        if 0 <= self._duration <= self._ticks_alive:
            self.get_world().remove_entity(self)
            return
        self._ticks_alive += 1

        if self._is_phasing and 0 <= self._initial_phasing < self._ticks_alive:
            if len(self.get_world().get_sensor_state(self._body_sensor_id)) == 0:
                self._block_collider.set_enabled(True)
                self._is_phasing = False

        if self.is_grounded():
            if self._y_vel > 0.1:
                self._y_vel = -self._bounciness * self._y_vel
            else:
                self._y_vel = 0

            if abs(self._x_vel) < 0.1:
                self._x_vel = 0
            else:
                self._x_vel = self._friction * self._x_vel
        else:
            self._y_vel += self._gravity

        if self._x_vel < 0 and self.is_left_walled():
            self._x_vel = -self._bounciness * self._x_vel
        elif self._x_vel > 0 and self.is_right_walled():
            self._x_vel = -self._bounciness * self._x_vel

        self._x_vel = util.bound(self._x_vel, -self.max_vel, self.max_vel)
        self._y_vel = util.bound(self._y_vel, -self.max_vel, self.max_vel)

        if self._x_vel < -0.1:
            self._x_flip = True
        elif self._x_vel > 0.1:
            self._x_flip = False

    def get_color(self, ignore_override=False):
        if ignore_override or self.get_color_override() is None:
            return self._color
        else:
            return self.get_color_override()

    def update_sprites(self):
        model = self.get_sprite()
        if model is None and self._img is not None:
            self._img = None
        elif model is not None:
            if self._img is None:
                self._img = sprites.ImageSprite.new_sprite(spriteref.ENTITY_LAYER, depth=PARTICLE_DEPTH)
            rect = self.get_rect()
            new_x = rect[0] + rect[2] // 2 - model.width() // 2
            new_y = rect[1] + rect[3] - model.height()
            self._img = self._img.update(new_model=model,
                                         new_x=new_x,
                                         new_y=new_y,
                                         new_xflip=self._x_flip,
                                         new_color=self.get_color())

    def all_sprites(self):
        for spr in super().all_sprites():
            yield spr
        if self._img is not None:
            yield self._img


class RotatingParticleEntity(ParticleEntity):

    def __init__(self, x, y, rotated_sprites, duration=60 * 2, initial_vel=None, initial_phasing=20,
                 color=colors.PERFECT_WHITE):
        if initial_vel is None:
            initial_vel = (-0.75 + 1.5 * random.random(), -(1.5 + 1 * random.random()))

        cs = gs.get_instance().cell_size
        ParticleEntity.__init__(self, x, y, cs // 5, cs // 5, initial_vel,
                                duration=duration, initial_phasing=initial_phasing, color=color)

        self.rotation = random.random()
        self.rotation_vel = 0.05 + random.random() * 0.1
        self.rotation_decay = 0.985

        self.rotated_sprites = rotated_sprites

    def update(self):
        super().update()

        if self.rotation_vel < 0.01:
            self.rotation_vel = 0
        else:
            self.rotation -= self.rotation_vel
            self.rotation_vel *= self.rotation_decay

    def get_sprite(self):
        return util.index_into(self.rotated_sprites, self.rotation, wrap=True)


class PlayerBodyPartParticle(RotatingParticleEntity):

    def __init__(self, x, y, player_id, part_idx):
        initial_vel = (-0.75 + 1.5 * random.random(), -(1.5 + 1 * random.random()))
        super().__init__(x, y, [], duration=60 * 5, initial_vel=initial_vel)

        self.player_id = player_id
        self.part_idx = part_idx

    def get_sprite(self):
        return spriteref.object_sheet().get_broken_player_sprite(self.player_id, self.part_idx, rotation=self.rotation)


class PlayerFadeAnimation(HasLightSourcesEntity):

    def __init__(self, cx, y_bottom, facing_right, player_type, duration, fade_out):
        super().__init__(cx - 2, y_bottom - 4, 4, 4)
        self.facing_right = facing_right
        self.player_type = player_type
        self.duration = duration
        self.ticks_active = 0
        self.fade_out = fade_out

        self._sprite = None

    def get_player_type(self):
        return self.player_type

    def get_fade_pcnt(self):
        if self.fade_out:
            return self.ticks_active / self.duration
        else:
            return 1 - (self.ticks_active / self.duration)

    def get_player_center(self):
        size_in_cells = self.player_type.get_size()
        size = (int(size_in_cells[0] * gs.get_instance().cell_size),
                int(size_in_cells[1] * gs.get_instance().cell_size))
        bottom_center = (self.get_center()[0], self.get_y() + self.get_h())
        return (bottom_center[0], bottom_center[1] - size[1] // 2)

    def get_light_sources(self):
        strength = 1 - self.get_fade_pcnt()
        return [(self.get_player_center(), PlayerEntity.LIGHT_RADIUS, colors.PERFECT_WHITE, strength)]

    def update(self):
        super().update()
        if self.ticks_active >= self.duration:
            self.get_world().remove_entity(self)
        else:
            if self._sprite is None:
                self._sprite = sprites.ImageSprite.new_sprite(spriteref.ENTITY_LAYER, depth=PLAYER_DEPTH)
            fade_pcnt = self.ticks_active / self.duration
            model = spriteref.object_sheet().get_phasing_sprite(self.player_type.get_id(), fade_pcnt, self.fade_out, 0)
            x = self.get_center()[0] - model.width() // 2
            y = self.get_y() + self.get_h() - model.height()
            self._sprite = self._sprite.update(new_model=model, new_x=x, new_y=y, new_xflip=not self.facing_right)
        self.ticks_active += 1

    def all_sprites(self):
        if self._sprite is not None:
            yield self._sprite


class FloatingDustParticleEntity(Entity):

    def __init__(self, xy, particle_type, duration, vel, color,
                 scale=1,
                 depth=0,
                 layer=spriteref.ENTITY_LAYER,
                 end_color=None,
                 anim_rate=4,
                 fric=0.0,
                 accel=(0, 0.01),
                 max_speed=10,
                 max_sway_per_second=3.1415/8):
        super().__init__(xy[0], xy[1], 1, 1)
        self._scale = scale
        self._depth = depth
        self._layer = layer
        self._type = particle_type
        self._duration = duration
        self._ticks_active = 0
        self.set_vel(vel)
        self._accel = accel
        self._fric = fric
        self._max_speed = max_speed
        self._start_color = color
        self._end_color = end_color if end_color is not None else color
        self._anim_rate = anim_rate
        self._max_sway = max_sway_per_second

        self._sprite = None

    def calc_next_vel(self, cur_vel):
        sway_val_rads = 2 * (0.5 - random.random()) * self._max_sway / configs.target_fps
        vel_with_sway = util.rotate(cur_vel, sway_val_rads)

        new_vel = util.add(vel_with_sway, self._accel)
        if util.mag(new_vel) > self._max_speed:
            new_vel = util.set_length(new_vel, self._max_speed)
        new_vel = util.mult(new_vel, 1 - self._fric)

        return new_vel

    def get_prog(self):
        return util.bound(self._ticks_active / self._duration, 0, 1)

    def update_sprites(self):
        prog = self.get_prog()
        cur_color = util.linear_interp(self._start_color, self._end_color, prog)
        cur_anim_idx = gs.get_instance().anim_tick() // self._anim_rate
        cur_model = spriteref.object_sheet().get_particle_sprite(self._type, cur_anim_idx)
        cur_xy = self.get_xy()

        if self._sprite is None:
            self._sprite = sprites.ImageSprite.new_sprite(self._layer, scale=self._scale, depth=self._depth)

        self._sprite = self._sprite.update(new_model=cur_model,
                                           new_x=cur_xy[0] - cur_model.width() * self._scale // 2,
                                           new_y=cur_xy[1] - cur_model.height() * self._scale // 2,
                                           new_color=cur_color, new_scale=self._scale, new_depth=self._depth)

    def update(self):
        if self._ticks_active >= self._duration:
            self.get_world().remove_entity(self)
        else:
            self.set_vel(self.calc_next_vel(self.get_vel()))
            self.set_xy(self.calc_next_xy(raw=True))

        self.update_sprites()
        self._ticks_active += 1

    def all_sprites(self):
        yield self._sprite


class ParticleEmitterZone(DynamicEntity):

    def __init__(self, rect, particle_spawner, spawn_rate_per_sec, parent=None, max_particles=20,
                 xy_provider=lambda: (random.random(), 1)):
        self.parent = parent
        super().__init__(rect[0], rect[1], rect[2], rect[3])
        self.enabled = True
        self._spawn_chance_per_frame = spawn_rate_per_sec / configs.target_fps
        self._max_particles = max_particles
        self._spawner = particle_spawner
        self._xy_provider = xy_provider

        if self.parent is not None:
            self.set_xy((self.parent.get_x() + rect[0], self.parent.get_y() + rect[1]))
            self.set_frame_of_reference_parents(self.parent)
        else:
            self.set_xy((rect[0], rect[1]))

        self._active_particle_ids = []

    def get_physics_group(self):
        return DECORATION_GROUP

    def update(self):
        self._active_particle_ids = [p for p in self._active_particle_ids if self.get_world().has_entity_with_id(p)]
        if self._max_particles < 0 or len(self._active_particle_ids) < self._max_particles:
            if self.enabled and random.random() < self._spawn_chance_per_frame:
                xy_scalars = self._xy_provider()
                xy = util.add(self.get_xy(), (self.get_w() * xy_scalars[0], self.get_h() * xy_scalars[1]))
                new_particle = self._spawner(xy)
                if new_particle is not None:
                    self.get_world().add_entity(new_particle)
                    self._active_particle_ids.append(new_particle.get_ent_id())


class PlayerIndicatorEntity(Entity):

    def __init__(self, target_player, player_num=0):
        super().__init__(0, 0, w=8, h=8)
        self.target_player_ent_id = target_player.get_ent_id()

        self.max_bob_height = 12
        self.min_bob_height = 8
        self.bob_period = 90
        self.bob_tick = 0

        self.player_num = player_num

        self._sprites = []

    def get_sprites(self, player, proximity):
        outline_spr = spriteref.object_sheet().character_arrows[self.player_num]
        fill_spr = spriteref.object_sheet().character_arrow_fills[player.get_player_type().get_id()]
        return [outline_spr, fill_spr]

    def _get_depth(self):
        return -200

    def get_target_pts(self, player):
        return [(player.get_center()[0], player.get_y())]

    def should_remove(self, player):
        return player.has_ever_moved()

    def update(self):
        super().update()
        player = self.get_world().get_entity_by_id(self.target_player_ent_id)
        if player is None or self.should_remove(player):
            self.get_world().remove_entity(self)
        else:
            xy_list = self.get_target_pts(player)

            y_offs = 0.5 * (1 + math.cos(self.bob_tick / self.bob_period * 6.283) * (self.max_bob_height - self.min_bob_height)) + self.min_bob_height

            new_sprites = []
            sprite_i = 0
            for xy in xy_list:
                proximity = util.dist(xy, player.get_center())
                models = self.get_sprites(player, proximity)

                for m in models:
                    if sprite_i < len(self._sprites):
                        spr = self._sprites[sprite_i]
                        sprite_i += 1
                    else:
                        spr = sprites.ImageSprite.new_sprite(spriteref.ENTITY_LAYER, depth=self._get_depth())
                    new_x = xy[0] - m.width() // 2
                    new_y = xy[1] - m.height() - y_offs

                    spr = spr.update(new_model=m, new_x=new_x, new_y=new_y)
                    new_sprites.append(spr)

            self._sprites = new_sprites
            self.bob_tick += 1

    def all_sprites(self):
        for spr in self._sprites:
            yield spr


class EndBlockIndicatorEntity(PlayerIndicatorEntity):

    def get_sprites(self, player, proximity):
        max_dist = gs.get_instance().cell_size * 2
        alpha = util.bound(proximity / max_dist, 0.333, 1)
        return [spriteref.object_sheet().get_goal_arrow(player.get_player_type().get_id(), alpha=alpha)]

    def should_remove(self, player):
        return False  # ???

    def _get_depth(self):
        return PLAYER_DEPTH + 2  # behind player

    def get_target_pts(self, player):
        res = []
        for block in self.get_world().all_end_blocks(player_types=(player.get_player_type(),)):
            pt = (block.get_center()[0], block.get_y())
            res.append(pt)
        return res


class FloatingTextAlertEntity(Entity):

    def __init__(self, bottom_center_xy, text, color=(1, 1, 1), end_color=None, text_scale=1.0, font_provider=None,
                 depth=0, fadeout_time=30, fadeout_dir=(0, -5)):
        self.text_img = sprites.TextSprite(spriteref.ENTITY_LAYER, 0, 0, text, scale=text_scale, depth=depth,
                                           color=color, font_lookup=font_provider,
                                           outline_thickness=1, outline_color=colors.PERFECT_BLACK)
        self.start_xy = (bottom_center_xy[0] - self.text_img.get_rect()[2] // 2,
                         bottom_center_xy[1] - self.text_img.get_rect()[3])
        super().__init__(self.start_xy[0], self.start_xy[1],
                         w=self.text_img.get_rect()[2],
                         h=self.text_img.get_rect()[3])
        self.ticks_active = 0
        self.fadeout_time = fadeout_time
        self.end_xy = util.add(self.start_xy, fadeout_dir)

        self.start_color = color
        self.end_color = color if end_color is None else end_color

    def all_sprites(self):
        for s in super().all_sprites():
            yield s
        for s in self.text_img.all_sprites():
            yield s

    def get_prog(self):
        return util.bound(self.ticks_active / self.fadeout_time, 0.0, 1.0)

    def update(self):
        super().update()
        if self.ticks_active >= self.fadeout_time:
            self.get_world().remove_entity(self)
        else:
            self.set_xy(util.linear_interp(self.start_xy, self.end_xy, self.get_prog()))
        self.ticks_active += 1

    def update_sprites(self):
        x, y = self.get_xy()
        color = util.linear_interp(self.start_color, self.end_color, self.get_prog())

        self.text_img.update(new_x=x, new_y=y, new_color=color)


class SpikeEntity(Entity):

    def __init__(self, pts, w, h, direction=(0, -1), color_id=0, period=60, loop=True):
        Entity.__init__(self, pts[0][0], pts[0][1], w, h)

        self.controller = MoveBetweenPointsController(self, pts, period=period, loop=loop)

        direction = util.tuplify(direction)
        if direction not in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            raise ValueError("invalid direction: {}".format(direction))
        self._direction = direction  # direction the spikes point

        self._bot_sprites = []
        self._top_sprites = []

        hit_box = [0, 0, self.get_w(), self.get_h()]
        player_collider = RectangleCollider(hit_box, CollisionMasks.SENSOR,
                                            collides_with=CollisionMasks.ACTOR,
                                            name="pointy!!")
        self._sensor_id = player_collider.get_id()
        self._sensor_ent = SensorEntity(hit_box, player_collider, parent=self)

        self._color_id = color_id

    def all_sub_entities(self):
        yield self._sensor_ent

    def is_vertical(self):
        return self._direction[0] == 0

    def is_horizontal(self):
        return self._direction[1] == 0

    def get_length(self):
        if self.is_vertical():
            return self.get_w()
        else:
            return self.get_h()

    def get_spike_height(self):
        if self.is_vertical():
            return self.get_h()
        else:
            return self.get_w()

    def get_color_id(self):
        return self._color_id

    def update(self):
        super().update()
        self.controller.update()

        ents_in_spikes = self.get_world().get_sensor_state(self._sensor_id)
        for e in ents_in_spikes:
            if isinstance(e, PlayerEntity):
                e.set_death_reason(DeathReason.SPIKED)

        top_models = spriteref.object_sheet().get_spikes_with_length(self.get_length(), tops=True, overflow_if_not_divisible=True)
        bot_models = spriteref.object_sheet().get_spikes_with_length(self.get_length(), tops=False, overflow_if_not_divisible=True)

        util.extend_or_empty_list_to_length(self._top_sprites, len(top_models), creator=lambda: sprites.ImageSprite.new_sprite(spriteref.BLOCK_LAYER))
        util.extend_or_empty_list_to_length(self._bot_sprites, len(top_models), creator=lambda: sprites.ImageSprite.new_sprite(spriteref.BLOCK_LAYER))

        xpos = self.get_x()
        ypos = self.get_y()

        new_top_sprites = []
        new_bot_sprites = []

        spike_height = self.get_spike_height()
        color = self.get_color()

        for i in range(0, len(top_models)):
            top_spr = self._top_sprites[i]
            bot_spr = self._bot_sprites[i]
            top_model = top_models[i]
            bot_model = bot_models[i]

            bot_ratio = (1, max(0, spike_height - top_model.height() - 1) / bot_model.height())
            if self.is_horizontal():
                rotation = 3 if self._direction[0] < 0 else 1
                dxy = (0, top_model.width())
                bot_offs = (top_model.height() if self._direction[0] < 0 else 1, 0)
                # bot_ratio = (max(0, spike_height - top_model.height() - 1) / bot_model.height(), 1)
                top_offs = (0 if self._direction[0] < 0 else self.get_w() - top_model.height(), 0)
            else:
                rotation = 0 if self._direction[1] < 0 else 2
                dxy = (top_model.width(), 0)
                bot_offs = (0, top_model.height() if self._direction[1] < 0 else 1)
                top_offs = (0, 0 if self._direction[1] < 0 else self.get_h() - top_model.height())
            new_top_sprites.append(top_spr.update(new_model=top_model, new_x=xpos + top_offs[0], new_y=ypos + top_offs[1],
                                                  new_rotation=rotation, new_color=color))
            new_bot_sprites.append(bot_spr.update(new_model=bot_model, new_x=xpos + bot_offs[0], new_y=ypos + bot_offs[1],
                                                  new_rotation=rotation, new_ratio=bot_ratio, new_color=color))

            xpos += dxy[0]
            ypos += dxy[1]

        self._bot_sprites = new_bot_sprites
        self._top_sprites = new_top_sprites

    def update_sprites(self):
        super().update_sprites()
        self.controller.update_sprites()

    def all_sprites(self):
        for spr in self._top_sprites:
            yield spr
        for spr in self._bot_sprites:
            yield spr
        for spr in self.controller.all_sprites():
            yield spr


_ALL_INFO_TYPES = {}


class InfoEntityType:

    def __init__(self, ident, turns, sprite_lookup, floating_type=False):
        self.ident = ident
        self.faces_player = turns
        self.sprite_lookup = sprite_lookup
        self.floating_type = floating_type
        _ALL_INFO_TYPES[ident] = self

    def get_entity_sprites(self):
        all_sprites = [] if self.sprite_lookup is None else self.sprite_lookup()
        if self.floating_type or len(all_sprites) == 0:
            return all_sprites
        else:
            return [all_sprites[(gs.get_instance().anim_tick() // 8) % len(all_sprites)]]

    def turns_to_face_player(self):
        return self.faces_player

    def get_id(self):
        return self.ident


class FalseBlockEntity(BlockEntity):
    """Block that doesn't prevent movement and gradually disappears when you enter it"""

    REVEAL_TIME = 16

    def __init__(self, x, y, w, h, art_id=0, color_id=0):
        super().__init__(x, y, w=w, h=h, art_id=art_id, color_id=color_id)

        self.reveal_ticks = 0

        self.set_colliders([])  # nothing should ever collide with this

        player_sensor = RectangleCollider([0, 0, w, h], CollisionMasks.SENSOR, collides_with=(CollisionMasks.ACTOR,))
        self.player_sensor_id = player_sensor.get_id()
        self._sensor_ent = SensorEntity([0, 0, w, h], [player_sensor], parent=self)

        self._x_sprite_for_editor = None

        self.last_revealed_tick = -1

    def all_sub_entities(self):
        yield self._sensor_ent

    def is_block(self):
        return False  # not a block in any real sense (collisions, mainly)

    def get_color(self, ignore_override=False, include_lighting=True):
        base_color = super().get_color(ignore_override=ignore_override, include_lighting=include_lighting)

        # goes to black as it becomes more revealed
        reveal_prog = util.bound(self.reveal_ticks / FalseBlockEntity.REVEAL_TIME, 0, 1)
        return colors.darken(base_color, reveal_prog)

    def update(self):
        super().update()

        # every block auto-decays by one
        if self.reveal_ticks > 0:
            self.reveal_ticks -= 1

        cur_tick = gs.get_instance().tick_count()
        if self.last_revealed_tick == cur_tick:
            pass  # already been updated by another linked block
        elif len(self.get_world().get_sensor_state(self.player_sensor_id)) > 0:
            # this block is responsible for updating its linked neighbors
            for block, deg in self.self_and_all_linked_neighbors_with_degrees():
                block.last_revealed_tick = cur_tick

                # blocks closer to player get revealed faster
                if deg == 0 or cur_tick % (2 ** deg) == 0:
                    block.reveal_ticks = block.reveal_ticks + 1

                # offset the auto-decay if it's connected at all, and apply an upper bound
                block.reveal_ticks = min(block.reveal_ticks + 1, FalseBlockEntity.REVEAL_TIME + 1)

    def update_sprites(self):
        super().update_sprites()

        # add a signal in the editor to distinguish it from real blocks
        if self.get_world().is_being_edited():
            font = spritesheets.get_default_font(small=False, mono=True)
            if self._x_sprite_for_editor is None:
                self._x_sprite_for_editor = sprites.TextSprite(spriteref.ENTITY_LAYER, 0, 0, "x", scale=1,
                                                               font_lookup=font)
            char_size = font.get_char("X").size()
            scale = 1
            self._x_sprite_for_editor.update(new_color=colors.PERFECT_BLACK,
                                             new_scale=scale,
                                             new_outline_thickness=scale,
                                             new_outline_color=colors.PERFECT_WHITE,
                                             new_depth=-10)
            c_xy = self.get_center()
            self._x_sprite_for_editor.update(new_x=c_xy[0] - ((char_size[0] - 1) * scale) // 2,
                                             new_y=c_xy[1] - ((char_size[1] + 1) * scale) // 2)
        else:
            self._x_sprite_for_editor = None

    def all_sprites(self):
        for spr in super().all_sprites():
            yield spr
        if self._x_sprite_for_editor is not None:
            # it looks cooler if it flashes~
            if (gs.get_instance().anim_tick() // 8) % 2 == 0:
                yield self._x_sprite_for_editor

    def self_and_all_linked_neighbors_with_degrees(self):
        """
        :return: (neighbor: FalseBlockEntity, degree: int)
        """
        graph = {}     # FalseBlockEntity -> set of linked FalseBlockEntity
        all_nodes = set()
        start_nodes = set()

        q = [self]

        seen = set()
        seen.add(self)

        while len(q) > 0:
            block = q.pop()
            all_nodes.add(block)
            if len(self.get_world().get_sensor_state(block.player_sensor_id)) > 0:
                start_nodes.add(block)

            if block not in graph:
                graph[block] = set()

            for n in block.get_linked_neighbors():
                graph[block].add((n, 1))

                if n not in seen:
                    seen.add(n)
                    q.append(n)

        distances = util.djikstras(all_nodes, graph, start_nodes)

        res = []
        for n in distances:
            if distances[n][0] != float('inf'):
                res.append((n, distances[n][0]))
        res.sort(key=lambda n: n[1])

        return res

    def get_linked_neighbors(self) -> typing.List['FalseBlockEntity']:
        search_rect = util.rect_expand(self.get_rect(with_xy_perturbs=False), all_expand=1)
        for n in self.get_world().all_entities_in_rect(search_rect, cond=lambda e: isinstance(e, FalseBlockEntity)):
            if n != self:
                yield n


class InfoEntityTypes:

    EXCLAM = InfoEntityType("exclam", False, lambda: spriteref.object_sheet().info_exclamation, floating_type=True)
    QUESTION = InfoEntityType("question", False, lambda: spriteref.object_sheet().info_question, floating_type=True)
    PLAYER_FAST = InfoEntityType(const.PLAYER_FAST, True, lambda: spriteref.object_sheet().get_player_sprites(const.PLAYER_FAST, spriteref.PlayerStates.IDLE))
    PLAYER_SMALL = InfoEntityType(const.PLAYER_SMALL, True, lambda: spriteref.object_sheet().player_b[spriteref.PlayerStates.IDLE])
    PLAYER_HEAVY = InfoEntityType(const.PLAYER_HEAVY, True, lambda: spriteref.object_sheet().player_c[spriteref.PlayerStates.IDLE])
    PLAYER_FLYING = InfoEntityType(const.PLAYER_FLYING, True, lambda: spriteref.object_sheet().player_d[spriteref.PlayerStates.IDLE])

    @staticmethod
    def get_by_id(ident):
        if ident in _ALL_INFO_TYPES:
            return _ALL_INFO_TYPES[ident]
        else:
            return InfoEntityTypes.QUESTION

    @staticmethod
    def all_types():
        return [_ALL_INFO_TYPES[key] for key in _ALL_INFO_TYPES]


class InfoEntity(Entity):

    def __init__(self, x, y, points, text, info_type, dialog_id=None, color_id=0):
        cs = gs.get_instance().cell_size
        Entity.__init__(self, x, y, w=cs, h=cs)
        self._points = points

        self._text = text
        self._color_id = color_id
        self._info_type = info_type if isinstance(info_type, InfoEntityType) else InfoEntityTypes.get_by_id(info_type)
        self._dialog_id = dialog_id

        self._base_sprite = None
        self._top_sprite = None
        self._text_sprite = None
        self._text_bg_sprite = None

        self._activation_radius = 8 * cs // 4
        self._should_show_text = False

        self._ticks_overlapping_player = 0
        self._activation_thresh = 10

        self._point_sprite_list_for_editor = []

    def _get_sprites(self):
        """returns: (top_sprite, base_sprite) or [sprite]"""
        return self._info_type.get_entity_sprites()

    def get_color_id(self):
        return self._color_id

    def update_sprites(self):
        all_sprites = self._get_sprites()
        base_model = all_sprites[0] if len(all_sprites) >= 1 else None
        top_model = all_sprites[1] if len(all_sprites) >= 2 else None

        w = self.get_world()
        p = None if w is None else w.get_player()

        should_xflip = self._info_type.faces_player and (p is not None and p.get_center()[0] < self.get_center()[0])

        if base_model is None:
            self._base_sprite = None
        else:
            if self._base_sprite is None:
                self._base_sprite = sprites.ImageSprite(base_model, 0, 0, spriteref.ENTITY_LAYER)
            cx = self.get_center()[0]
            bot_y = self.get_y() + self.get_h()
            self._base_sprite = self._base_sprite.update(new_model=base_model,
                                                         new_x=cx - base_model.width() // 2,
                                                         new_y=bot_y - base_model.height(),
                                                         new_depth=WORLD_UI_DEPTH,
                                                         new_color=self.get_color(),
                                                         new_xflip=should_xflip)

        cs = gs.get_instance().cell_size
        if top_model is None:
            self._top_sprite = None
        else:
            if self._top_sprite is None:
                self._top_sprite = sprites.ImageSprite(top_model, 0, 0, spriteref.ENTITY_LAYER)
            self._top_sprite = self._top_sprite.update(new_model=top_model,
                                                       new_x=cx - top_model.width() // 2,
                                                       new_y=bot_y - base_model.height() - cs // 8 - top_model.height(),
                                                       new_depth=PLAYER_DEPTH + 1,
                                                       new_color=self.get_color(),
                                                       new_xflip=should_xflip)

        if not self._should_show_text or (w is not None and w.is_dialog_active()):
            self._text_sprite = None
            self._text_bg_sprite = None
        else:
            if self._text_sprite is None:
                self._text_sprite = sprites.TextSprite(spriteref.ENTITY_LAYER, 0, 0, self._text, depth=WORLD_UI_DEPTH,
                                                       font_lookup=spriteref.spritesheets.get_default_font(small=True))
            self._text_sprite.update(new_text=self._text)
            if len(self._points) == 0:
                height = self._base_sprite.height() if self._base_sprite is not None else 0
                height += self._top_sprite.height() if self._top_sprite is not None else 0
                height = max(height, gs.get_instance().cell_size * 2)
                pt = (self.get_center()[0] - self._text_sprite.size()[0] // 2,
                      self.get_y() + self.get_h() - height - self._text_sprite.size()[1] - 8)
            else:
                pt = self._points[0]
            self._text_sprite.update(new_x = pt[0], new_y = pt[1])

            text_rect = self._text_sprite.get_rect()
            bg_rect = util.rect_expand(text_rect, all_expand=0)
            if self._text_bg_sprite is None:
                self._text_bg_sprite = sprites.BorderBoxSprite(spriteref.ENTITY_LAYER, bg_rect,
                                                               all_borders=spriteref.overworld_sheet().border_thin)
            self._text_bg_sprite.update(new_rect=bg_rect)

    def update(self):
        super().update()
        if self._ticks_overlapping_player < 0:
            self._ticks_overlapping_player += 1
        else:
            self._ticks_overlapping_player = max(0, self._ticks_overlapping_player - 1)

        _update_point_sprites_for_editor(self.is_selected_in_editor(), self._point_sprite_list_for_editor,
                                         self._points, (8, 8))

        w = self.get_world()
        p = None if w is None else w.get_player(must_be_active=True)

        overlapping = False
        if p is not None:
            overlapping = util.dist(p.get_center(), self.get_center()) <= self._activation_radius
            if overlapping:
                self._ticks_overlapping_player = min(self._activation_thresh, self._ticks_overlapping_player + 2)

        self._should_show_text = self._ticks_overlapping_player >= self._activation_thresh

        if self._dialog_id is not None and overlapping and self._should_show_text and inputs.get_instance().was_pressed(const.MENU_ACCEPT):
            d = dialog.get_dialog(self._dialog_id, p.get_player_type(), self._info_type)
            if d is not None:
                self._ticks_overlapping_player = -60  # so that we can't insta-reactivate dialog after this one is over
                import src.engine.scenes as scenes
                active_scene = scenes.get_instance().get_active_scene()
                if isinstance(active_scene, dialog.DialogScene):
                    active_scene.start_dialog(d)

    def all_sprites(self):
        yield self._text_sprite
        yield self._text_bg_sprite
        yield self._base_sprite
        yield self._top_sprite

        for spr in self._point_sprite_list_for_editor:
            yield spr


class CameraBoundMarker(Entity):

    def __init__(self, x, y, idx, show_timer=True):
        super().__init__(x, y, w=16, h=16)
        self.idx = idx
        self.show_timer = show_timer

        self._sprite = None
        self._number_sprites = []
        self._timer_sprite = None

    def get_idx(self):
        return self.idx

    def get_show_timer(self):
        return self.show_timer

    def get_color(self, ignore_override=False):
        if ignore_override:
            return colors.PERFECT_WHITE
        else:
            return super().get_color(ignore_override=ignore_override)

    def update_sprites(self):
        if self.get_world().is_being_edited():
            if self._sprite is None:
                self._sprite = sprites.ImageSprite.new_sprite(spriteref.WORLD_UI_LAYER)
            self._sprite = self._sprite.update(new_model=spriteref.object_sheet().get_camera_boundary_sprite(self.idx),
                                               new_x=self.get_x(),
                                               new_y=self.get_y(),
                                               new_color=self.get_color())
            numbers = [int(c) for c in str(self.idx)]
            util.extend_or_empty_list_to_length(
                self._number_sprites,
                len(numbers),
                creator=lambda: sprites.ImageSprite.new_sprite(spriteref.WORLD_UI_LAYER, depth=-5))
            for i, c in enumerate(numbers):
                model = spriteref.level_builder_sheet().number_icons[c]
                self._number_sprites[i] = self._number_sprites[i].update(
                    new_model=model,
                    new_x=self.get_x() + self.get_w() - 1 - (model.width() - 1) * (len(numbers) - i),
                    new_y=self.get_y() + self.get_h() - model.height(),
                    new_color=self.get_color())

            if self.show_timer:
                if self._timer_sprite is None:
                    self._timer_sprite = sprites.ImageSprite.new_sprite(spriteref.WORLD_UI_LAYER, depth=-3)
                model = spriteref.level_builder_sheet().clock_icon
                self._timer_sprite = self._timer_sprite.update(
                    new_model=model,
                    new_x=self.get_x(),
                    new_y=self.get_y() + self.get_h() - model.height(),
                    new_color=self.get_color())
            else:
                self._timer_sprite = None
        else:
            self._sprite = None
            self._number_sprites.clear()
            self._timer_sprite = None

    def all_sprites(self):
        yield self._sprite
        yield self._timer_sprite
        for spr in self._number_sprites:
            yield spr


class AbstractZoneEntity(Entity):

    def __init__(self, x, y, w, h, must_be_fully_inside=True, entity_filter=lambda e: True):
        super().__init__(x, y, w, h)
        self.must_be_fully_inside = must_be_fully_inside
        self.entity_filter = entity_filter

        self._editor_icon_sprite = None
        self._editor_rect_sprite = None

    def update(self):
        super().update()

        my_rect = self.get_rect()
        for e in self.get_world().all_entities_in_rect(my_rect, cond=self.entity_filter):
            if not self.must_be_fully_inside or util.rect_contains(my_rect, e.get_rect(with_xy_perturbs=False)):
                self.handle_entity(e)

        self.update_sprites()

    def update_sprites(self):
        if self.get_world().is_being_edited():
            if self._editor_rect_sprite is None:
                self._editor_rect_sprite = sprites.RectangleOutlineSprite(spriteref.POLYGON_LAYER)
            self._editor_rect_sprite = self._editor_rect_sprite.update(new_rect=self.get_rect(),
                                                                       new_color=self.get_rect_color(),
                                                                       new_outline=1)
            icon_model = self.get_editor_icon_model()
            if icon_model is not None:
                if self._editor_icon_sprite is None:
                    self._editor_icon_sprite = sprites.ImageSprite.new_sprite(spriteref.WORLD_UI_LAYER)
                c_xy = self.get_center()
                self._editor_icon_sprite = self._editor_icon_sprite.update(new_model=self.get_editor_icon_model(),
                                                                           new_x=c_xy[0] - icon_model.width() // 2,
                                                                           new_y=c_xy[1] - icon_model.height() // 2,
                                                                           new_color=self.get_color())
            else:
                self._editor_icon_sprite = None
        else:
            self._editor_rect_sprite = None
            self._editor_icon_sprite = None

    def all_sprites(self):
        for spr in super().all_sprites():
            yield spr
        if self._editor_icon_sprite is not None:
            yield self._editor_icon_sprite
        if self._editor_rect_sprite is not None:
            yield self._editor_rect_sprite

    def get_rect_color(self):
        raise NotImplementedError()

    def get_editor_icon_model(self):
        raise NotImplementedError()

    def handle_entity(self, ent):
        raise NotImplementedError()


class KillZoneEntity(AbstractZoneEntity):

    def __init__(self, x, y, w, h):
        super().__init__(x, y, w, h, must_be_fully_inside=True, entity_filter=lambda e: e.is_player())

    def get_rect_color(self):
        return colors.PERFECT_RED

    def get_editor_icon_model(self):
        return spriteref.object_sheet().skull_icon

    def handle_entity(self, ent: PlayerEntity):
        if isinstance(ent, PlayerEntity):
            ent.set_death_reason(DeathReason.OUT_OF_BOUNDS)


class CollisionMask:

    def __init__(self, name, is_solid=True, is_sensor=False, render_depth=20):
        self._name = name
        self._is_solid = is_solid
        self._is_sensor = is_sensor
        self._render_depth = render_depth

    def get_name(self) -> str:
        return self._name

    def get_render_depth(self) -> int:
        return self._render_depth

    def is_solid(self) -> bool:
        return self._is_solid

    def is_sensor(self) -> bool:
        return self._is_sensor


class CollisionMasks:

    BLOCK = CollisionMask("block", render_depth=20)
    BREAKABLE = CollisionMask("breakable_block", render_depth=20)

    SLOPE_BLOCK_HORZ = CollisionMask("slope_block_horz", render_depth=25)
    SLOPE_BLOCK_VERT = CollisionMask("slope_block_vert", render_depth=25)

    ACTOR = CollisionMask("actor", render_depth=10)  # aka BLOCK_AVOIDER
    BREAKING = CollisionMask("breaking", render_depth=10)

    SENSOR = CollisionMask("block_sensor", is_solid=False, is_sensor=True, render_depth=10)

    SNAP_DOWN_SENSOR = CollisionMask("snap_down_sensor", is_solid=False, is_sensor=True, render_depth=15)

    PARTICLE = CollisionMask("particle", is_solid=True, render_depth=16)


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

    def __init__(self, points, mask, collides_with=None, resolution_hint=None, color=colors.PERFECT_RED, name=None):
        self._mask = mask
        self._collides_with = [] if collides_with is None else util.listify(collides_with)
        self._points = points
        self._resolution_hint = resolution_hint if resolution_hint is not None else CollisionResolutionHints.BOTH
        self._name = name

        self._debug_color = color
        self._id = _next_collider_id()

        self._ignore_ids = set()
        self._entity_ignore_conds = []

        self._is_enabled = True

    def get_id(self):
        return self._id

    def get_name(self):
        return self._name

    def set_enabled(self, val):
        self._is_enabled = val

    def is_enabled(self):
        return self._is_enabled

    def get_mask(self):
        return self._mask

    def set_mask(self, val):
        self._mask = val

    def get_resolution_hint(self):
        return self._resolution_hint

    def set_collides_with(self, other_masks):
        self._collides_with = util.listify(other_masks)

    def get_collides_with(self):
        return self._collides_with

    def collides_with(self, other: 'PolygonCollider'):
        return self.collides_with_mask(other.get_mask()) and other.get_id() not in self._ignore_ids

    def set_ignore_collisions_with(self, other: Union[List['PolygonCollider'], 'PolygonCollider']):
        for c in util.listify(other):
            self._ignore_ids.add(c.get_id())

    def add_entity_ignore_condition(self, cond):
        """cond: Entiy -> bool"""
        self._entity_ignore_conds.append(cond)

    def can_collide_with_colliders_from_entity(self, other_entity):
        if other_entity is None:
            return True
        else:
            for cond in self._entity_ignore_conds:
                if cond(other_entity):
                    return False
            return True

    def collides_with_mask(self, mask: CollisionMask):
        return mask in self._collides_with

    def collides_with_masks(self, masks, any=True):
        any_failed = False
        for mask in masks:
            if self.collides_with_mask(mask):
                if any:
                    return True
            else:
                any_failed = True
                if not any:
                    return False
        return not any_failed

    def is_overlapping(self, offs, other, other_offs):
        raise NotImplementedError()  # TODO general polygon collisions

    def is_colliding_with(self, offs, other_collider, other_offs, other_entity):
        return (self.can_collide_with_colliders_from_entity(other_entity)
                and self.collides_with(other_collider)
                and self.is_overlapping(offs, other_collider, other_offs))

    def is_colliding_with_any(self, offs, other_colliders, other_offs, other_entity):
        if not self.can_collide_with_colliders_from_entity(other_entity):
            return False
        else:
            for c in other_colliders:
                if self.collides_with(c) and self.is_overlapping(offs, c, other_offs):
                    return True
            return False

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

    def __init__(self, points, mask, collides_with=None, resolution_hint=None, color=colors.PERFECT_RED, name=None):
        if len(points) != 3:
            raise ValueError("must have 3 points, instead got: {}".format(points))
        PolygonCollider.__init__(self, points, mask, collides_with=collides_with, resolution_hint=resolution_hint,
                                 color=color, name=name)

    def is_overlapping(self, offs, other, other_offs):
        if isinstance(other, TriangleCollider):
            return util.triangles_intersect(self.get_points(offs=offs), other.get_points(offs=other_offs))
        elif isinstance(other, RectangleCollider):
            return util.rect_intersects_triangle(other.get_rect(offs=other_offs), self.get_points(offs=offs))
        else:
            return super().is_overlapping(offs, other, other_offs)


class RectangleCollider(PolygonCollider):

    def __init__(self, rect, mask, collides_with=None, resolution_hint=None, color=colors.PERFECT_RED, name=None):
        points = [p for p in util.all_rect_corners(rect, inclusive=False)]
        PolygonCollider.__init__(self, points, mask, collides_with=collides_with, resolution_hint=resolution_hint,
                                 color=color, name=name)

    def is_overlapping(self, offs, other, other_offs):
        if isinstance(other, RectangleCollider):
            return util.get_rect_intersect(self.get_rect(offs=offs), other.get_rect(offs=other_offs)) is not None
        elif isinstance(other, TriangleCollider):
            return util.rect_intersects_triangle(self.get_rect(offs=offs), other.get_points(offs=other_offs))
        else:
            return super().is_overlapping(offs, other, other_offs)


