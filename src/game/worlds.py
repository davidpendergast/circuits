
import src.game.globalstate as gs
import src.game.spriteref as spriteref
import src.game.colors as colors

import src.engine.sprites as sprites


class World:

    def __init__(self):
        self.entities = set()    # set of entities in world
        self._to_add = set()     # set of new entities to add next frame
        self._to_remove = set()  # set of entities to remove next frame

    @staticmethod
    def new_test_world():
        res = World()
        res.add_entity(BlockEntity(4, 4, 3, 1), next_update=False)

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


_ENT_ID = 0

def next_entity_id():
    global _ENT_ID
    _ENT_ID = _ENT_ID + 1
    return _ENT_ID - 1


class Entity:

    def __init__(self, x=0, y=0, w=0, h=0):
        self._ent_id = next_entity_id()
        self._rect = [x, y, w, h]
        self._colliders = []

        self.world = None  # world updates this when entity is added / removed

    def get_world(self):
        return self.world

    def get_rect(self):
        return self._rect

    def get_x(self):
        return self._rect[0]

    def get_y(self):
        return self._rect[1]

    def get_w(self):
        return self._rect[2]

    def get_h(self):
        return self._rect[3]

    def update(self):
        pass

    def all_sprites(self):
        return []

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

    def __init__(self, x, y, grid_w, grid_h):
        cell_size = gs.get_instance().cell_size
        Entity.__init__(self, x=x, y=y, w=grid_w * cell_size, h=grid_h * cell_size)

        self._rect_sprite = None

    def update(self):
        if self._rect_sprite is None:
            self._rect_sprite = sprites.RectangleSprite(spriteref.POLYGON_LAYER, 0, 0, 0, 0)
        self._rect_sprite = self._rect_sprite.update(new_x=self.get_x(), new_y=self.get_y(),
                                                     new_w=self.get_w(), new_h=self.get_h(),
                                                     new_color=colors.DARK_GRAY, new_depth=10)

    def all_sprites(self):
        if gs.get_instance().debug_render:
            yield self._rect_sprite
        else:
            return []


class CollisionMask:

    def __init__(self, name, collides_with=()):
        self._name = name
        self._collides_with = collides_with

    def get_name(self) -> str:
        return self._name

    def collides_with(self, mask) -> bool:
        if mask is None:
            return False
        else:
            return mask.get_name() in self._collides_with


class CollisionMasks:

    BLOCK = CollisionMask("block")
    ACTOR = CollisionMask("actor", collides_with=("block"))


class Collider:

    def __init__(self, mask=None, dynamic=True):
        self._mask = mask
        self._dynamic = dynamic

    def get_mask(self):
        return self._mask

    def is_dynamic(self):
        return self._dynamic

    def get_points(self, offs=(0, 0)):
        return []
