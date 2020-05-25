
import src.utils.util as util
import typing

import src.game.entities as entities


# json keys
TYPE_ID = "type"        # str
SUBTYPE_ID = "subtype"  # str

X = "x"                 # int
Y = "y"                 # int
W = "w"                 # int
H = "h"                 # int

POINTS = "points"       # list of (int, int)
PT_1 = "pt_1"           # (int, int)
PT_2 = "pt_2"           # (int, int)
PT_3 = "pt_3"           # (int, int)

LOOP = "loop"           # bool
DURATION = "duration"   # int



class SpecType:

    def __init__(self, type_id, required_keys=()):
        self.type_id = type_id
        self.required_keys = util.listify(required_keys)

    def build_entities(self, json_blob) -> typing.Iterable[entities.Entity]:
        raise NotImplementedError()

    def build(self, json_blob, world):
        for ent in self.build_entities(json_blob):
            if ent is not None:
                world.add_entity(ent, next_update=False)


class BlockSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "static_block", required_keys=(X, Y, W, H))

    def build_entities(self, json_blob):
        x = json_blob[X]
        y = json_blob[Y]
        w = json_blob[W]
        h = json_blob[H]

        yield entities.BlockEntity(x, y, w, h)


class SlopedQuadBlockSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "slope_block_quad", required_keys=(X, Y, W, H, PT_1, PT_2, PT_3))

    def build_entities(self, json_blob):
        x = json_blob[X]
        y = json_blob[Y]
        w = json_blob[W]
        h = json_blob[H]
        p1 = json_blob[PT_1]
        p2 = json_blob[PT_2]
        p3 = json_blob[PT_3]




class MovingBlockSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "moving_block", required_keys=(POINTS, W, H, DURATION, LOOP))

    def build_entities(self, json_blob):
        points = json_blob[POINTS]
        w = json_blob[W]
        h = json_blob[H]
        duration = json_blob[DURATION]
        loop = json_blob[LOOP]

        yield entities.MovingBlockEntity(w, h, points, period=duration, loop=loop)


class PlayerSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "player", required_keys=(X, Y, SUBTYPE_ID))

    def build_entities(self, json_blob):
        x = json_blob[X]
        y = json_blob[Y]
        player_type = json_blob[SUBTYPE_ID]  # TODO

        yield entities.PlayerEntity(x, y)


class SpecTypes:

    BLOCK = BlockSpecType()
    MOVING_BLOCK = MovingBlockSpecType()
    SLOPE_BLOCK_QUAD = SlopedQuadBlockSpecType()
    PLAYER = PlayerSpecType()


class SpecFactory:

    @staticmethod
    def get_spec(json_blob):
        pass

