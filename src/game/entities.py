
import math
import random

import src as src  # for typing~

import src.utils.util as util
import src.engine.sprites as sprites
import src.engine.inputs as inputs
import src.engine.keybinds as keybinds
import src.engine.globaltimer as globaltimer
import configs as configs

import src.game.spriteref as spriteref
import src.game.playertypes as playertypes
import src.game.colors as colors
import src.game.globalstate as gs
import src.game.const as const
import src.game.debug as debug


_ENT_ID = 0


def next_entity_id():
    global _ENT_ID
    _ENT_ID += 1
    return _ENT_ID - 1


# physics groups
UNKNOWN_GROUP = -1
ENVIRONMENT_GROUP = 5
ACTOR_GROUP = 10


# depths
PLAYER_DEPTH = 0
PARTICLE_DEPTH = 2
BLOCK_DEPTH = 10


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

        self._world = None  # world sets this when entity is added / removed
        self._spec = None   # bp sets this when it creates the entity

        self._color_override = None
        self._is_selected_in_editor = False

        self._debug_sprites = {}

        self._colliders = []

        self._frame_of_reference_parent = None
        self._frame_of_reference_parent_do_horz = True
        self._frame_of_reference_parent_do_vert = True
        self._frame_of_reference_children = []

    def get_world(self) -> 'src.game.worlds.World':
        return self._world

    def get_spec(self):
        return self._spec

    def set_world(self, world):
        self._world = world

    def set_color_override(self, val):
        self._color_override = val

    def get_color_override(self):
        return self._color_override

    def set_selected_in_editor(self, val):
        self._is_selected_in_editor = val

    def is_selected_in_editor(self):
        return self._is_selected_in_editor

    def about_to_remove_from_world(self):
        pass

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

    def set_frame_of_reference_parent(self, parent, horz=True, vert=True):
        self._frame_of_reference_parent_do_horz = horz
        self._frame_of_reference_parent_do_vert = vert

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

    def update_sprites(self):
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

    def was_crushed(self):
        pass

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
        elif self.get_color_id() is not None:
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

    def is_actor(self):
        return self.is_player()

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
        return colors.PERFECT_DARK_GRAY

    def get_color_id(self):
        return 0

    def all_sprites(self):
        for spr in self.all_debug_sprites():
            yield spr

    def get_physics_group(self):
        return ENVIRONMENT_GROUP


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
        pass

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
            self._sprite = self._sprite.update(new_model=img, new_x=self.get_x(), new_y=self.get_y(),
                                               new_scale=1, new_depth=0, new_color=self.get_color(),
                                               new_ratio=ratio)
        else:
            scale = 1
            inner_rect = util.rect_expand(self.get_rect(), all_expand=-spriteref.block_sheet().border_inset * scale)
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


class SensorEntity(Entity):

    def __init__(self, rect, sensor, parent=None):
        self.parent = parent
        Entity.__init__(self, 0, 0, w=rect[2], h=rect[3])

        if self.parent is not None:
            self.set_xy((self.parent.get_x() + rect[0], self.parent.get_y() + rect[1]))
            self.set_frame_of_reference_parent(self.parent)
        else:
            self.set_xy((rect[0], rect[1]))

        self.set_colliders([sensor])

    def is_dynamic(self):
        return True

    def get_physics_group(self):
        return ACTOR_GROUP


