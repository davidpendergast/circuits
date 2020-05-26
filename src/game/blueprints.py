
import typing
import traceback

import src.utils.util as util

import src.game.entities as entities
import src.game.worlds as worlds
import src.game.globalstate as gs


# json keys
TYPE_ID = "type"        # str
SUBTYPE_ID = "subtype"  # any_json

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


_ALL_SPEC_TYPES = {}


class SpecType:

    def __init__(self, type_id, required_keys=(), optional_keys=None):
        self.type_id = type_id
        self.required_keys = util.listify(required_keys)
        self.optional_keys = {} if optional_keys is None else optional_keys

        if type_id in _ALL_SPEC_TYPES:
            raise ValueError("type_id already used: {}".format(type_id))
        else:
            _ALL_SPEC_TYPES[type_id] = self

    def check_if_valid(self, blob):
        if TYPE_ID not in blob:
            raise ValueError("blob has no type_id")
        elif blob[TYPE_ID] != self.type_id:
            raise ValueError("expected type_id {}, instead got: {}".format(self.type_id, blob[TYPE_ID]))
        else:
            for key in self.required_keys:
                if key not in blob:
                    raise ValueError("missing key: {}".format(key))
                if key == SUBTYPE_ID:
                    subtype = blob[SUBTYPE_ID]
                    if subtype not in self.get_subtypes():
                        raise ValueError("unknown subtype: {}".format(subtype))
        return True

    def get_id(self):
        return self.type_id

    def get_subtypes(self):
        return []

    def build_entities(self, json_blob) -> typing.Iterable[entities.Entity]:
        raise NotImplementedError()

    def build(self, json_blob, world) -> None:
        for ent in self.build_entities(json_blob):
            if ent is not None:
                world.add_entity(ent, next_update=False)

    def __repr__(self):
        return type(self).__name__


class BlockSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "block", required_keys=(X, Y, W, H))

    def build_entities(self, json_blob):
        x = json_blob[X]
        y = json_blob[Y]
        w = json_blob[W]
        h = json_blob[H]

        yield entities.BlockEntity(x, y, w, h)


class SlopedQuadBlockSpecType(SpecType):
    """
        A 2x2 block with a 2x1 slope removed from one of its sides. Like this:

        * .
        |   ' .
        *---*---*   <--- (0, 0, "horizontal")
        |   |   |
        *---*---*

        *---*---*
         '  |   |
          --*---*   <--- (0, 0, "vertical")
           \|   |
            *---*

        *---*---*
        |   |   |
        *---*---*   <--- (0, 2, "horizontal")
        |  .  '
        *
    """

    def __init__(self):
        SpecType.__init__(self, "sloped_2x2_block", required_keys=(X, Y, SUBTYPE_ID))

    def get_subtypes(self):
        return [
            (0, 0, "horizontal"),     # x, y position of point, orientation of slope
            (2, 0, "horizontal"),
            (0, 2, "horizontal"),
            (2, 2, "horizontal"),
            (0, 0, "vertical"),
            (2, 0, "vertical"),
            (0, 2, "vertical"),
            (2, 2, "vertical")
        ]

    def build_entities(self, json_blob):
        x = json_blob[X]
        y = json_blob[Y]

        subtype = json_blob[SUBTYPE_ID]

        cs = gs.get_instance().cell_size
        rect = None
        triangle = None

        tri_pt = (x + cs * subtype[0], y + cs * subtype[1])

        if subtype[2] == "horizontal":
            triangle = [tri_pt, (x, y + cs), (x + 2 * cs, y + cs)]
            if subtype[1] == 0:
                rect = [x, y + cs, 2 * cs, cs]
            else:
                rect = [x, y, 2 * cs, cs]
        else:
            triangle = [tri_pt, (x + cs, y), (x + cs, y + 2 * cs)]
            if subtype[0] == 0:
                rect = [x + cs, y, cs, 2 * cs]
            else:
                rect = [x, y, cs, 2 * cs]

        rect_block = entities.BlockEntity(rect[0], rect[1], rect[2], rect[3])
        slope_block = entities.SlopeBlockEntity(triangle)

        #yield entities.CompositeBlockEntity([rect_block, slope_block])
        yield rect_block
        yield slope_block


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

    def get_subtypes(self):
        return ["A", "B", "C", "D"]

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

    @staticmethod
    def get(type_id) -> SpecType:
        if type_id in _ALL_SPEC_TYPES:
            return _ALL_SPEC_TYPES[type_id]
        else:
            raise ValueError("unrecognized type_id: {}".format(type_id))

    @staticmethod
    def all_types() -> typing.Iterable[SpecType]:
        for type_id in _ALL_SPEC_TYPES:
            yield _ALL_SPEC_TYPES[type_id]


ENTITIES = "entities"  # list of entity data blobs


class LevelBlueprint:

    def __init__(self, json_blob):
        self.json_blob = json_blob

    def create_world(self) -> worlds.World:
        world = worlds.World()

        entity_blobs = util.read_safely(self.json_blob, ENTITIES, [])
        for blob in entity_blobs:
            try:
                type_id = blob[TYPE_ID]
                spec_type = SpecTypes.get(type_id)
                spec_type.check_if_valid(blob)
                spec_type.build(blob, world)
            except Exception:
                print("ERROR: failed to build blob: {}".format(blob))
                traceback.print_exc()

        return world


def get_test_blueprint() -> LevelBlueprint:
    json_blob = {
        ENTITIES: [
            {TYPE_ID: "player", X: 45, Y: 35, SUBTYPE_ID: "A"},
            {TYPE_ID: "block", X: 0, Y: 112, W: 128, H: 16},
            {TYPE_ID: "block", X: 0, Y: 0, W: 16, H: 16},
        ]
    }

    quad_type = SpecTypes.SLOPE_BLOCK_QUAD
    for i in range(0, 8):
        subtype = quad_type.get_subtypes()[i]
        x = 64 + i * 48
        y = 192
        json_blob[ENTITIES].append({TYPE_ID: quad_type.get_id(), SUBTYPE_ID: subtype, X: x, Y: y})

    return LevelBlueprint(json_blob)



