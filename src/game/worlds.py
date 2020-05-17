
import typing
import math

import src.utils.util as util
import src.engine.globaltimer as globaltimer

import src.game.globalstate as gs
import src.game.entities as entities


class World:

    def __init__(self):
        self.entities = set()    # set of entities in world
        self._to_add = set()     # set of new entities to add next frame
        self._to_remove = set()  # set of entities to remove next frame

    @staticmethod
    def new_test_world():
        res = World()
        cs = gs.get_instance().cell_size
        res.add_entity(entities.BlockEntity(cs * 4, cs * 11, cs * 15, cs * 1), next_update=False)
        res.add_entity(entities.BlockEntity(cs * 9, cs * 10, cs * 2, cs * 1), next_update=False)

        pts = [(10 * cs, 6 * cs), (16 * cs, 6 * cs), (16 * cs, 10 * cs)]
        moving_block = entities.MovingBlockEntity(cs * 2, cs * 1, pts)
        res.add_entity(moving_block, next_update=False)

        res.add_entity(entities.PlayerEntity(cs * 6, cs * 5), next_update=False)

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

        for ent in self.entities:
            ent.update()

        dyna_ents = [e for e in self.all_dynamic_entities()]

        phys_groups = {}
        for e in dyna_ents:
            if e.get_physics_group() not in phys_groups:
                phys_groups[e.get_physics_group()] = []
            phys_groups[e.get_physics_group()].append(e)

        ordered_phys_groups = [group_key for group_key in phys_groups]
        ordered_phys_groups.sort()

        invalids = []

        for group_key in ordered_phys_groups:
            group_ents = phys_groups[group_key]
            new_invalids = CollisionResolver.move_dynamic_entities_and_resolve_collisions(self, group_ents)
            invalids.extend(new_invalids)

        if len(invalids) > 0:
            print("WARN: failed to solve collisions with: {}".format(invalids))

    def all_entities(self, cond=None) -> typing.Iterable[entities.Entity]:
        for e in self.entities:
            if cond is None or cond(e):
                yield e

    def all_dynamic_entities(self, cond=None) -> typing.Iterable[entities.Entity]:
        for e in self.all_entities(cond=lambda _e: _e.is_dynamic() and (cond is None or cond(_e))):
            yield e

    def all_sprites(self):
        for ent in self.entities:
            for spr in ent.all_sprites():
                yield spr

    def all_debug_sprites(self):
        for ent in self.entities:
            for spr in ent.all_debug_sprites():
                yield spr


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
                invalids.append(ent)

        return invalids

    @staticmethod
    def _solve_all_collisions(world, dyna_ents, start_positions, next_positions):
        all_blocks = [b for b in world.all_entities(cond=lambda _e: isinstance(_e, entities.BlockEntity))]
        for ent in dyna_ents:
            CollisionResolver._solve_pre_move_collisions(world, ent, start_positions, all_blocks)

        for ent in dyna_ents:
            CollisionResolver._try_to_move(world, ent, start_positions, next_positions, all_blocks)

        for ent in dyna_ents:
            if next_positions[ent] is not None:
                ent.set_xy(next_positions[ent])

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

        return util.Utils.bfs(target_xy, is_correct, get_neighbors, get_cost=get_cost, limit=100)

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
                    return True
        return False

