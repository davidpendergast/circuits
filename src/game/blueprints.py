
import typing
import traceback
import random

import src.utils.util as util

import src.game.entities as entities
import src.game.worlds as worlds
import src.game.globalstate as gs
import src.game.spriteref as spriteref
import src.game.const as const


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

ART_ID = "art_id"       # int
COLOR_ID = "color_id"   # int

LOOP = "loop"           # bool
DURATION = "duration"   # int

X_DIR = "x_dir"         # int: -1, 0, or 1
Y_DIR = "y_dir"         # int: -1, 0, or 1


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
        blob_copy = json_blob.copy()
        for key in self.optional_keys:
            if key not in blob_copy:
                blob_copy[key] = self.optional_keys[key]

        for ent in self.build_entities(blob_copy):
            if ent is not None:
                world.add_entity(ent, next_update=False)

    def __repr__(self):
        return type(self).__name__


class BlockSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "block", required_keys=(X, Y, W, H),
                          optional_keys={ART_ID: -1, COLOR_ID: 0})

    def build_entities(self, json_blob):
        x = json_blob[X]
        y = json_blob[Y]
        w = json_blob[W]
        h = json_blob[H]

        art_id = json_blob[ART_ID]
        color_id = json_blob[COLOR_ID]

        yield entities.BlockEntity(x, y, w, h, art_id=art_id, color_id=color_id)


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
        SpecType.__init__(self, "sloped_2x2_block", required_keys=(X, Y, SUBTYPE_ID),
                          optional_keys={ART_ID: -1, COLOR_ID: 0})

    def get_subtypes(self):
        return SlopedQuadBlockSpecType.ALL_SUBTYPES

    # (x pos of point, y pos of point, orientation of slope)
    HORZ_0_0 = (0, 0, "horizontal")
    HORZ_2_0 = (2, 0, "horizontal")
    HORZ_0_2 = (0, 2, "horizontal")
    HORZ_2_2 = (2, 2, "horizontal")

    VERT_0_0 = (0, 0, "vertical")
    VERT_2_0 = (2, 0, "vertical")
    VERT_0_2 = (0, 2, "vertical")
    VERT_2_2 = (2, 2, "vertical")

    ALL_SUBTYPES = [HORZ_0_0, HORZ_2_0, HORZ_0_2, HORZ_2_2,
                    VERT_0_0, VERT_2_0, VERT_0_2, VERT_2_2]

    # subtype -> (rotation, xflip)
    _SUBTYPE_TO_SPRITE_INFO_MAP = {
        HORZ_0_0: (0, True),
        HORZ_2_0: (0, False),  # the 'default' art
        HORZ_0_2: (2, False),
        HORZ_2_2: (2, True),
        VERT_0_0: (3, False),
        VERT_2_0: (1, True),
        VERT_0_2: (3, True),
        VERT_2_2: (1, False)
    }

    def _get_sprite_info(self, json_blob):
        art_id = json_blob[ART_ID]
        if art_id < 0:
            art_id = int(random.random() * 100)
        rot, xflip = SlopedQuadBlockSpecType._SUBTYPE_TO_SPRITE_INFO_MAP[json_blob[SUBTYPE_ID]]

        return entities.CompositeBlockEntity.BlockSpriteInfo(lambda: spriteref.block_sheet().get_quad_block_sprite(art_id),
                                                             rotation=rot, xflip=xflip)

    def build_entities(self, json_blob):
        x = json_blob[X]
        y = json_blob[Y]

        subtype = json_blob[SUBTYPE_ID]

        cs = gs.get_instance().cell_size

        tri_pt = (cs * subtype[0], cs * subtype[1])

        if subtype[2] == "horizontal":
            triangle = [tri_pt, (0, cs), (2 * cs, cs)]
            if subtype[1] == 0:
                rect = [0, cs, 2 * cs, cs]
            else:
                rect = [0, 0, 2 * cs, cs]
        else:
            triangle = [tri_pt, (cs, 0), (cs, 2 * cs)]
            if subtype[0] == 0:
                rect = [cs, 0, cs, 2 * cs]
            else:
                rect = [0, 0, cs, 2 * cs]

        rect_colliders = entities.BlockEntity.build_colliders_for_rect(rect)
        tri_colliders = entities.SlopeBlockEntity.build_colliders_for_points(triangle)

        yield entities.CompositeBlockEntity(x, y, rect_colliders + tri_colliders,
                                            [self._get_sprite_info(json_blob)],
                                            color_id=json_blob[COLOR_ID])


class StartBlockSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "start_block", required_keys=(SUBTYPE_ID, X, Y, W, H, X_DIR),
                          optional_keys={COLOR_ID: -1})

    def get_subtypes(self):
        return const.ALL_PLAYER_IDS

    def build_entities(self, json_blob):
        subtype = json_blob[SUBTYPE_ID]
        x = json_blob[X]
        y = json_blob[Y]
        w = json_blob[W]
        h = json_blob[H]
        facing_dir = json_blob[X_DIR]
        color_id = json_blob[COLOR_ID]

        player_type = entities.PlayerTypes.get_type(subtype)
        yield entities.StartBlock(x, y, w, h, player_type, facing_dir=facing_dir, color_id=color_id)


class EndBlockSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "end_block", required_keys=(SUBTYPE_ID, X, Y, W, H),
                          optional_keys={COLOR_ID: -1})

    def get_subtypes(self):
        return const.ALL_PLAYER_IDS

    def build_entities(self, json_blob):
        subtype = json_blob[SUBTYPE_ID]
        x = json_blob[X]
        y = json_blob[Y]
        w = json_blob[W]
        h = json_blob[H]
        color_id = json_blob[COLOR_ID]

        player_type = entities.PlayerTypes.get_type(subtype)
        yield entities.EndBlock(x, y, w, h, player_type, color_id=color_id)


class MovingBlockSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "moving_block", required_keys=(POINTS, W, H, DURATION, LOOP),
                          optional_keys={ART_ID: -1, COLOR_ID: 0})

    def build_entities(self, json_blob):
        points = json_blob[POINTS]
        w = json_blob[W]
        h = json_blob[H]
        duration = json_blob[DURATION]
        loop = json_blob[LOOP]

        art_id = json_blob[ART_ID]
        color_id = json_blob[COLOR_ID]

        yield entities.MovingBlockEntity(w, h, points, period=duration, loop=loop, art_id=art_id, color_id=color_id)


class PlayerSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "player", required_keys=(X, Y, SUBTYPE_ID))

    def get_subtypes(self):
        return [const.PLAYER_FAST, const.PLAYER_SMALL, const.PLAYER_HEAVY, const.PLAYER_FLYING]

    def build_entities(self, json_blob):
        x = json_blob[X]
        y = json_blob[Y]

        if gs.get_instance().player_type_override is None:
            player_type_id = json_blob[SUBTYPE_ID]
            player_type = entities.PlayerTypes.get_type(player_type_id)
        else:
            player_type = gs.get_instance().player_type_override

        yield entities.PlayerEntity(x, y, player_type=player_type)


class SpecTypes:

    BLOCK = BlockSpecType()
    MOVING_BLOCK = MovingBlockSpecType()
    SLOPE_BLOCK_QUAD = SlopedQuadBlockSpecType()
    PLAYER = PlayerSpecType()
    START_BLOCK = StartBlockSpecType()
    END_BLOCK = EndBlockSpecType()

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


def get_test_blueprint_0() -> LevelBlueprint:
    cs = gs.get_instance().cell_size
    json_blob = {
        ENTITIES: [
            {TYPE_ID: "player", X: cs * 6, Y: cs * 5, SUBTYPE_ID: const.PLAYER_FAST},

            {TYPE_ID: "block", X: cs * 4, Y: cs * 11, W: cs * 3, H: cs * 1},
            {TYPE_ID: "block", X: cs * 13, Y: cs * 11, W: cs * 6, H: cs * 1},
            {TYPE_ID: "block", X: cs * 9, Y: cs * 10, W: cs * 2, H: cs * 2},
            {TYPE_ID: "block", X: cs * 5, Y: cs * 7, W: cs * 0.5, H: cs * 4},
            {TYPE_ID: "block", X: cs * 0, Y: cs * 7, W: cs * 5, H: cs * 1},

            {TYPE_ID: "block", X: cs * 21, Y: cs * 3, W: cs * 0.5, H: cs * 4},
            {TYPE_ID: "block", X: cs * 21.5, Y: cs * 3, W: cs * 2, H: cs * 2},

            {TYPE_ID: "sloped_2x2_block", SUBTYPE_ID: SlopedQuadBlockSpecType.HORZ_0_0, X: cs * 11, Y: cs * 10},
            {TYPE_ID: "sloped_2x2_block", SUBTYPE_ID: SlopedQuadBlockSpecType.HORZ_2_0, X: cs * 7, Y: cs * 10},
        ]
    }

    pts = [(10 * cs, 6 * cs), (16 * cs, 6 * cs), (16 * cs, 10 * cs)]
    json_blob[ENTITIES].append({TYPE_ID: "moving_block", POINTS: pts, W: cs * 2, H: cs * 1, DURATION: 90, LOOP: True})

    return LevelBlueprint(json_blob)


