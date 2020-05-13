
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

    def all_sprites(self):
        for ent in self.entities:
            for spr in ent.all_sprites():
                yield spr

    def all_debug_sprites(self):
        for ent in self.entities:
            for spr in ent.all_debug_sprites():
                yield spr
