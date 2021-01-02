
import typing

import configs
import src.utils.util as util
import src.game.const as const

import src.game.globalstate as gs
import src.game.entities as entities
import src.engine.keybinds as keybinds
import src.engine.inputs as inputs
import src.game.playertypes as playertypes


class World:

    def __init__(self, bp=None):
        self.entities = set()    # set of entities in world
        self._to_add = set()     # set of new entities to add next frame
        self._to_remove = set()  # set of entities to remove next frame

        self._game_state = None

        self._sensor_states = {}  # sensor_id -> list of entities

        # regular hashing
        self._ent_id_to_ent = {}  # ent_id -> entity

        # spacial hashing
        self._entities_to_cells = {}  # ent -> set of cells (x, y) it's inside
        self._cells_to_entities = {}   # (x, y) - set of entities inside

        self._light_sources = util.SpacialHashMap(gs.get_instance().cell_size * 5)

        self.camera_min_xy = [None, None]
        self.camera_max_xy = [None, None]

        self.safe_zones = []  # list of rects that are safe for actors to be in. if empty, the entire world is safe
        self.kill_zones = []  # list of rects that kill actors when they enter (overriding safe zones)

        self._orig_blueprint = bp

        self._tick = 0

    def set_game_state(self, game_state):
        self._game_state = game_state

    def get_game_state(self) -> 'src.menus._GameState':
        return self._game_state

    def set_safe_zones(self, safe_zones, kill_zones=()):
        self.safe_zones = safe_zones
        self.kill_zones = util.listify(kill_zones)

    def set_camera_bounds(self, camera_min_xy, camera_max_xy):
        self.camera_min_xy = camera_min_xy
        self.camera_max_xy = camera_max_xy

    def has_entity(self, ent):
        return ent.get_ent_id() in self._ent_id_to_ent

    def add_entity(self, ent, next_update=True):
        if ent is None or ent in self.entities:
            raise ValueError("can't add entity, either because it's None or it's already in world: {}".format(ent))
        elif next_update:
            self._to_add.add(ent)
        else:
            self.entities.add(ent)
            self.rehash_entity(ent)
            self._ent_id_to_ent[ent.get_ent_id()] = ent
            ent.set_world(self)

    def remove_entity(self, ent, next_update=True):
        if ent is None:
            return
        elif next_update:
            self._to_remove.add(ent)
        else:
            ent.about_to_remove_from_world()
            self.entities.remove(ent)
            self._unhash(ent)
            del self._ent_id_to_ent[ent.get_ent_id()]
            ent.set_world(None)

    def rehash_entity(self, ent):
        rect = ent.get_rect()

        cells_inside = set()
        for cell in self.all_cells_in_rect(rect):
            cells_inside.add(cell)

        old_cells = set() if not ent in self._entities_to_cells else self._entities_to_cells[ent]
        if cells_inside == old_cells:
            return  # no change

        if ent in self._entities_to_cells:
            for old_cell in self._entities_to_cells[ent]:
                if old_cell not in cells_inside:
                    if old_cell in self._cells_to_entities and ent in self._cells_to_entities[old_cell]:
                        self._cells_to_entities[old_cell].remove(ent)
                        if len(self._cells_to_entities[old_cell]) == 0:
                            del self._cells_to_entities[old_cell]

        self._entities_to_cells[ent] = cells_inside
        for cell in cells_inside:
            if cell not in self._cells_to_entities:
                self._cells_to_entities[cell] = set()
            self._cells_to_entities[cell].add(ent)

        # for debug
        # sorted_cells = [c for c in cells_inside]
        # sorted_cells.sort()
        # print("INFO: rehashed! {} is inside the cells: {}".format(ent, sorted_cells))

    def _unhash(self, ent):
        if ent in self._entities_to_cells:
            for cell in self._entities_to_cells[ent]:
                if cell in self._cells_to_entities and ent in self._cells_to_entities[cell]:
                    self._cells_to_entities[cell].remove(ent)
                    if len(self._cells_to_entities[cell]) == 0:
                        del self._cells_to_entities[cell]
            del self._entities_to_cells[ent]

    def all_cells_in_rect(self, rect):
        cs = gs.get_instance().cell_size
        if rect[2] <= 0 or rect[3] <= 0:
            return []
        start_cell = (rect[0] // cs, rect[1] // cs)
        end_cell = ((rect[0] + rect[2] - 1) // cs, (rect[1] + rect[3] - 1) // cs)
        for x in range(start_cell[0], end_cell[0] + 1):
            for y in range(start_cell[1], end_cell[1] + 1):
                yield (x, y)

    def _do_debug_player_type_toggle(self):
        cur_player = self.get_player()
        if cur_player is None:
            return
        else:
            ptype = cur_player.get_player_type()
            all_types = [t for t in playertypes.PlayerTypes.all_types()]
            if ptype in all_types:
                idx = all_types.index(ptype)
                next_type = all_types[(idx + 1) % len(all_types)]
            else:
                next_type = all_types[0]

            gs.get_instance().player_type_override = next_type  # new levels will get this player type too

            cur_x, cur_y = cur_player.get_xy()
            new_player = entities.PlayerEntity(cur_x, cur_y, next_type,
                                               align_to_cells=False,
                                               controller=cur_player.get_controller())
            new_player.set_y(cur_y + cur_player.get_h() - new_player.get_h())  # keep feet position the same

            self.remove_entity(cur_player)
            self.add_entity(new_player)

    def handle_debug_commands(self):
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.TOGGLE_PLAYER_TYPE)):
            self._do_debug_player_type_toggle()

    def get_blueprint(self):
        return self._orig_blueprint

    def get_start_block(self, player_type):
        for b in self.all_entities(lambda ent: ent.is_start_block()):
            if b.get_player_type() == player_type:
                return b
        return None

    def get_end_blocks(self, player_type):
        for b in self.all_entities(lambda ent: ent.is_end_block()):
            if b.get_player_type() == player_type:
                yield b

    def get_entity_by_id(self, ent_id):
        if ent_id in self._ent_id_to_ent:
            return self._ent_id_to_ent[ent_id]

    def get_player_start_position(self, player):
        player_type = player.get_player_type()
        start_block = self.get_start_block(player_type)
        if start_block is None:
            print("WARN: no start block for player type: {}".format(player_type))
            return (0, 0)
        else:
            block_rect = start_block.get_rect()
            x = block_rect[0] + block_rect[2] // 2 - player.get_w() // 2
            y = block_rect[1] - player.get_h()
            return (x, y)

    def all_light_sources_at_pt(self, pt, check_circle_collision=True):
        """yields: ((x, y), radius, color, strength) for each light source that may reach the given position."""
        for item in self._light_sources.all_items_at_point(pt):
            center, radius, color, strength = item[2]
            if check_circle_collision:
                if not util.circle_contains(center, radius, pt):
                    continue
            yield (center, radius, color, strength)

    def get_tick(self):
        return self._tick

    def update(self):
        if configs.is_dev:
            self.handle_debug_commands()

        for ent in self._to_add:
            if ent not in self._to_remove:
                self.add_entity(ent, next_update=False)
        self._to_add.clear()

        for ent in self._to_remove:
            if ent in self.entities:
                self.remove_entity(ent, next_update=False)
        self._to_remove.clear()

        dyna_ents = [e for e in self.all_entities(cond=lambda _e: _e.is_dynamic())]

        phys_groups = {}
        for e in dyna_ents:
            if e.get_physics_group() not in phys_groups:
                phys_groups[e.get_physics_group()] = []
            phys_groups[e.get_physics_group()].append(e)

        for ent in self.entities:
            ent.update()

        ordered_phys_groups = [group_key for group_key in phys_groups]
        ordered_phys_groups.sort()

        invalids = []

        for group_key in ordered_phys_groups:
            group_ents = phys_groups[group_key]
            new_invalids = CollisionResolver.move_dynamic_entities_and_resolve_collisions(self, group_ents)
            invalids.extend(new_invalids)

        if entities.ACTOR_GROUP in phys_groups:
            actor_ents = phys_groups[entities.ACTOR_GROUP]
            CollisionResolver.activate_snap_sensors_if_necessary(self, actor_ents)

        self._sensor_states.clear()

        if entities.ACTOR_GROUP in phys_groups:
            actor_ents = phys_groups[entities.ACTOR_GROUP]
            new_sensor_states = CollisionResolver.calc_sensor_states(self, actor_ents)
            self._sensor_states.update(new_sensor_states)

            for actor in actor_ents:
                actor.update_frame_of_reference_parent()

        if len(self.safe_zones) > 0 or len(self.kill_zones) > 0:
            if entities.ACTOR_GROUP in phys_groups:
                for actor in phys_groups[entities.ACTOR_GROUP]:
                    c_xy = actor.get_center()
                    actor_oob = False
                    for kill_rect in self.kill_zones:
                        if util.rect_contains(kill_rect, c_xy):
                            actor_oob = True
                            break
                    if not actor_oob:
                        any_safe_zone_contains = False
                        for safe_rect in self.safe_zones:
                            if util.rect_contains(safe_rect, c_xy):
                                any_safe_zone_contains = True
                                break
                        if len(self.safe_zones) > 0 and not any_safe_zone_contains:
                            actor_oob = True
                    if actor_oob:
                        actor.fell_out_of_bounds()

        if len(invalids) > 0:
            print("WARN: failed to solve collisions with: {}".format(invalids))
            for i in invalids:
                i.set_vel((0, 0))
                i.was_crushed()

        self._light_sources.clear()
        for ent in self.entities:
            n = 0
            for light_src in ent.get_light_sources():
                if not isinstance(light_src, tuple) or len(light_src) != 4:
                    raise ValueError("Invalid light source on entity {}: {}".format(ent, light_src))
                else:
                    xy, radius, color, strength = light_src
                    self._light_sources.put("{}_{}".format(ent.get_ent_id(), n),
                                            [xy[0] - radius, xy[1] - radius, radius * 2, radius * 2],
                                            (xy, radius, color, strength))

        for ent in self.entities:
            ent.update_sprites()

            # TODO kinda weird to do this here?
            if ent.is_player():
                ent.handle_death_if_necessary()

        if self.get_game_state() is not None and self.get_game_state().get_status().world_ticks_inc:
            self._tick += 1

    def all_entities(self, cond=None) -> typing.Iterable[entities.Entity]:
        for e in self.entities:
            if cond is None or cond(e):
                yield e

    def all_entities_in_cells(self, cells, cond=None):
        res = set()
        rejected = set()
        for c in cells:
            if c in self._cells_to_entities:
                for ent in self._cells_to_entities[c]:
                    if ent in rejected:
                        # only want to test condition once per entity
                        continue
                    elif cond is not None and not cond(ent):
                        rejected.add(ent)
                    else:
                        res.add(ent)
        return res

    def all_entities_in_rect(self, rect, cond=None) -> typing.Iterable[entities.Entity]:
        """returns: all entities that are in the cells that rect contains"""
        cells = [c for c in self.all_cells_in_rect(rect)]
        return self.all_entities_in_cells(cells, cond=cond)

    def get_player(self, must_be_active=True, with_type=None) -> entities.PlayerEntity:
        for e in self.entities:
            if isinstance(e, entities.PlayerEntity):
                if must_be_active and not e.is_active():
                    continue
                elif with_type is not None and e.get_player_type() != with_type:
                    continue
                else:
                    return e
        return None

    def get_sensor_state(self, sensor_id) -> typing.List[entities.Entity]:
        if sensor_id not in self._sensor_states:
            return []
        else:
            # the entity could have died and been removed since the sensor state was calculated
            return [e for e in self._sensor_states[sensor_id] if self.has_entity(e)]

    def is_door_unlocked(self, toggle_idx):
        for e in self.all_entities():
            if isinstance(e, entities.KeyEntity):
                if e.get_toggle_idx() == toggle_idx and e.is_satisfied():
                    return True
        return False

    def constrain_camera(self, worldview):
        if self.camera_min_xy[0] is not None:  # this will be none if the level is empty
            cam_rect = worldview.get_camera_rect_in_world()
            new_cam_xy = [None, None]
            if cam_rect[2] < self.camera_max_xy[0] - self.camera_min_xy[0]:
                if cam_rect[0] + cam_rect[2] > self.camera_max_xy[0]:
                    new_cam_xy[0] = self.camera_max_xy[0] - cam_rect[2]
                if cam_rect[0] < self.camera_min_xy[0]:
                    new_cam_xy[0] = self.camera_min_xy[0]
            else:
                # camera is too wide to fit within the bounds, so center it?
                new_cam_xy[0] = int((self.camera_max_xy[0] + self.camera_min_xy[0]) / 2 - cam_rect[2] / 2)

            if cam_rect[3] < self.camera_max_xy[1] - self.camera_min_xy[1]:
                if cam_rect[1] + cam_rect[3] > self.camera_max_xy[1]:
                    new_cam_xy[1] = self.camera_max_xy[1] - cam_rect[3]
                elif cam_rect[1] < self.camera_min_xy[1]:
                    new_cam_xy[1] = self.camera_min_xy[1]
            else:
                # camera is too tall to fit within the bounds, snap to top
                new_cam_xy[1] = self.camera_min_xy[1]

            worldview.set_camera_pos_in_world(new_cam_xy)


