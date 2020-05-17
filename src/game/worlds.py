
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

        moving_block = entities.MovingBlockEntity(cs * 16, cs * 6, cs * 2, cs * 1)
        moving_block.get_vel = lambda: (0, 2 * math.sin(globaltimer.tick_count() / 30))
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

        enviroment_ents = [e for e in dyna_ents if e.is_environment()]
        CollisionResolver.move_dynamic_entities_and_resolve_collisions(self, enviroment_ents)

        other_ents = [e for e in dyna_ents if not e.is_environment()]
        invalids = CollisionResolver.move_dynamic_entities_and_resolve_collisions(self, other_ents)

        if len(invalids) > 0:
            print("WARN: failed to solve collisions with: {}".format(invalids))

    def all_entities(self, cond=None) -> typing.Iterable[entities.Entity]:
        for e in self.entities:
            if cond is None or cond(e):
                yield e

    def all_dynamic_entities(self, cond=None) -> typing.Iterable[entities.DynamicEntity]:
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

        def get_neighbors(xy):
            for n in util.Utils.neighbors(xy[0], xy[1], and_diags=False):
                yield n

        def is_correct(xy):
            return not CollisionResolver._has_contact(dyna_ent, xy, all_blocks)

        def get_cost(xy):
            dx = abs(xy[0] - target_xy[0])
            dy = abs(xy[1] - target_xy[1])
            return ((dx * dx + dy * dy), dx)  # closest points first, then break ties by preferring y shifts

        return util.Utils.bfs(target_xy, is_correct, get_neighbors, get_cost=get_cost, limit=100)

    @staticmethod
    def _has_contact(ent, xy, all_blocks) -> bool:
        for b in all_blocks:
            ent_rect = ent.get_rect()
            ent_rect_for_xy = [xy[0], xy[1], ent_rect[2], ent_rect[3]]
            if util.Utils.get_rect_intersect(b.get_rect(), ent_rect_for_xy) is not None:
                for collider in ent.all_colliders():
                    for b_collider in b.all_colliders():
                        if collider.is_colliding_with(xy, b_collider, b.get_xy()):
                            return True
        return False

