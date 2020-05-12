
import src.game.globalstate as gs
import src.game.spriteref as spriteref
import src.game.colors as colors

import src.utils.util as util
import src.engine.sprites as sprites


class World:

    def __init__(self):
        self.entities = set()    # set of entities in world
        self._to_add = set()     # set of new entities to add next frame
        self._to_remove = set()  # set of entities to remove next frame

    @staticmethod
    def new_test_world():
        res = World()
        cs = gs.get_instance().cell_size
        res.add_entity(BlockEntity(cs * 4, cs * 11, cs * 15, cs * 1), next_update=False)
        res.add_entity(BlockEntity(cs * 9, cs * 10, cs * 2, cs * 1), next_update=False)

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


_ENT_ID = 0


def next_entity_id():
    global _ENT_ID
    _ENT_ID = _ENT_ID + 1
    return _ENT_ID - 1


class Entity:

    def __init__(self, x=0, y=0, w=0, h=0):
        self._ent_id = next_entity_id()
        self._rect = [x, y, w, h]

        self.world = None  # world sets this when entity is added / removed

        self._debug_sprites = {}

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

    def get_xy(self):
        return (self.get_x(), self.get_y())

    def get_size(self):
        return (self.get_w(), self.get_h())

    def update(self):
        pass

    def all_colliders(self):
        return []

    def all_sprites(self):
        return []

    def all_debug_sprites(self):
        main_rect_key = "main_rect"
        if main_rect_key not in self._debug_sprites:
            self._debug_sprites[main_rect_key] = sprites.RectangleSprite(spriteref.POLYGON_LAYER)
        self._debug_sprites[main_rect_key].update(new_rect=self.get_rect(), new_color=self.get_debug_color(),
                                                  new_depth=20)
        yield self._debug_sprites[main_rect_key]

        colliders_key = "colliders"
        if colliders_key not in self._debug_sprites:
            self._debug_sprites[colliders_key] = []

        all_colliders = [c for c in self.all_colliders()]

        util.Utils.extend_or_empty_list_to_length(self._debug_sprites[colliders_key], len(all_colliders),
                                                  creator=lambda: sprites.RectangleOutlineSprite(spriteref.POLYGON_LAYER))
        for collider, rect_sprite in zip(all_colliders, self._debug_sprites[colliders_key]):
            color = colors.RED
            rect = collider.get_rect(offs=self.get_xy())
            rect_sprite.update(new_rect=rect, new_color=color, new_outline=2, new_depth=5)
            yield rect_sprite

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


class BlockEntity(Entity):

    def __init__(self, x, y, w, h):
        Entity.__init__(self, x=x, y=y, w=w, h=h)

        self._rect_collider = RectangleCollider([0, 0, w, h], mask=CollisionMasks.BLOCK, dynamic=False)

    def update(self):
        pass

    def get_debug_color(self):
        return colors.DARK_GRAY

    def all_sprites(self):
        return []

    def all_colliders(self):
        yield self._rect_collider


class PlayerEntity(Entity):
    pass


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


class PolygonCollider:

    def __init__(self, points, mask=None, dynamic=True):
        self._mask = mask
        self._dynamic = dynamic
        self._points = points

    def get_mask(self):
        return self._mask

    def is_dynamic(self):
        return self._dynamic

    def get_points(self, offs=(0, 0)):
        return [(p[0] + offs[0], p[1] + offs[1]) for p in self._points]

    def get_rect(self, offs=(0, 0)):
        pts = self.get_points(offs=offs)
        if len(pts) == 0:
            return [0, 0, 0, 0]
        else:
            return util.Utils.get_rect_containing_points(pts)


class RectangleCollider(PolygonCollider):

    def __init__(self, rect, mask=None, dynamic=True):
        points = [p for p in util.Utils.all_rect_corners(rect, inclusive=False)]
        PolygonCollider.__init__(self, points, mask=mask, dynamic=dynamic)
