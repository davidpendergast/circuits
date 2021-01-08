
import typing
import traceback
import random
import os

import src.utils.util as util

import src.game.entities as entities
import src.game.worlds as worlds
import src.game.globalstate as gs
import src.game.spriteref as spriteref
import src.game.const as const
import src.game.playertypes as playertypes


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

INVERTED = "inverted"   # bool
TEXT = "text"           # str


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
                        works_as_list = isinstance(subtype, tuple) and list(subtype) in self.get_subtypes()
                        works_as_tuple = isinstance(subtype, list) and tuple(subtype) in self.get_subtypes()

                        if not works_as_list and not works_as_tuple:
                            raise ValueError("unknown subtype: {}".format(subtype))
        return True

    def get_id(self):
        return self.type_id

    def get_subtypes(self):
        return []

    def get_color_ids(self, spec):
        return []

    def get_art_ids(self, spec):
        return []

    def index_of_subtype(self, subtype):
        all_subtypes = self.get_subtypes()
        if subtype in all_subtypes:
            return all_subtypes.index(subtype)
        elif util.tuplify(subtype) in all_subtypes:
            return all_subtypes.index(util.tuplify(subtype))
        else:
            return -1

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
                ent._spec = json_blob.copy()  # XXX but helpful for the level editor

    def get_default_value(self, k):
        if k in self.optional_keys:
            return self.optional_keys[k]
        elif k == X or k == Y:
            return 0
        elif k == W or k == H:
            return 16
        elif k == POINTS:
            return []
        elif k in (PT_1, PT_2, PT_3):
            return (0, 0)
        elif k == ART_ID or k == COLOR_ID:
            return 0
        elif k == LOOP:
            return True
        elif k == DURATION:
            return 90
        elif k == X_DIR or k == Y_DIR:
            return 0
        else:
            return None

    def get_minimum_size(self):
        return (4, 4)

    def get_default_blob(self):
        res = {TYPE_ID: self.get_id()}
        subtypes = self.get_subtypes()
        if len(subtypes) > 0:
            res[SUBTYPE_ID] = subtypes[0]
        all_keys = [k for k in self.required_keys] + [k for k in self.optional_keys]
        for k in all_keys:
            if k in res:
                continue
            else:
                val = self.get_default_value(k)
                if val is not None:
                    res[k] = val
                else:
                    raise ValueError("No default value exists for key: {}".format(k))

        return res

    def __repr__(self):
        return type(self).__name__


class BlockSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "block", required_keys=(X, Y, W, H),
                          optional_keys={ART_ID: 0, COLOR_ID: 0})

    def build_entities(self, json_blob):
        x = json_blob[X]
        y = json_blob[Y]
        w = json_blob[W]
        h = json_blob[H]

        art_id = json_blob[ART_ID]
        color_id = json_blob[COLOR_ID]

        if w > 4 and h > 4:
            yield entities.BlockEntity(x, y, w, h, art_id=art_id, color_id=color_id)
        else:
            yield entities.BreakableBlockEntity(x, y, w, h, art_id=art_id, color_id=color_id)

    def get_color_ids(self, spec):
        return [0, 1, 2, 3, 4]

    def get_art_ids(self, spec):
        size = (spec[W] // gs.get_instance().cell_size, spec[H] // gs.get_instance().cell_size)
        n_block_sprites = spriteref.block_sheet().num_block_sprites(size)
        return [i for i in range(0, n_block_sprites)]


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
                          optional_keys={ART_ID: 0, COLOR_ID: 0, W: 32, H: 32})

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
        rot, xflip = SlopedQuadBlockSpecType._SUBTYPE_TO_SPRITE_INFO_MAP[tuple(json_blob[SUBTYPE_ID])]

        return entities.CompositeBlockEntity.BlockSpriteInfo(lambda: spriteref.block_sheet().get_quad_block_sprite(art_id),
                                                             rotation=rot, xflip=xflip)

    def get_color_ids(self, spec):
        return [0, 1, 2, 3, 4]

    def get_art_ids(self, spec):
        n_block_sprites = spriteref.block_sheet().num_quad_block_sprites()
        return [i for i in range(0, n_block_sprites)]

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

    def get_default_value(self, k):
        if k == W or k == H:
            return 16
        else:
            return super().get_default_value(k)

    def get_minimum_size(self):
        return (16, 16)

    def get_player_type(self, json_blob):
        return playertypes.PlayerTypes.get_type(json_blob[SUBTYPE_ID])

    def build_entities(self, json_blob):
        x = json_blob[X]
        y = json_blob[Y]
        w = json_blob[W]
        h = json_blob[H]
        facing_dir = json_blob[X_DIR]
        color_id = json_blob[COLOR_ID]

        player_type = self.get_player_type(json_blob)
        yield entities.StartBlock(x, y, w, h, player_type, facing_dir=facing_dir, color_id=color_id)


class EndBlockSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "end_block", required_keys=(SUBTYPE_ID, X, Y, W, H),
                          optional_keys={COLOR_ID: -1})

    def get_subtypes(self):
        return const.ALL_PLAYER_IDS

    def get_default_value(self, k):
        if k == W:
            return 32
        elif k == H:
            return 16
        else:
            return super().get_default_value(k)

    def get_minimum_size(self):
        return (32, 16)

    def build_entities(self, json_blob):
        subtype = json_blob[SUBTYPE_ID]
        x = json_blob[X]
        y = json_blob[Y]
        w = json_blob[W]
        h = json_blob[H]
        color_id = json_blob[COLOR_ID]

        player_type = playertypes.PlayerTypes.get_type(subtype)
        yield entities.EndBlock(x, y, w, h, player_type, color_id=color_id)


class SpikeSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "spikes", required_keys=(SUBTYPE_ID, X, Y, W, H),
                          optional_keys={COLOR_ID: 0})

    def get_subtypes(self):
        return [(0, -1), (1, 0), (0, 1), (-1, 0)]  # direction the spikes point

    def build_entities(self, json_blob) -> typing.Iterable[entities.Entity]:
        x = json_blob[X]
        y = json_blob[Y]
        w = json_blob[W]
        h = json_blob[H]
        direction = json_blob[SUBTYPE_ID]
        color_id = json_blob[COLOR_ID]

        yield entities.SpikeEntity(x, y, w, h, direction, color_id=color_id)

    def get_color_ids(self, spec):
        return [0, 1, 2, 3, 4]

    def get_default_value(self, k):
        if k == W:
            return 32
        elif k == H:
            return 16
        elif k == SUBTYPE_ID:
            return self.get_subtypes()[0]
        else:
            return super().get_default_value(k)

    def get_minimum_size(self):
        return (4, 8)


class InfoSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "info", required_keys=(SUBTYPE_ID, X, Y, TEXT, POINTS),
                          optional_keys={COLOR_ID: 0})

    def get_subtypes(self):
        return ["exclam", "question"]

    def get_default_value(self, k):
        if k == TEXT:
            return "Info text will appear here.\nRemember to watch your step!"
        else:
            return super().get_default_value(k)

    def build_entities(self, json_blob) -> typing.Iterable[entities.Entity]:
        x = json_blob[X]
        y = json_blob[Y]
        subtype = json_blob[SUBTYPE_ID]
        text = json_blob[TEXT]
        points = json_blob[POINTS]
        color_id = json_blob[COLOR_ID]

        yield entities.InfoEntity(x, y, points, text, color_id=color_id, info_type=subtype)


class DoorBlockSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "door_block", required_keys=(SUBTYPE_ID, X, Y, W, H),
                          optional_keys={ART_ID: 0, INVERTED: False})

    def get_subtypes(self):
        return [0, 1, 2, 3]

    def build_entities(self, json_blob) -> typing.Iterable[entities.Entity]:
        x = json_blob[X]
        y = json_blob[Y]
        w = json_blob[W]
        h = json_blob[H]
        inverted = json_blob[INVERTED]

        toggle_idx = int(json_blob[SUBTYPE_ID])

        yield entities.DoorBlock(x, y, w, h, toggle_idx, inverted=inverted)

    def get_minimum_size(self):
        return (16, 16)


class KeySpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "key", required_keys=(SUBTYPE_ID, X, Y))

    def get_subtypes(self):
        return [0, 1, 2, 3]

    def build_entities(self, json_blob) -> typing.Iterable[entities.Entity]:
        x = json_blob[X]
        y = json_blob[Y]
        toggle_idx = int(json_blob[SUBTYPE_ID])

        yield entities.KeyEntity.make_at_cell(x / 16, y / 16, toggle_idx)


class MovingBlockSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "moving_block", required_keys=(X, Y, W, H, DURATION, LOOP),
                          optional_keys={POINTS: tuple(), ART_ID: -1, COLOR_ID: 0})

    def build_entities(self, json_blob):
        points = list(util.listify(json_blob[POINTS]))
        x = json_blob[X]
        y = json_blob[Y]
        points.insert(0, (x, y))

        w = json_blob[W]
        h = json_blob[H]
        duration = json_blob[DURATION]
        loop = json_blob[LOOP]

        art_id = json_blob[ART_ID]
        color_id = json_blob[COLOR_ID]

        yield entities.MovingBlockEntity(w, h, points, period=duration, loop=loop, art_id=art_id, color_id=color_id)

    def get_color_ids(self, spec):
        return [0, 1, 2, 3, 4]

    def get_default_value(self, k):
        if k == W:
            return 32
        elif k == H:
            return 8
        else:
            return super().get_default_value(k)

    def get_art_ids(self, spec):
        size = (spec[W] / gs.get_instance().cell_size, spec[H] / gs.get_instance().cell_size)
        n_block_sprites = spriteref.block_sheet().num_block_sprites(size)
        return [i for i in range(0, n_block_sprites)]


class PlayerSpecType(SpecType):

    def __init__(self):
        SpecType.__init__(self, "player", required_keys=(X, Y, SUBTYPE_ID))

    def get_subtypes(self):
        return [const.PLAYER_FAST, const.PLAYER_SMALL, const.PLAYER_HEAVY, const.PLAYER_FLYING]

    @staticmethod
    def get_player_type(json_blob):
        player_type_id = json_blob[SUBTYPE_ID]
        return playertypes.PlayerTypes.get_type(player_type_id)

    def build_entities(self, json_blob):
        x = json_blob[X]
        y = json_blob[Y]

        if gs.get_instance().player_type_override is None:
            player_type = PlayerSpecType.get_player_type(json_blob)
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
    SPIKES = SpikeSpecType()
    INFO = InfoSpecType()

    DOOR_BLOCK = DoorBlockSpecType()
    KEY_BLOCK = KeySpecType()

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


ENTITIES = "entities"           # list of entity data blobs
NAME = "name"                   # name of level
PLAYERS = "characters"          # characters in the level
TIME_LIMIT = "time_limit"       # time limit for level
LEVEL_ID = "level_id"           # identifier for level
DESCRIPTION = "description"     # level flavor text