def get_test_blueprint_1() -> LevelBlueprint:
    cs = gs.get_instance().cell_size
    json_blob = {
        ENTITIES: [
            {TYPE_ID: "player", X: cs * 12, Y: cs * 11, SUBTYPE_ID: const.PLAYER_FAST},
        ]
    }

    rects = [
        (0, 0, 2, 5),
        (0, 5, 2, 3),
        (0, 8, 7, 1),
        (0, 9, 2, 4),
        (0, 13, 7, 2),
        (7, 14, 10, 1),  # floor
        (4, 11, 3, 2),

        (9, 7, 2, 1),  # floating platform
        (17, 7, 2, 1),
        (19, 6, 4, 1),
        (15, 10, 2, 1),
        (14, 10, 1, 2),

        (2, 0, 4, 1),  # ciel
        (2, 1, 2, 1),
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
        json_blob[ENTITIES].append({TYPE_ID: "block", X: cs * r[0], Y: cs * r[1], W: cs * r[2], H: cs * r[3]})

    json_blob[ENTITIES].append({TYPE_ID: "sloped_2x2_block", SUBTYPE_ID: SlopedQuadBlockSpecType.HORZ_2_0, X: cs * 17, Y: cs * 6})
    json_blob[ENTITIES].append({TYPE_ID: "sloped_2x2_block", SUBTYPE_ID: SlopedQuadBlockSpecType.HORZ_2_2, X: cs * 4, Y: cs * 1})
    json_blob[ENTITIES].append({TYPE_ID: "sloped_2x2_block", SUBTYPE_ID: SlopedQuadBlockSpecType.VERT_0_0, X: cs * 13, Y: cs * 10})

    return LevelBlueprint(json_blob)


def get_test_blueprint_2() -> LevelBlueprint:
    json_blob = {
        ENTITIES: [
            {TYPE_ID: "player", X: 3*16, Y: 2*16, SUBTYPE_ID: const.PLAYER_FAST},
            {TYPE_ID: "block", X: 0, Y: 112, W: 128, H: 16},
            {TYPE_ID: "block", X: 0, Y: 0, W: 16, H: 16},
            {TYPE_ID: "block", X: 2*16, Y: 14.5*16, W: 25*16, H: 0.5*16}
        ]
    }

    quad_type = SpecTypes.SLOPE_BLOCK_QUAD
    for i in range(0, 8):
        subtype = quad_type.get_subtypes()[i]
        x = 64 + i * 48
        y = 160
        json_blob[ENTITIES].append({TYPE_ID: quad_type.get_id(), SUBTYPE_ID: subtype, X: x, Y: y})

    return LevelBlueprint(json_blob)


def get_test_blueprint_3() -> LevelBlueprint:
    json_blob = {
        ENTITIES: [
            {TYPE_ID: "player", X: 3 * 16, Y: 2 * 16, SUBTYPE_ID: const.PLAYER_FAST},
            {TYPE_ID: "block", X: 3 * 16, Y: 7 * 16, W: 4 * 16, H: 16},
            {TYPE_ID: "block", X: 0, Y: 0, W: 16, H: 8 * 16},
            {TYPE_ID: "block", X: 10 * 16, Y: 8 * 16, W: 2 * 16, H: 16},
            {TYPE_ID: "block", X: 4 * 16, Y: 14 * 16, W: 18 * 16, H: 16},
            {TYPE_ID: "block", X: 12 * 16, Y: 12 * 16, W: 2 * 16, H: 2 * 16},
            {TYPE_ID: "block", X: 4 * 16, Y: 12 * 16, W: 1 * 16, H: 2 * 16},
            {TYPE_ID: "start_block", SUBTYPE_ID: const.PLAYER_FAST, X: 4 * 16, Y: 11 * 16, W: 16, H: 16, X_DIR: 1},
            {TYPE_ID: "start_block", SUBTYPE_ID: const.PLAYER_SMALL, X: 14 * 16, Y: 10 * 16, W: 16 * 2, H: 16, X_DIR: 1},
            {TYPE_ID: "block", X: 14 * 16, Y: 11 * 16, W: 2 * 16, H: 3 * 16},
            {TYPE_ID: "end_block", SUBTYPE_ID: const.PLAYER_FAST, X: 22 * 16, Y: 12 * 16, W: 16 * 2, H: 16},
            {TYPE_ID: "block", X: 22 * 16, Y: 13 * 16, W: 2 * 16, H: 2 * 16},
            {TYPE_ID: "block", X: 18 * 16, Y: 6 * 16, W: 2 * 16, H: 8 * 16},
            {TYPE_ID: "end_block", SUBTYPE_ID: const.PLAYER_SMALL, X: 16, Y: 7 * 16, W: 16 * 2, H: 16},
            {TYPE_ID: "block", X: 0, Y: 8 * 16, W: 4 * 16, H: 7 * 16}
        ]
    }

    return LevelBlueprint(json_blob)

