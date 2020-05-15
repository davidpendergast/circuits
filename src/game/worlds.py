
import typing
import math

import src.utils.util as util

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

        invalids = CollisionResolver.move_dynamic_entities_and_resolve_collisions(self, dyna_ents)

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
        # highest priority first
        dyna_ents.sort(key=lambda e: e.get_collision_priority(), reverse=True)

        start_positions = {}
        next_positions = {}
        for ent in dyna_ents:
            start_positions[ent] = ent.get_xy()
            next_positions[ent] = ent.calc_next_xy()

        CollisionResolver._solve_all_collisions(world, dyna_ents, start_positions, next_positions)

        invalids = []

        for ent in dyna_ents:
            if next_positions[ent] is not None:
                ent.set_xy(next_positions[ent])
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
            # TODO - pixel-by-pixel search
            target_xy = next_positions[dyna_ent]
            next_xy = CollisionResolver._find_nearest_valid_position(world, dyna_ent, target_xy, all_blocks)
            if next_xy is not None:
                if ((next_xy[0] < target_xy[0] and dyna_ent.get_vel()[0] > 0)  # TODO - hack
                        or (next_xy[0] > target_xy[0] and dyna_ent.get_vel()[0] < 0)):
                    dyna_ent.set_x_vel(0)
                if ((next_xy[1] < target_xy[1] and dyna_ent.get_vel()[1] > 0)
                        or (next_xy[1] > target_xy[1] and dyna_ent.get_vel()[1] < 0)):
                    dyna_ent.set_y_vel(0)

            next_positions[dyna_ent] = next_xy

    @staticmethod
    def _find_nearest_valid_position(world, dyna_ent, target_xy, all_blocks):
        for xy in CollisionResolver._neighboring_positions_to_check(target_xy, 100):
            if not CollisionResolver._has_contact(dyna_ent, xy, all_blocks):
                return xy
        return None

    @staticmethod
    def _neighboring_positions_to_check(start_xy, n_points=100):
        yield start_xy

        already_checked = set()
        already_checked.add(start_xy)

        # TODO this spiral strategy is so janky
        # plot x=(0.75 + 0.25 * t^0.75)*cos(t), y=(0.75 + 0.25 *  t^0.75)*sin(t) from t=0 to100

        t = 0
        while len(already_checked) < n_points:
            dx = (0.75 + 0.25 * t ** 0.75) * math.cos(t)
            dy = (0.75 + 0.25 * t ** 0.75) * math.sin(t)
            pt = (round(start_xy[0] + dx), round(start_xy[1] + dy))
            if pt not in already_checked:
                yield pt
                already_checked.add(pt)
            t += 1

    @staticmethod
    def _has_contact(ent, xy, all_blocks):
        for b in all_blocks:
            ent_rect = ent.get_rect()
            ent_rect_for_xy = [xy[0], xy[1], ent_rect[2], ent_rect[3]]
            if util.Utils.get_rect_intersect(b.get_rect(), ent_rect_for_xy) is not None:
                for collider in ent.all_colliders():
                    for b_collider in b.all_colliders():
                        if collider.is_colliding_with(xy, b_collider, b.get_xy()):
                            return True
        return False