class LevelBlueprint:

    def __init__(self, json_blob):
        self.json_blob = json_blob

        self.loaded_from_file = None
        self._cached_entities = None  # list of (blob, spec)

    @staticmethod
    def build(name, level_id, players, timelimit, desc, entity_specs):
        return LevelBlueprint({
            NAME: name,
            PLAYERS: [p.get_id() for p in players],
            LEVEL_ID: level_id,
            TIME_LIMIT: timelimit,
            DESCRIPTION: desc,
            ENTITIES: entity_specs
        })

    def name(self):
        return util.read_string(self.json_blob, NAME, "???")

    def level_id(self):
        return util.read_string(self.json_blob, LEVEL_ID, "???")

    def copy_with(self, name=None, level_id=None, description=None, edits=None):
        if edits is None:
            edits = {}

        if name is not None:
            edits[NAME] = name
        if level_id is not None:
            edits[LEVEL_ID] = level_id
        if description is not None:
            edits[DESCRIPTION] = description

        json_copy = util.copy_json(self.json_blob)
        for key in edits:
            json_copy[key] = edits[key]
        return LevelBlueprint(json_copy)

    def get_attribute(self, attrib_id):
        if attrib_id in self.json_blob:
            return self.json_blob[attrib_id]
        else:
            return None

    def description(self):
        return util.read_string(self.json_blob, DESCRIPTION, "???")

    def time_limit(self):
        """returns: level's time limit in ticks"""
        return 60 * 60

    def _recache_entity_specs(self, force=False):
        if force or self._cached_entities is None:
            self._cached_entities = []
            entity_blobs = util.read_safely(self.json_blob, ENTITIES, [])
            for blob in entity_blobs:
                try:
                    type_id = blob[TYPE_ID]
                    spec_type = SpecTypes.get(type_id)
                    spec_type.check_if_valid(blob)
                    self._cached_entities.append((blob, spec_type))
                except Exception:
                    print("ERROR: level \"{}\" failed to build blob: {}".format(self.level_id(), blob))
                    traceback.print_exc()

    def all_entities(self):
        """yields (blob, spec)"""
        self._recache_entity_specs(force=False)
        for blob_and_spec in self._cached_entities:
            yield blob_and_spec

    def get_player_types(self):
        res = []
        if PLAYERS in self.json_blob:
            for player_id in self.json_blob[PLAYERS]:
                res.append(playertypes.PlayerTypes.get_type(player_id))
        else:
            for blob, spec in self.all_entities():
                if isinstance(spec, StartBlockSpecType):
                    res.append(spec.get_player_type(blob))
        if len(res) == 0:
            # just for test levels, really
            for blob, spec in self.all_entities():
                if isinstance(spec, PlayerSpecType):
                    player_type = PlayerSpecType.get_player_type(blob)
                    if player_type is not None:
                        res.append(player_type)
        return res

    def create_world(self) -> worlds.World:
        world = worlds.World(bp=self)

        self._recache_entity_specs(force=False)
        for (blob, spec) in self.all_entities():
            try:
                spec.build(blob, world)
            except Exception:
                print("ERROR: failed to build blob: {}".format(blob))
                traceback.print_exc()

        camera_min_xy = [None, None]
        camera_max_xy = [None, None]
        for ent in world.all_entities():
            if ent.is_block():
                camera_min_xy[0] = min(camera_min_xy[0] if camera_min_xy[0] is not None else float('inf'), ent.get_rect()[0])
                camera_max_xy[0] = max(camera_max_xy[0] if camera_max_xy[0] is not None else -float('inf'), ent.get_rect()[0] + ent.get_rect()[2])
                camera_min_xy[1] = min(camera_min_xy[1] if camera_min_xy[1] is not None else float('inf'), ent.get_rect()[1])
                camera_max_xy[1] = max(camera_max_xy[1] if camera_max_xy[1] is not None else -float('inf'), ent.get_rect()[1] + ent.get_rect()[3])
        world.set_camera_bounds(camera_min_xy, camera_max_xy)

        if camera_max_xy[0] is not None:
            safe_zone = [camera_min_xy[0],
                         camera_min_xy[1],
                         camera_max_xy[0] - camera_min_xy[0],
                         camera_max_xy[1] - camera_min_xy[1]]
            safe_zone = util.rect_expand(safe_zone, gs.get_instance().cell_size * 0.5)
            world.set_safe_zones([safe_zone])

        return world

    def __repr__(self):
        return "{}:{}".format(type(self).__name__, self.name())


def load_level_from_file(filepath) -> LevelBlueprint:
    try:
        json_blob = util.load_json_from_path(filepath)
        return LevelBlueprint(json_blob)

    except Exception:
        print("ERROR: failed to load level: {}".format(filepath))
        traceback.print_exc()
        return None


def load_all_levels_from_dir(path):
    """returns: map from level_id -> level blueprint"""

    res = {}  # level_id -> LevelBlueprint
    try:
        for file in os.listdir(path):
            if file.endswith(".json"):
                filepath = os.path.join(path, file)
                level = load_level_from_file(filepath)
                if level is not None:
                    level.loaded_from_file = filepath
                    res[level.level_id()] = level
                    print("INFO: loaded level \"{}\" from file: {}".format(level.level_id(), filepath))
    except Exception:
        print("ERROR: unexpected error while reading levels from: {}".format(path))
        traceback.print_exc()

    return res


def write_level_to_file(level, filepath):
    try:
        util.save_json_to_path(level.json_blob, filepath)
        return True

    except Exception:
        traceback.print_exc()
        return False