class _Contact:
    def __init__(self, collider1, xy1, collider2, xy2, overlap_rect):
        self.collider1 = collider1
        self.collider1_xy = xy1

        self.collider2 = collider2
        self.collider2_xy = xy2

        self.overlap_rect = overlap_rect


class CollisionResolver:

    @staticmethod
    def move_dynamic_entities_and_resolve_collisions(world, dyna_ents):
        start_positions = {}
        requested_next_positions = {}
        raw_requested_next_positions = {}
        next_positions = {}
        for ent in dyna_ents:
            start_positions[ent] = ent.get_xy(raw=False)
            requested_next_positions[ent] = ent.calc_next_xy(raw=False)
            raw_requested_next_positions[ent] = ent.calc_next_xy(raw=True)

            next_positions[ent] = requested_next_positions[ent]

        CollisionResolver._solve_all_collisions(world, dyna_ents, start_positions, next_positions)

        invalids = []

        for ent in dyna_ents:
            if next_positions[ent] is not None:
                raw_next_xy = raw_requested_next_positions[ent]

                if requested_next_positions[ent][0] == next_positions[ent][0]:
                    ent.set_x(raw_next_xy[0])
                else:
                    ent.set_x(next_positions[ent][0])

                    # something stopped us from moving horizontally
                    if (0 < ent.get_x_vel()) == (next_positions[ent][0] < requested_next_positions[ent][0]):
                        ent.set_x_vel(0)

                if requested_next_positions[ent][1] == next_positions[ent][1]:
                    ent.set_y(raw_next_xy[1])
                else:
                    ent.set_y(next_positions[ent][1])

                    # something stopped us from moving vertically
                    if (0 < ent.get_y_vel()) == (next_positions[ent][1] < requested_next_positions[ent][1]):
                        ent.set_y_vel(0)
            else:
                ent.set_vel((0, 0))
                invalids.append(ent)

        return invalids

    @staticmethod
    def _solve_all_collisions(world, dyna_ents, start_positions, next_positions):
        for ent in dyna_ents:
            CollisionResolver._solve_pre_move_collisions(world, ent, start_positions)

        for ent in dyna_ents:
            CollisionResolver._try_to_move(world, ent, start_positions, next_positions)

    @staticmethod
    def _solve_pre_move_collisions(world, dyna_ent, start_positions):
        """
        make sure we're in a valid position before we even start moving
            returns: valid (x, y) for dyna_ent
        """
        start_positions[dyna_ent] = CollisionResolver._find_nearest_valid_position(world,
                                                                                   dyna_ent,
                                                                                   start_positions[dyna_ent])

    @staticmethod
    def _shift_until_blocked(world, dyna_ent, start_xy, end_xy):
        dx = end_xy[0] - start_xy[0]
        dy = end_xy[1] - start_xy[1]
        if dx == 0 and dy == 0:
            return start_xy
        steps = max(abs(dx), abs(dy))
        best = start_xy

        for i in range(1, steps + 1):
            x = start_xy[0] + int((dx * i / steps))
            y = start_xy[1] + int((dy * i / steps))
            if len(CollisionResolver._get_blocked_solid_colliders(world, dyna_ent, (x, y))) == 0:
                best = (x, y)
            else:
                break
        return best

    @staticmethod
    def _try_to_move(world, dyna_ent, start_positions, next_positions):
        if start_positions[dyna_ent] is None:
            next_positions[dyna_ent] = None
        elif start_positions[dyna_ent] == next_positions[dyna_ent]:
            pass  # we already know the next position is valid
        else:
            target_xy = next_positions[dyna_ent]
            next_xy = CollisionResolver._find_nearest_valid_position(world, dyna_ent, target_xy)
            next_positions[dyna_ent] = next_xy

    @staticmethod
    def _find_nearest_valid_position(world, dyna_ent, target_xy, max_dist=10):
        blocked_colliders_cache = {}  # xy -> list of colliders

        def _get_blocked_colliders(xy):
            if xy not in blocked_colliders_cache:
                blocked_colliders_cache[xy] = CollisionResolver._get_blocked_solid_colliders(world, dyna_ent, xy)
            return blocked_colliders_cache[xy]

        def _allow_shift_from(xy):
            blocked_colliders = _get_blocked_colliders(xy)
            if len(blocked_colliders) == 0:
                return True, True  # i guess?
            else:
                allow_horz = False
                allow_vert = False

                for c in blocked_colliders:
                    if c.get_resolution_hint().allows_horz():
                        allow_horz = True
                    if c.get_resolution_hint().allows_vert():
                        allow_vert = True
                    if allow_horz and allow_vert:
                        break

                return allow_horz, allow_vert

        def get_neighbors(xy):
            yield (xy[0] - 1, xy[1])
            yield (xy[0] + 1, xy[1])
            yield (xy[0], xy[1] - 1)
            yield (xy[0], xy[1] + 1)

        def is_correct(xy):
            return len(_get_blocked_colliders(xy)) == 0

        def get_cost(xy):
            dx = abs(xy[0] - target_xy[0])
            dy = abs(xy[1] - target_xy[1])
            return ((dx * dx + dy * dy), dx)  # closest points first, then break ties by preferring y shifts

        res = None

        # if we're originally only colliding with vert-only or horz-only colliders, try to resolve
        # collisions just using x or y shifts, respectively
        allow_horz, allow_vert = _allow_shift_from(target_xy)
        if allow_horz and not allow_vert:
            res = util.bfs(target_xy, is_correct, lambda xy: [(xy[0] - 1, xy[1]), (xy[0] + 1, xy[1])],
                           get_cost=get_cost, limit=max_dist * 2)

        elif allow_vert and not allow_horz:
            res = util.bfs(target_xy, is_correct, lambda xy: [(xy[0], xy[1] - 1), (xy[0], xy[1] + 1)],
                           get_cost=get_cost, limit=max_dist * 2)

        # if that doesn't work, try all directions
        if res is None:
            res = util.bfs(target_xy, is_correct, get_neighbors, get_cost=get_cost, limit=max_dist * max_dist)

        return res

    @staticmethod
    def _get_blocked_solid_colliders(world, ent, xy) -> typing.List[entities.PolygonCollider]:
        """
        returns: list of ent's solid colliders that are colliding with at least one block
        """
        res = []
        for collider in ent.all_colliders(solid=True):
            if CollisionResolver._is_colliding_with_any_blocks(world, ent, collider, xy):
                res.append(collider)
        return res

    @staticmethod
    def _is_colliding_with_any_blocks(world, ent, collider, xy) -> bool:
        collider_rect = collider.get_rect(offs=xy)
        for b in world.all_entities_in_rect(collider_rect, cond=lambda _e: _e.is_block()):
            for b_collider in b.all_colliders(solid=True):
                if collider.is_colliding_with(xy, b_collider, b.get_xy()):
                    return True
        return False

    @staticmethod
    def calc_sensor_states(world, dyna_ents):
        res = {}
        for ent in dyna_ents:
            ent_xy = ent.get_xy()
            for c in ent.all_colliders(sensor=True):
                c_state = []
                c_rect = c.get_rect(offs=ent_xy)
                cares_about_blocks = c.collides_with_masks((entities.CollisionMasks.BLOCK,
                                                            entities.CollisionMasks.SLOPE_BLOCK_HORZ,
                                                            entities.CollisionMasks.SLOPE_BLOCK_VERT), any=True)
                cares_about_actors = c.collides_with_mask(entities.CollisionMasks.ACTOR)
                for b in world.all_entities_in_rect(c_rect, cond=lambda _e: (cares_about_blocks and _e.is_block()) or (cares_about_actors and _e.is_actor())):
                    if any(c.is_colliding_with(ent_xy, b_collider, b.get_xy()) for b_collider in b.all_colliders()):
                        c_state.append(b)

                res[c.get_id()] = c_state

        CollisionResolver._calc_slope_sensor_states(world, dyna_ents, res)

        return res

    @staticmethod
    def activate_snap_sensors_if_necessary(world, dyna_ents):
        for ent in dyna_ents:
            ent_xy = ent.get_xy()
            should_snap_down = False
            snap_dist = 0

            for c in ent.all_colliders(sensor=True):
                if c.get_mask() != entities.CollisionMasks.SNAP_DOWN_SENSOR:
                    continue
                c_rect = c.get_rect(offs=ent_xy)
                for b in world.all_entities_in_rect(c_rect, cond=lambda _e: _e.is_block()):
                    if any(c.is_colliding_with(ent_xy, b_collider, b.get_xy()) for b_collider in b.all_colliders(solid=True)):
                        should_snap_down = True
                        snap_dist = max(snap_dist, c.get_rect()[3])

            if should_snap_down and snap_dist > 0:
                snap_xy = (ent_xy[0], ent_xy[1] + snap_dist)
                new_xy = CollisionResolver._shift_until_blocked(world, ent, ent_xy, snap_xy)
                if new_xy != ent_xy:
                    ent.set_y_vel(0)
                    ent.set_y(new_xy[1])

    @staticmethod
    def _calc_slope_sensor_states(world, dyna_ents, res):
        for ent in dyna_ents:
            ent_xy = ent.get_xy()
            for c in ent.all_colliders(sensor=True):
                c_state = [] if c.get_id() not in res else res[c.get_id()]
                c_rect = c.get_rect(offs=ent_xy)
                for b in world.all_entities_in_rect(c_rect, cond=lambda _e: _e.is_block()):
                    if any(c.is_colliding_with(ent_xy, b_collider, b.get_xy()) for b_collider in b.all_colliders(solid=True)):
                        c_state.append(b)
                res[c.get_id()] = c_state

