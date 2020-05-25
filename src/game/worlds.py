
import typing

import src.utils.util as util

import src.game.globalstate as gs
import src.game.entities as entities


class World:

    def __init__(self):
        self.entities = set()    # set of entities in world
        self._to_add = set()     # set of new entities to add next frame
        self._to_remove = set()  # set of entities to remove next frame

        self._sensor_states = {}  # sensor_id -> list of entities

    @staticmethod
    def new_test_world_old():
        res = World()
        cs = gs.get_instance().cell_size
        res.add_entity(entities.BlockEntity(cs * 4, cs * 11, cs * 15, cs * 1), next_update=False)
        res.add_entity(entities.BlockEntity(cs * 9, cs * 10, cs * 2, cs * 1), next_update=False)
        res.add_entity(entities.BlockEntity(cs * 5, cs * 7, cs * 0.5, cs * 4), next_update=False)
        res.add_entity(entities.BlockEntity(cs * 0, cs * 7, cs * 5, cs * 1), next_update=False)

        res.add_entity(entities.BlockEntity(cs * 21, cs * 3, cs * 0.5, cs * 4), next_update=False)
        res.add_entity(entities.BlockEntity(cs * 21.5, cs * 3, cs * 2, cs * 2), next_update=False)

        res.add_entity(entities.SlopeBlockEntity(cs * 11, cs * 10, entities.SlopeBlockEntity.UPWARD_LEFT_2x1,
                                                 triangle_scale=cs), next_update=False)
        res.add_entity(entities.SlopeBlockEntity(cs * 7, cs * 10, entities.SlopeBlockEntity.UPWARD_RIGHT_2x1,
                                                 triangle_scale=cs), next_update=False)

        pts = [(10 * cs, 6 * cs), (16 * cs, 6 * cs), (16 * cs, 10 * cs), (16 * cs, 10 * cs)]
        moving_block = entities.MovingBlockEntity(cs * 2, cs * 1, pts)
        res.add_entity(moving_block, next_update=False)

        res.add_entity(entities.PlayerEntity(cs * 6, cs * 5), next_update=False)

        return res

    @staticmethod
    def new_test_world():
        res = World()
        cs = gs.get_instance().cell_size

        res.add_entity(entities.PlayerEntity(cs * 12, cs * 11), next_update=False)

        rects = [(0, 0, 2, 5),
                 (0, 5, 2, 3),
                 (0, 8, 7, 1),
                 (0, 9, 2, 4),
                 (0, 13, 7, 2),
                 (7, 14, 10, 1),    # floor
                 (4, 11, 3, 2),

                 (9, 7, 2, 1),     # floating platform
                 (17, 7, 2, 1),
                 (19, 6, 4, 1),
                 (15, 10, 2, 1),

                 (2, 0, 4, 2),      # ciel
                 (6, 0, 19, 3),
                 (25, 0, 5, 4),

                 (13, 7, 2, 3),
                 (17, 14.5, 2, 0.5),
                 (19, 11, 2, 4),
                 (23, 10, 2, 5),
                 (21, 14, 2, 1),
                 (25, 7, 2, 6),
                 (25, 13, 4, 2),
                 (27, 12, 2, 1),
                 (29, 4, 1, 11)
                 ]

        for r in rects:
            res.add_entity(entities.BlockEntity(cs * r[0], cs * r[1], cs * r[2], cs * r[3]), next_update=False)

        slopes = [(17, 6, entities.SlopeBlockEntity.UPWARD_RIGHT_2x1),
                  (4, 2, entities.SlopeBlockEntity.DOWNWARD_RIGHT_2x1)]

        for s in slopes:
            res.add_entity(entities.SlopeBlockEntity(s[0] * cs, s[1] * cs, s[2], triangle_scale=cs))

        composites = [((14, 10, 1, 2), (13, 10, entities.SlopeBlockEntity.DOWNWARD_RIGHT_1x2))]

        for comp in composites:
            blocks = []
            for spec in comp:
                if len(spec) == 4:
                    r = spec
                    blocks.append(entities.BlockEntity(cs * r[0], cs * r[1], cs * r[2], cs * r[3]))
                else:
                    s = spec
                    blocks.append(entities.SlopeBlockEntity(s[0] * cs, s[1] * cs, s[2], triangle_scale=cs))
            res.add_entity(entities.CompositeBlockEntity(blocks))

        return res

    def add_entity(self, ent, next_update=True):
        if ent is None or ent in self.entities or ent in self._to_add:
            raise ValueError("can't add entity, either because it's None or it's already in world: {}".format(ent))
        elif next_update:
            self._to_add.add(ent)
        else:
            self.entities.add(ent)
            ent.world = self

    def update(self):
        for ent in self._to_add:
            if ent not in self._to_remove:
                self.entities.add(ent)
                ent.world = self
        self._to_add.clear()

        for ent in self._to_remove:
            if ent in self.entities:
                self.entities.remove(ent)
                ent.world = None
        self._to_remove.clear()

        dyna_ents = [e for e in self.all_dynamic_entities()]

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

        if len(invalids) > 0:
            print("WARN: failed to solve collisions with: {}".format(invalids))
            for i in invalids:
                i.set_vel((0, 0))

    def all_entities(self, cond=None) -> typing.Iterable[entities.Entity]:
        for e in self.entities:
            if cond is None or cond(e):
                yield e

    def get_player(self):
        for e in self.entities:
            if isinstance(e, entities.PlayerEntity):
                return e
        return None

    def all_dynamic_entities(self, cond=None) -> typing.Iterable[entities.Entity]:
        for e in self.all_entities(cond=lambda _e: _e.is_dynamic() and (cond is None or cond(_e))):
            yield e

    def get_sensor_state(self, sensor_id):
        if sensor_id not in self._sensor_states:
            return []
        else:
            return self._sensor_states[sensor_id]


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
        all_blocks = CollisionResolver.get_all_relevant_blocks(world, dyna_ents)
        for ent in dyna_ents:
            CollisionResolver._solve_pre_move_collisions(world, ent, start_positions, all_blocks)

        for ent in dyna_ents:
            CollisionResolver._try_to_move(world, ent, start_positions, next_positions, all_blocks)

    @staticmethod
    def _solve_pre_move_collisions(world, dyna_ent, start_positions, all_blocks):
        """
        make sure we're in a valid position before we even start moving
            returns: valid (x, y) for dyna_ent
        """
        start_positions[dyna_ent] = CollisionResolver._find_nearest_valid_position(world, dyna_ent,
                                                                                   start_positions[dyna_ent],
                                                                                   all_blocks)

    @staticmethod
    def _shift_until_blocked(world, dyna_ent, start_xy, end_xy, all_blocks):
        dx = end_xy[0] - start_xy[0]
        dy = end_xy[1] - start_xy[1]
        if dx == 0 and dy == 0:
            return start_xy
        steps = max(abs(dx), abs(dy))
        best = start_xy
        for i in range(1, steps + 1):
            x = start_xy[0] + int((dx * i / steps))
            y = start_xy[1] + int((dy * i / steps))
            if len(CollisionResolver._get_blocked_solid_colliders(dyna_ent, (x, y), all_blocks)) == 0:
                best = (x, y)
            else:
                break
        return best

    @staticmethod
    def _try_to_move(world, dyna_ent, start_positions, next_positions, all_blocks):
        if start_positions[dyna_ent] is None:
            next_positions[dyna_ent] = None
        elif start_positions[dyna_ent] == next_positions[dyna_ent]:
            pass  # we already know the next position is valid
        else:
            target_xy = next_positions[dyna_ent]
            next_xy = CollisionResolver._find_nearest_valid_position(world, dyna_ent, target_xy, all_blocks)
            next_positions[dyna_ent] = next_xy

    @staticmethod
    def _find_nearest_valid_position(world, dyna_ent, target_xy, all_blocks):

        blocked_colliders_cache = {}  # xy -> list of colliders

        def _get_blocked_colliders(xy):
            if xy not in blocked_colliders_cache:
                blocked_colliders_cache[xy] = CollisionResolver._get_blocked_solid_colliders(dyna_ent, xy, all_blocks)
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
            allow_horz, allow_vert = _allow_shift_from(xy)
            if allow_horz:
                yield (xy[0] - 1, xy[1])
                yield (xy[0] + 1, xy[1])
            if allow_vert:
                yield (xy[0], xy[1] - 1)
                yield (xy[0], xy[1] + 1)

        def is_correct(xy):
            return len(_get_blocked_colliders(xy)) == 0

        def get_cost(xy):
            dx = abs(xy[0] - target_xy[0])
            dy = abs(xy[1] - target_xy[1])
            return ((dx * dx + dy * dy), dx)  # closest points first, then break ties by preferring y shifts

        return util.bfs(target_xy, is_correct, get_neighbors, get_cost=get_cost, limit=100)

    @staticmethod
    def _get_blocked_solid_colliders(ent, xy, all_blocks) -> typing.List[entities.PolygonCollider]:
        """
        returns: list of ent's solid colliders that are colliding with at least one block
        """
        res = []
        for collider in ent.all_colliders(solid=True):
            if CollisionResolver._is_colliding_with_any_blocks(ent, collider, xy, all_blocks):
                res.append(collider)
        return res

    @staticmethod
    def _is_colliding_with_any_blocks(ent, collider, xy, all_blocks) -> bool:
        # TODO - some pre-filtering based on AABB
        for b in all_blocks:
            for b_collider in b.all_colliders(solid=True):
                if collider.is_colliding_with(xy, b_collider, b.get_xy()):
                    collider.is_colliding_with(xy, b_collider, b.get_xy())
                    return True
        return False

    @staticmethod
    def get_all_relevant_blocks(world, dyna_ents, sloped_filter=None, moving_filter=None):
        must_be_sloped = sloped_filter is True
        must_not_be_sloped = sloped_filter is False

        must_be_moving = moving_filter is True
        must_not_be_moving = moving_filter is False

        res = []
        for b in world.all_entities(cond=lambda _e: isinstance(_e, entities.AbstractBlockEntity)):
            for b2 in b.all_blocks(recurse=True):
                is_moving = isinstance(b2, entities.MovingBlockEntity)
                if (is_moving and must_not_be_moving) or (not is_moving and must_be_moving):
                    continue

                is_sloped = isinstance(b2, entities.SlopeBlockEntity)
                if (is_sloped and must_not_be_sloped) or (not is_sloped and must_be_sloped):
                    continue

                res.append(b2)
        return res

    @staticmethod
    def calc_sensor_states(world, dyna_ents):
        # TODO - this assumes we only care about sensing blocks
        all_blocks = CollisionResolver.get_all_relevant_blocks(world, dyna_ents)
        res = {}
        for ent in dyna_ents:
            ent_xy = ent.get_xy()
            for c in ent.all_colliders(sensor=True):
                c_state = []
                for b in all_blocks:
                    if any(c.is_colliding_with(ent_xy, b_collider, b.get_xy()) for b_collider in b.all_colliders(solid=True)):
                        c_state.append(b)
                res[c.get_id()] = c_state

        CollisionResolver._calc_slope_sensor_states(world, dyna_ents, res)

        return res

    @staticmethod
    def activate_snap_sensors_if_necessary(world, dyna_ents):
        # TODO - this assumes we only care about sensing blocks
        all_blocks = CollisionResolver.get_all_relevant_blocks(world, dyna_ents)

        for ent in dyna_ents:
            ent_xy = ent.get_xy()
            should_snap_down = False
            snap_dist = 0

            for c in ent.all_colliders(sensor=True):
                if c.get_mask() != entities.CollisionMasks.SNAP_DOWN_SENSOR:
                    continue
                for b in all_blocks:
                    if any(c.is_colliding_with(ent_xy, b_collider, b.get_xy()) for b_collider in b.all_colliders(solid=True)):
                        should_snap_down = True
                        snap_dist = max(snap_dist, c.get_rect()[3])

            if should_snap_down and snap_dist > 0:
                snap_xy = (ent_xy[0], ent_xy[1] + snap_dist)
                new_xy = CollisionResolver._shift_until_blocked(world, ent, ent_xy, snap_xy, all_blocks)
                if new_xy != ent_xy:
                    ent.set_y_vel(0)
                    ent.set_y(new_xy[1])

    @staticmethod
    def _calc_slope_sensor_states(world, dyna_ents, res):
        all_blocks = CollisionResolver.get_all_relevant_blocks(world, dyna_ents, sloped_filter=True)
        for ent in dyna_ents:
            ent_xy = ent.get_xy()
            for c in ent.all_colliders(sensor=True):
                c_state = [] if c.get_id() not in res else res[c.get_id()]
                for b in all_blocks:
                    if any(c.is_colliding_with(ent_xy, b_collider, b.get_xy()) for b_collider in b.all_colliders(solid=True)):
                        c_state.append(b)
                res[c.get_id()] = c_state