class SpecUtils:

    @staticmethod
    def get_rect(spec_blob, default_size=16):
        if X in spec_blob:
            x = int(spec_blob[X])
        else:
            return None
        if Y in spec_blob:
            y = int(spec_blob[Y])
        else:
            return None
        w = default_size
        h = default_size
        if W in spec_blob:
            w = int(spec_blob[W])
        if H in spec_blob:
            h = int(spec_blob[H])
        return [x, y, w, h]

    @staticmethod
    def set_xy(spec_blob, xy):
        res = spec_blob.copy()
        if X in spec_blob:
            res[X] = int(xy[0])
        if Y in spec_blob:
            res[Y] = int(xy[1])
        return res

    @staticmethod
    def move(spec_blob, dxy, and_points=True):
        res = spec_blob.copy()
        if X in spec_blob:
            res[X] = int(spec_blob[X] + dxy[0])
        if Y in spec_blob:
            res[Y] = int(spec_blob[Y] + dxy[1])
        if and_points:
            res = SpecUtils.move_points(res, dxy)
        return res

    @staticmethod
    def resize(spec_blob, dxy, min_size=4):
        min_w = min_size
        min_h = min_size
        if TYPE_ID in spec_blob and SUBTYPE_ID in spec_blob:
            type_id = spec_blob[TYPE_ID]
            try:
                spec_type = SpecTypes.get(type_id)
                min_size_internal = spec_type.get_minimum_size()
                min_w = max(min_size_internal[0], min_w)
                min_h = max(min_size_internal[1], min_h)
            except Exception:
                print("ERROR: failed to find minimum size of spec: {}".format(spec_blob))
                traceback.print_exc()

        res = spec_blob.copy()
        if W in spec_blob:
            if res[W] < dxy[0]:
                res[W] = dxy[0]
            else:
                res[W] = max(min_w, int(res[W] + dxy[0]))
        if H in spec_blob:
            if res[H] < dxy[1]:
                res[H] = dxy[1]
            else:
                res[H] = max(min_h, int(res[H] + dxy[1]))
        return res

    @staticmethod
    def add_point(spec_blob, xy):
        res = spec_blob.copy()
        if POINTS in spec_blob:
            new_points = [pt for pt in spec_blob[POINTS]]
            new_points.append(xy)
            res[POINTS] = tuple(new_points)
        return res

    @staticmethod
    def remove_points(spec_blob, xy, r=16):
        res = spec_blob.copy()
        if POINTS in spec_blob:
            res[POINTS] = tuple(pt for pt in spec_blob[POINTS] if util.dist(pt, xy) > r)
        return res

    @staticmethod
    def clear_points(spec_blob):
        res = spec_blob.copy()
        if POINTS in spec_blob:
            res[POINTS] = tuple()
        return res

    @staticmethod
    def move_points(spec_blob, dxy):
        res = spec_blob.copy()
        if POINTS in spec_blob:
            res[POINTS] = tuple(util.add(pt, dxy) for pt in spec_blob[POINTS])
        return res

    @staticmethod
    def cycle_subtype(spec_blob, steps):
        res = spec_blob.copy()
        if TYPE_ID in spec_blob and SUBTYPE_ID in spec_blob:
            type_id = spec_blob[TYPE_ID]
            try:
                spec_type = SpecTypes.get(type_id)
                my_subtype = res[SUBTYPE_ID]
                all_subtypes = spec_type.get_subtypes()
                idx = spec_type.index_of_subtype(my_subtype)
                if idx >= 0:
                    next_idx = (idx + steps) % len(all_subtypes)
                    next_subtype = all_subtypes[next_idx]
                    res[SUBTYPE_ID] = next_subtype
            except Exception:
                print("ERROR: failed to cycle spec subtype: {}".format(spec_blob))
                traceback.print_exc()
        return res

    @staticmethod
    def cycle_color(spec_blob, steps):
        res = spec_blob.copy()
        if TYPE_ID in spec_blob:
            type_id = spec_blob[TYPE_ID]

            try:
                spec_type = SpecTypes.get(type_id)

                if COLOR_ID in spec_blob:
                    cur_color = spec_blob[COLOR_ID]
                elif COLOR_ID in spec_type.optional_keys:
                    cur_color = spec_type.optional_keys[COLOR_ID]
                else:
                    return res  # this spec doesn't support color

                available_colors = spec_type.get_color_ids(res)
                if len(available_colors) > 0:
                    cur_idx = -1
                    if cur_color in available_colors:
                        cur_idx = available_colors.index(cur_color)
                    new_idx = (cur_idx + steps) % len(available_colors)
                    res[COLOR_ID] = available_colors[new_idx]
            except Exception:
                print("ERROR: failed to cycle spec color: {}".format(spec_blob))
                traceback.print_exc()
        return res

    @staticmethod
    def cycle_art(spec_blob, steps):
        res = spec_blob.copy()
        if TYPE_ID in spec_blob:
            type_id = spec_blob[TYPE_ID]
            try:
                spec_type = SpecTypes.get(type_id)

                if ART_ID in spec_blob:
                    cur_art = spec_blob[ART_ID]
                elif ART_ID in spec_type.optional_keys:
                    cur_art = spec_type.optional_keys[COLOR_ID]
                else:
                    return res  # this spec doesn't support art

                available_art = spec_type.get_art_ids(res)
                if len(available_art) > 0:
                    cur_idx = -1
                    if cur_art in available_art:
                        cur_idx = available_art.index(cur_art)
                    new_idx = (cur_idx + steps) % len(available_art)
                    res[ART_ID] = available_art[new_idx]
            except Exception:
                print("ERROR: failed to cycle spec art: {}".format(spec_blob))
                traceback.print_exc()
        return res

    @staticmethod
    def toggle_inverted(spec_blob):
        res = spec_blob.copy()
        if TYPE_ID in spec_blob:
            type_id = spec_blob[TYPE_ID]
            try:
                spec_type = SpecTypes.get(type_id)
                if INVERTED in spec_blob:
                    cur_val = spec_blob[INVERTED]
                elif INVERTED in spec_type.optional_keys:
                    cur_val = spec_type.optional_keys[INVERTED]
                else:
                    return res  # doesn't support inversion

                res[INVERTED] = not cur_val

            except Exception:
                print("ERROR: failed to toggle inversion: {}".format(spec_blob))
                traceback.print_exc()
        return res