class CompositeBlockEntity(AbstractBlockEntity):

    class BlockSpriteInfo:
        def __init__(self, model_provider=lambda: None, xy_offs=(0, 0), rotation=0, scale=1, xflip=False):
            self.model_provider = model_provider
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

            x = self.get_x()
            y = self.get_y()
            self._sprites[i] = spr.update(new_model=info.model_provider(),
                                          new_x=x + info.xy_offs[0], new_y=y + info.xy_offs[1],
                                          new_scale=info.scale, new_xflip=info.xflip,
                                          new_color=self.get_color(),
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


class MovingBlockEntity(BlockEntity):

    def __init__(self, w, h, pts, period=90, loop=True, art_id=0, color_id=0):
        BlockEntity.__init__(self, pts[0][0], pts[0][1], w, h, art_id=art_id, color_id=color_id)
        self._pts = pts
        self._period = period
        self._loop = loop

        self._point_sprites_for_editor = []

    def is_dynamic(self):
        return False

    def update(self):
        tick_count = self.get_world().get_tick()

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

        super().update()

    def update_sprites(self):
        if not self.is_selected_in_editor():
            self._point_sprites_for_editor.clear()
        else:
            util.extend_or_empty_list_to_length(self._point_sprites_for_editor, len(self._pts),
                                                creator=lambda: sprites.RectangleOutlineSprite(spriteref.POLYGON_LAYER))
            block_size = self.get_size()
            for i in range(0, len(self._pts)):
                pt = self._pts[i]
                pt_sprite = self._point_sprites_for_editor[i]
                self._point_sprites_for_editor[i] = pt_sprite.update(new_rect=[pt[0], pt[1], block_size[0], block_size[1]],
                                                                     new_outline=1, new_color=colors.PERFECT_YELLOW,
                                                                     new_depth=-500)
        super().update_sprites()

    def all_sprites(self):
        for spr in self._point_sprites_for_editor:
            yield spr
        for spr in super().all_sprites():
            yield spr


class DoorBlock(BlockEntity):

    def __init__(self, x, y, w, h, toggle_idx):
        BlockEntity.__init__(self, x, y, w, h)
        self._toggle_idx = toggle_idx
        self._is_solid = True

    def get_toggle_idx(self):
        return self._toggle_idx

    def update(self):
        should_be_solid = not self.get_world().is_door_unlocked(self._toggle_idx)
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


class KeyEntity(Entity):

    @staticmethod
    def make_at_cell(grid_x, grid_y, toggle_idx):
        cs = gs.get_instance().cell_size
        return KeyEntity(cs * grid_x + cs // 4, cs * grid_y, toggle_idx)

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

        player_collider = RectangleCollider([0, 0, cs // 2, cs], CollisionMasks.SENSOR, collides_with=(CollisionMasks.ACTOR,))
        self.player_sensor_id = player_collider.get_id()
        self._sensor_ent = SensorEntity([0, 0, cs // 2, cs], player_collider, parent=self)

    def set_world(self, world):
        super().set_world(world)
        if world is not None:
            world.add_entity(self._sensor_ent)

    def about_to_remove_from_world(self):
        super().about_to_remove_from_world()
        self.get_world().remove_entity(self._sensor_ent)

    def is_satisfied(self):
        return self._player_colliding_tick_count >= self._player_collide_thresh

    def all_sprites(self):
        yield self._icon_sprite
        yield self._base_sprite

    def get_toggle_idx(self):
        return self._toggle_idx

    def update(self):
        if len(self.get_world().get_sensor_state(self.player_sensor_id)) > 0:
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

        if self.is_satisfied():
            bob_height = 0
        else:
            bob_height = int(bob_height * (1 - self._player_colliding_tick_count / self._player_collide_thresh))

        self._icon_sprite = self._icon_sprite.update(new_model=key_model,
                                                     new_x=rect[0] + rect[2] // 2 - key_model.width() // 2,
                                                     new_y=rect[1] + rect[3] - bob_height - key_model.height())
        self._bob_tick_count += 1

        if self._base_sprite is None:
            self._base_sprite = sprites.ImageSprite.new_sprite(spriteref.ENTITY_LAYER, depth=-3)
        self._base_sprite = self._base_sprite.update(new_model=base_model,
                                                     new_x=rect[0] + rect[2] // 2 - base_model.width() // 2,
                                                     new_y=rect[1] + rect[3] - base_model.height())


class StartBlock(BlockEntity):

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

    def get_main_model(self):
        cs = gs.get_instance().cell_size
        size = (self.get_w() // cs, self.get_h() // cs)
        return spriteref.block_sheet().get_start_block_sprite(size, self.get_player_type().get_id())


class EndBlock(CompositeBlockEntity):

    def __init__(self, x, y, w, h, player_type, color_id=-1):
        cs = gs.get_instance().cell_size
        if w != cs * 2:
            raise ValueError("illegal width for start block: {}".format(w))
        if h != cs:
            raise ValueError("illegal height for start block: {}".format(h))

        self._player_type = player_type

        if color_id < 0:
            color_id = player_type.get_color_id()

        dip_h = 3

        colliders = []
        colliders.extend(BlockEntity.build_colliders_for_rect([2, dip_h, 28, 16 - dip_h]))  # center
        colliders.extend(BlockEntity.build_colliders_for_rect([0, 0, 2, 16]))   # left
        colliders.extend(BlockEntity.build_colliders_for_rect([30, 0, 2, 16]))  # right

        self._is_satisfied = False

        sprite_infos = [CompositeBlockEntity.BlockSpriteInfo(model_provider=lambda: self.get_main_model(),
                                                             xy_offs=(0, 0))]

        CompositeBlockEntity.__init__(self, x, y, colliders, sprite_infos, color_id=color_id)

        # this is what it uses to detect the player (normally blocks can't have sensors)
        level_end_collider = RectangleCollider([0, 0, 28, 10], CollisionMasks.SENSOR,
                                               collides_with=CollisionMasks.ACTOR,
                                               name="level_end_{}".format(self._player_type))
        self._level_end_sensor_id = level_end_collider.get_id()
        self._player_stationary_in_sensor_count = 0
        self._player_stationary_in_sensor_limit = 10
        self._sensor_ent = SensorEntity([2, 0, 28, dip_h + 2], level_end_collider, parent=self)

    def set_world(self, world):
        super().set_world(world)
        if world is not None:
            world.add_entity(self._sensor_ent)

    def about_to_remove_from_world(self):
        super().about_to_remove_from_world()
        self.get_world().remove_entity(self._sensor_ent)

    def update(self):
        actors_in_sensor = self.get_world().get_sensor_state(self._level_end_sensor_id)
        found_one = False
        for a in actors_in_sensor:
            if isinstance(a, PlayerEntity) and a.get_player_type() == self._player_type and not a.is_crouching():
                # TODO velocity relative to block?
                if util.mag(a.get_vel()) < 2:
                    self._player_stationary_in_sensor_count += 1
                    found_one = True
        if not found_one:
            self._player_stationary_in_sensor_count = 0

        was_satisfied = self._is_satisfied
        self._is_satisfied = self._player_stationary_in_sensor_count >= self._player_stationary_in_sensor_limit

        if not was_satisfied and self._is_satisfied:
            print("INFO: satisfied end block for player: {}".format(self.get_player_type()))

    def is_satisfied(self):
        return self._is_satisfied

    def get_player_type(self):
        return self._player_type

    def get_main_model(self):
        cs = gs.get_instance().cell_size
        size = (self.get_w() // cs, self.get_h() // cs)
        return spriteref.block_sheet().get_end_block_sprite(size, self.get_player_type().get_id())

    def __repr__(self):
        return type(self).__name__ + "({}, {})".format(self.get_rect(), self.get_player_type())


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


class PlayerEntity(Entity):

    def __init__(self, x, y, player_type: playertypes.PlayerType, controller=None, align_to_cells=True):
        cs = gs.get_instance().cell_size
        w = int(cs * player_type.get_size()[0])
        h = int(cs * player_type.get_size()[1])

        Entity.__init__(self, 0, 0, w=w, h=h)

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

        self.set_colliders([vert_env_collider, horz_env_collider,
                            self.foot_sensor, self.left_sensor, self.right_sensor,  self.snap_down_sensor,
                            slope_collider_main_horz, slope_collider_main_top,
                            foot_slope_env_collider, foot_slope_sensor])

        if align_to_cells:
            cell_w = math.ceil(w / cs)
            cell_h = math.ceil(h / cs)

            aligned_x = int(x + (cs * cell_w - w) / 2)  # center the player across the cells it overlaps
            aligned_y = int(y - (cs * (cell_h - 1)) + (cs * cell_h - h))  # ground the player in the y-cell
            self.set_xy((aligned_x, aligned_y))
        else:
            self.set_xy((x, y))

    def get_player_type(self):
        return self._player_type

    def get_controller(self):
        return self._controller

    def is_active(self):
        return self._controller.is_active()

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

        should_snap_down = self._last_jump_time > 3 and self._air_time <= 1 and self._y_vel >= 0
        self.snap_down_sensor.set_enabled(should_snap_down)

        self._last_jump_time += 1

        if self.get_x_vel() < -0.1:
            self._dir_facing = -1
        elif self.get_x_vel() > 0.1:
            self._dir_facing = 1

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

    def dir_facing(self):
        if self.is_clinging_to_wall():
            if self.is_left_walled() and self.is_right_walled():
                return -self._dir_facing  # i promise this makes sense TODO does it?
            else:
                return 1 if self.is_left_walled() else -1
        else:
            return self._dir_facing

    def _handle_inputs(self):
        cur_inputs = self.get_controller().get_inputs(self.get_world().get_tick())
        request_left = cur_inputs.is_left_held()
        request_right = cur_inputs.is_right_held()
        request_jump = cur_inputs.was_jump_pressed()
        holding_jump = cur_inputs.is_jump_held()
        holding_crouch = cur_inputs.is_down_held()

        self._holding_left = request_left
        self._holding_right = request_right
        self._holding_crouch = self.get_player_type().can_crouch() and holding_crouch

        if request_jump:
            self._last_jump_request_time = 0
        else:
            self._last_jump_request_time += 1

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
                accel += self._air_accel

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
            if self.is_grounded():
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

    def update_frame_of_reference_parent(self):
        # TODO should we care about slope blocks? maybe? otherwise you could get scooped up by a moving platform
        # TODO touching your toe as you're (mostly) standing on a slop
        blocks_upon = self.get_world().get_sensor_state(self.foot_sensor_id)
        best_upon, _ = self._choose_best_frame_of_reference(blocks_upon, self.foot_sensor)
        if best_upon is not None:
            self.set_frame_of_reference_parent(best_upon)
            return

        blocks_on_left = self.get_world().get_sensor_state(self.left_sensor_id)
        blocks_on_right = self.get_world().get_sensor_state(self.right_sensor_id)

        best_on_left, left_overlap = self._choose_best_frame_of_reference(blocks_on_left, self.left_sensor)
        best_on_right, right_overlap = self._choose_best_frame_of_reference(blocks_on_right, self.right_sensor)

        if best_on_left is not None and best_on_right is not None:
            if left_overlap <= right_overlap:
                self.set_frame_of_reference_parent(best_on_left, vert=False)
            else:
                self.set_frame_of_reference_parent(best_on_right, vert=False)
        elif best_on_left is not None:
            self.set_frame_of_reference_parent(best_on_left, vert=False)
        elif best_on_right is not None:
            self.set_frame_of_reference_parent(best_on_right, vert=False)
        else:
            self.set_frame_of_reference_parent(None)

    def _choose_best_frame_of_reference(self, candidate_list, sensor):
        if len(candidate_list) == 0:
            return None, None
        elif len(candidate_list) == 1:
            return candidate_list[0]
        else:
            candidate_list.sort(key=lambda b: b.get_rect())  # for consistency
            # figure out which one we're on more
            xy = self.get_xy(raw=False)
            collider_rect = sensor.get_rect(xy)
            max_overlap = -1
            max_overlap_block = None
            for block in candidate_list:
                for block_collider in block.all_colliders():
                    block_collider_rect = block_collider.get_rect(block.get_xy(raw=False))
                    overlap_rect = util.get_rect_intersect(collider_rect, block_collider_rect)
                    if overlap_rect is None:
                        continue  # ??
                    elif overlap_rect[2] * overlap_rect[3] > max_overlap:
                        max_overlap = overlap_rect[2] * overlap_rect[3]
                        max_overlap_block = block

            return max_overlap_block, max_overlap

    def get_debug_color(self):
        return colors.PERFECT_BLUE

    def get_player_state(self):
        """returns: (state, anim_rate)"""
        if self.is_grounded() and (self._last_jump_time <= 1 or self.get_y_vel() > -0.1):
            if self.is_moving() or self.is_holding_left_or_right():
                if not self.is_crouching():
                    return spriteref.PlayerStates.WALKING
                else:
                    return spriteref.PlayerStates.CROUCH_WALKING
            else:
                if not self.is_crouching():
                    return spriteref.PlayerStates.IDLE
                else:
                    return spriteref.PlayerStates.CROUCH_IDLE

        elif (not self.is_left_walled() and not self.is_right_walled()) or not self.get_player_type().can_walljump():
            return spriteref.PlayerStates.AIRBORNE

        else:
            return spriteref.PlayerStates.WALLSLIDE

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
        self.do_death(DeathReason.CRUSHED)

    def do_death(self, reason, silent=False):
        player_id = self.get_player_type().get_id()
        if not silent:
            cx, cy = self.get_center()
            for i in range(0, spriteref.object_sheet().num_broken_player_parts(player_id)):
                self.get_world().add_entity(PlayerBodyPartParticle(cx, cy, player_id, i))
        self.get_world().remove_entity(self)
        # TODO tell gs or someone we died?
        print("INFO: player {} was {}.".format(player_id, reason))

    def __repr__(self):
        return "{}({}, {})".format(type(self).__name__, self.get_player_type().get_id(), self.get_rect())


class DeathReason:
    CRUSHED = "crushed"
    UNKNOWN = "killed by the guardians"


class ParticleEntity(Entity):

    def __init__(self, x, y, w, h, vel, duration=-1, initial_phasing=-1):
        Entity.__init__(self, x, y, w, h)
        self._x_vel = vel[0]
        self._y_vel = vel[1]
        self._initial_phasing = initial_phasing
        self._duration = duration
        self._ticks_alive = 0

        self._gravity = 0.15
        self._bounciness = 0.8
        self._friction = 0.97

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

    def is_dynamic(self):
        return True

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

        if self._x_vel < -0.1:
            self._x_flip = True
        elif self._x_vel > 0.1:
            self._x_flip = False

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
                                         new_xflip=self._x_flip)

    def all_sprites(self):
        for spr in super().all_sprites():
            yield spr
        if self._img is not None:
            yield self._img


class PlayerBodyPartParticle(ParticleEntity):

    def __init__(self, x, y, player_id, part_idx):
        cs = gs.get_instance().cell_size
        initial_vel = (-0.75 + 1.5 * random.random(), -(1.5 + 1 * random.random()))
        ParticleEntity.__init__(self, x, y, cs // 5, cs // 5, initial_vel, duration=60 * 5, initial_phasing=20)

        self.player_id = player_id
        self.part_idx = part_idx

        self.rotation = random.random()
        self.rotation_vel = 0.05 + random.random() * 0.1
        self.rotation_decay = 0.985

    def update(self):
        super().update()

        if self.rotation_vel < 0.01:
            self.rotation_vel = 0
        else:
            self.rotation -= self.rotation_vel
            self.rotation_vel *= self.rotation_decay

    def get_sprite(self):
        return spriteref.object_sheet().get_broken_player_sprite(self.player_id, self.part_idx, rotation=self.rotation)


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

    SLOPE_BLOCK_HORZ = CollisionMask("slope_block_horz", render_depth=25)
    SLOPE_BLOCK_VERT = CollisionMask("slope_block_vert", render_depth=25)

    ACTOR = CollisionMask("actor", render_depth=10)

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

    def get_resolution_hint(self):
        return self._resolution_hint

    def collides_with(self, other: 'PolygonCollider'):
        return self.collides_with_mask(other.get_mask())

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