def get_test_blueprint_0() -> LevelBlueprint:
    cs = gs.get_instance().cell_size
    json_blob = {
        NAME: "Platform of Fate",
        LEVEL_ID: "_gay",
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

    pts = [(16 * cs, 6 * cs), (16 * cs, 10 * cs)]
    json_blob[ENTITIES].append({TYPE_ID: "moving_block", X: 10 * cs, Y: 6 * cs, POINTS: pts, W: cs * 2, H: cs * 1, DURATION: 90, LOOP: True})

    return LevelBlueprint(json_blob)


def get_test_blueprint_1() -> LevelBlueprint:
    cs = gs.get_instance().cell_size
    json_blob = {
        NAME: "Mockup 1",
        LEVEL_ID: "_mockup_1",
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


def get_template_blueprint() -> LevelBlueprint:
    level = load_level_from_file(util.resource_path("template_level.json"))
    level.loaded_from_file = None
    return level


def get_test_blueprint_2() -> LevelBlueprint:
    json_blob = {
        LEVEL_ID: "_all_quads",
        NAME: "Quad City",
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
        NAME: "Level Start and End Test",
        PLAYERS: [const.PLAYER_FAST, const.PLAYER_SMALL, const.PLAYER_FLYING],
        ENTITIES: [
            {TYPE_ID: "block", X: 3 * 16, Y: 7 * 16, W: 4 * 16, H: 16},
            {TYPE_ID: "block", X: 0, Y: 0, W: 16, H: 8 * 16},
            {TYPE_ID: "block", X: 10 * 16, Y: 8 * 16, W: 2 * 16, H: 16},
            {TYPE_ID: "block", X: 4 * 16, Y: 14 * 16, W: 12 * 16, H: 16},
            {TYPE_ID: "block", X: 12 * 16, Y: 12 * 16, W: 2 * 16, H: 2 * 16},
            {TYPE_ID: "block", X: 4 * 16, Y: 12 * 16, W: 1 * 16, H: 2 * 16},
            {TYPE_ID: "start_block", SUBTYPE_ID: const.PLAYER_FAST, X: 4 * 16, Y: 11 * 16, W: 16, H: 16, X_DIR: 1},
            {TYPE_ID: "start_block", SUBTYPE_ID: const.PLAYER_SMALL, X: 14 * 16, Y: 10 * 16, W: 16 * 2, H: 16, X_DIR: 1},
            {TYPE_ID: "start_block", SUBTYPE_ID: const.PLAYER_FLYING, X: 26 * 16, Y: 9 * 16, W: 16, H: 16, X_DIR: -1},
            {TYPE_ID: "block", X: 14 * 16, Y: 11 * 16, W: 2 * 16, H: 3 * 16},
            {TYPE_ID: "block", X: 22 * 16, Y: 13 * 16, W: 2 * 16, H: 2 * 16},
            {TYPE_ID: "block", X: 18 * 16, Y: 6 * 16, W: 2 * 16, H: 8 * 16},
            {TYPE_ID: "end_block", SUBTYPE_ID: const.PLAYER_FAST, X: 22 * 16, Y: 12 * 16, W: 16 * 2, H: 16},
            {TYPE_ID: "end_block", SUBTYPE_ID: const.PLAYER_SMALL, X: 16, Y: 7 * 16, W: 16 * 2, H: 16},
            {TYPE_ID: "end_block", SUBTYPE_ID: const.PLAYER_FLYING, X: 16 * 16, Y: 14 * 16, W: 16 * 2, H: 16},
            {TYPE_ID: "block", X: 0, Y: 8 * 16, W: 4 * 16, H: 7 * 16},
            {TYPE_ID: "block", X: 1 * 16, Y: 0, W: 30 * 16, H: 3 * 16, COLOR_ID: 1},
            {TYPE_ID: "block", X: 18 * 16, Y: 14 * 16, W: 4 * 16, H: 1 * 16, COLOR_ID: 0},
            {TYPE_ID: "block", X: 26 * 16, Y: 10 * 16, W: 1 * 16, H: 5 * 16, COLOR_ID: 0}
        ]
    }

    return LevelBlueprint(json_blob)


def get_test_blueprint_4() -> LevelBlueprint:
    json_blob = {
        NAME: "Toggle Block Test",
        PLAYERS: [const.PLAYER_FAST, const.PLAYER_SMALL],
        ENTITIES: [
            {TYPE_ID: "block", X: 2 * 16, Y: 5 * 16, W: 4 * 16, H: 16},
            {TYPE_ID: "block", X: 0, Y: 0, W: 16, H: 15 * 16},
            {TYPE_ID: "block", X: 6 * 16, Y: 7 * 16, W: 2 * 16, H: 16},
            {TYPE_ID: "block", X: 4 * 16, Y: 14 * 16, W: 12 * 16, H: 16},
            {TYPE_ID: "block", X: 1 * 16, Y: 6 * 16, W: 5 * 16, H: 2 * 16},
            {TYPE_ID: "block", X: 12 * 16, Y: 12 * 16, W: 2 * 16, H: 2 * 16},
            {TYPE_ID: "block", X: 4 * 16, Y: 12 * 16, W: 1 * 16, H: 2 * 16},
            {TYPE_ID: "start_block", SUBTYPE_ID: const.PLAYER_FAST, X: 1 * 16, Y: 11 * 16, W: 16, H: 16, X_DIR: 1},
            {TYPE_ID: "start_block", SUBTYPE_ID: const.PLAYER_SMALL, X: 1 * 16, Y: 5 * 16, W: 16, H: 16, X_DIR: 1},
            {TYPE_ID: "block", X: 14 * 16, Y: 11 * 16, W: 2 * 16, H: 3 * 16},
            {TYPE_ID: "block", X: 22 * 16, Y: 13 * 16, W: 2 * 16, H: 2 * 16},
            {TYPE_ID: "block", X: 18 * 16, Y: 6 * 16, W: 2 * 16, H: 8 * 16},
            {TYPE_ID: "end_block", SUBTYPE_ID: const.PLAYER_FAST, X: 22 * 16, Y: 12 * 16, W: 16 * 2, H: 16},
            {TYPE_ID: "end_block", SUBTYPE_ID: const.PLAYER_SMALL, X: 27 * 16, Y: 5 * 16, W: 16 * 2, H: 16},
            {TYPE_ID: "block", X: 1 * 16, Y: 0, W: 30 * 16, H: 3 * 16, COLOR_ID: 1},
            {TYPE_ID: "block", X: 18 * 16, Y: 14 * 16, W: 4 * 16, H: 1 * 16, COLOR_ID: 0},
            {TYPE_ID: "block", X: 26 * 16, Y: 10 * 16, W: 1 * 16, H: 5 * 16, COLOR_ID: 0}
        ]
    }

    return LevelBlueprint(json_blob)

