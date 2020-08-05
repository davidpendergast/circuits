import typing
import src.engine.spritesheets as spritesheets
import src.engine.sprites as sprites
import src.utils.util as util

import src.game.const as const
import src.game.colors as colors

BLOCK_LAYER = "block_layer"
ENTITY_LAYER = "entity_layer"
POLYGON_LAYER = "polygon_layer"
UI_FG_LAYER = "ui_fg_layer"
UI_BG_LAYER = "ui_bg_layer"


def all_world_layers():
    yield BLOCK_LAYER
    yield ENTITY_LAYER
    yield POLYGON_LAYER


def _img(x, y, w, h, offs=(0, 0)):
    return sprites.ImageModel(x, y, w, h, offset=offs)


def get_color(color_id, dark=False):
    if color_id == 0:
        return colors.WHITE if not dark else colors.DARK_GRAY
    elif color_id == 1:
        return colors.BLUE if not dark else colors.DARK_BLUE
    elif color_id == 2:
        return colors.TAN if not dark else colors.DARK_TAN
    elif color_id == 3:
        return colors.GREEN if not dark else colors.DARK_GREEN
    elif color_id == 4:
        return colors.PURPLE if not dark else colors.DARK_PURPLE
    else:
        return colors.PERFECT_RED


class PlayerState:

    def __init__(self, state_id, fallback=None):
        self.state_id = state_id
        self._fallback_state = fallback

    def get_fallback(self):
        return self._fallback_state

    def __eq__(self, other):
        if isinstance(other, PlayerState):
            return self.state_id == other.state_id
        else:
            return False

    def __hash__(self):
        return hash(self.state_id)


class PlayerStates:
    IDLE = PlayerState("idle")
    CROUCH_IDLE = PlayerState("crouch_idle", fallback=IDLE)
    CROUCH_WALKING = PlayerState("crouch_walking", fallback=CROUCH_IDLE)
    AIRBORNE = PlayerState("airborne", fallback=IDLE)
    WALLSLIDE = PlayerState("wallslide", fallback=AIRBORNE)
    WALKING = PlayerState("walking", fallback=IDLE)


class _ObjectSheet(spritesheets.SpriteSheet):

    def __init__(self):
        spritesheets.SpriteSheet.__init__(self, "objects", "assets/circuits.png")

        self.player_a = {
            PlayerStates.IDLE: [],
            PlayerStates.CROUCH_IDLE: [],
            PlayerStates.CROUCH_WALKING: [],
            PlayerStates.WALLSLIDE: [],
            PlayerStates.AIRBORNE: [],
            PlayerStates.WALKING: []
        }

        self.player_b = {
            PlayerStates.IDLE: [],
            PlayerStates.AIRBORNE: [],
            PlayerStates.WALKING: []
        }

        self.player_c = {
            PlayerStates.IDLE: [],
            PlayerStates.AIRBORNE: [],
            PlayerStates.WALKING: []
        }

        self.player_d = {
            PlayerStates.IDLE: [],
            PlayerStates.AIRBORNE: [],
            PlayerStates.WALKING: []
        }

        self._player_id_to_sprite_lookup = {
            const.PLAYER_FAST: self.player_a,
            const.PLAYER_SMALL: self.player_b,
            const.PLAYER_HEAVY: self.player_c,
            const.PLAYER_FLYING: self.player_d
        }

        self.title_img = None

    def get_player_sprites(self, player_id, player_state) -> typing.List[sprites.ImageModel]:
        if player_id not in self._player_id_to_sprite_lookup:
            raise ValueError("unrecognized player id: {}".format(player_id))
        else:
            lookup = self._player_id_to_sprite_lookup[player_id]
            if player_state in lookup and len(lookup[player_state]) > 0:
                return lookup[player_state]
            elif player_state.get_fallback() is not None:
                return self.get_player_sprites(player_id, player_state.get_fallback())
            else:
                return []  # no sprites exist, apparently

    def get_player_sprite(self, player_id, player_state, frame) -> typing.Optional[sprites.ImageModel]:
        spr_list = self.get_player_sprites(player_id, player_state)
        if len(spr_list) == 0:
            return None
        else:
            return spr_list[frame % len(spr_list)]

    def draw_to_atlas(self, atlas, sheet, start_pos=(0, 0)):
        super().draw_to_atlas(atlas, sheet, start_pos=start_pos)

        self.player_a[PlayerStates.IDLE] = [_img(0 + i * 16, 0, 16, 32, offs=start_pos) for i in range(0, 2)]
        self.player_a[PlayerStates.CROUCH_IDLE] = [_img(96 + i * 16, 0, 16, 32, offs=start_pos) for i in range(0, 2)]
        # self.player_a[PlayerStates.CROUCH_WALKING] = # TODO
        self.player_a[PlayerStates.WALLSLIDE] = [_img(64 + i * 16, 0, 16, 32, offs=start_pos) for i in range(0, 2)]
        self.player_a[PlayerStates.AIRBORNE] = [_img(32 + i * 16, 0, 16, 32, offs=start_pos) for i in range(0, 2)]
        self.player_a[PlayerStates.WALKING] = [_img(128 + i * 16, 0, 16, 32, offs=start_pos) for i in range(0, 8)]

        self.player_b[PlayerStates.IDLE] = [_img(0 + i * 16, 48, 16, 16, offs=start_pos) for i in range(0, 2)]
        self.player_b[PlayerStates.AIRBORNE] = [_img(32 + i * 16, 48, 16, 16, offs=start_pos) for i in range(0, 2)]
        self.player_b[PlayerStates.CROUCH_WALKING] = [_img(64 + i * 16, 48, 16, 16, offs=start_pos) for i in range(0, 2)]
        self.player_b[PlayerStates.CROUCH_IDLE] = [_img(96 + i * 16, 48, 16, 16, offs=start_pos) for i in range(0, 2)]
        self.player_b[PlayerStates.WALKING] = [_img(128 + i * 16, 48, 16, 16, offs=start_pos) for i in range(0, 6)]

        self.player_c[PlayerStates.IDLE] = [_img(0 + i * 32, 64, 32, 32, offs=start_pos) for i in range(0, 2)]

        self.player_d[PlayerStates.IDLE] = [_img(0 + i * 16, 96, 16, 32, offs=start_pos) for i in range(0, 8)]
        self.player_d[PlayerStates.WALKING] = [_img(0 + i * 16, 128, 16, 32, offs=start_pos) for i in range(0, 8)]
        self.player_d[PlayerStates.CROUCH_IDLE] = [_img(0 + i * 16, 176, 16, 16, offs=start_pos) for i in range(0, 2)]
        self.player_d[PlayerStates.AIRBORNE] = [_img(32 + i * 16, 160, 16, 32, offs=start_pos) for i in range(0, 6)]

        self.title_img = _img(0, 224, 80, 40, offs=start_pos)


class _BlockSheet(spritesheets.SpriteSheet):

    def __init__(self):
        spritesheets.SpriteSheet.__init__(self, "blocks", "assets/blocks.png")
        self.plain_1x1 = None
        self.border_sprites = []
        self.border_inset = 2

        self.blocks = {}        # (w, h) -> list of imgs
        self.quad_blocks = []

        self.start_blocks = {}  # (w, h, player_id) -> img
        self.end_blocks = {}    # (w, h, player_id) -> img

    def get_block_sprite(self, size, art_id):
        if art_id == 0:
            # should use the empty sprite
            return None

        if size in self.blocks and len(self.blocks[size]) > 0:
            return self.blocks[size][(art_id - 1) % len(self.blocks[size])]
        else:
            return None

    def get_quad_block_sprite(self, art_id):
        if len(self.quad_blocks) > 0:
            return self.quad_blocks[art_id % len(self.quad_blocks)]
        else:
            return None

    def get_start_block_sprite(self, size, player_id):
        key = (size[0], size[1], player_id)
        if key in self.start_blocks:
            return self.start_blocks[key]
        else:
            return None

    def get_end_block_sprite(self, size, player_id):
        key = (size[0], size[1], player_id)
        if key in self.end_blocks:
            return self.end_blocks[key]
        else:
            return None

    def draw_to_atlas(self, atlas, sheet, start_pos=(0, 0)):
        super().draw_to_atlas(atlas, sheet, start_pos=start_pos)
        self.plain_1x1 = _img(0, 0, 16, 16, offs=start_pos)

        inset = self.border_inset
        self.border_sprites = [
            _img(0, 0, inset, inset, offs=start_pos),               # top left
            _img(inset, 0, 16 - inset * 2, inset, offs=start_pos),  # top
            _img(16 - inset, 0, inset, inset, offs=start_pos),      # top right

            _img(0, inset, inset, 16 - inset * 2, offs=start_pos),               # left
            _img(inset, inset, 16 - inset * 2, 16 - inset * 2, offs=start_pos),  # center
            _img(16 - inset, inset, inset, 16 - inset * 2, offs=start_pos),      # right

            _img(0, 16 - inset, inset, inset, offs=start_pos),               # bottom left
            _img(inset, 16 - inset, 16 - inset * 2, inset, offs=start_pos),  # bottom
            _img(16 - inset, 16 - inset, inset, inset, offs=start_pos),      # bottom right
        ]

        def _make_blocks(size, x, y, n=1, offs=(0, 0)):
            return [_img(x + i * 16 * size[0], y, 16 * size[0], 16 * size[1], offs=offs) for i in range(0, n)]

        self.blocks[(1, 1)] = _make_blocks((1, 1), 16, 0, n=2, offs=start_pos)
        self.blocks[(2, 1)] = _make_blocks((2, 1), 0, 16, n=2, offs=start_pos)
        self.blocks[(3, 1)] = _make_blocks((3, 1), 0, 32, n=2, offs=start_pos)

        self.blocks[(2, 0.5)] = _make_blocks((2, 0.5), 0, 48, n=1, offs=start_pos)

        self.blocks[(1, 2)] = _make_blocks((1, 2), 0, 64, n=2, offs=start_pos)
        self.blocks[(2, 2)] = _make_blocks((2, 2), 0, 96, n=1, offs=start_pos)
        self.blocks[(3, 2)] = _make_blocks((3, 2), 0, 128, n=1, offs=start_pos)

        self.quad_blocks = _make_blocks((2, 2), 0, 160, n=3, offs=start_pos)

        player_ids = const.ALL_PLAYER_IDS
        for start_block, player_id in zip(_make_blocks((1, 1), 0, 432, n=4, offs=start_pos), player_ids):
            self.start_blocks[(1, 1, player_id)] = start_block
        for start_block, player_id in zip(_make_blocks((2, 1), 0, 448, n=4, offs=start_pos), player_ids):
            self.start_blocks[(2, 1, player_id)] = start_block
        for end_block, player_id in zip(_make_blocks((2, 1), 0, 416, n=4, offs=start_pos), player_ids):
            self.end_blocks[(2, 1, player_id)] = end_block


class CutsceneTypes:
    ALL_TYPES = []

    SUN = util.add_to_list("assets/cutscenes/sun.png", ALL_TYPES)
    BARREN = util.add_to_list("assets/cutscenes/barren.png", ALL_TYPES)
    SHIP = util.add_to_list("assets/cutscenes/ship.png", ALL_TYPES)
    SPLIT = util.add_to_list("assets/cutscenes/split.png", ALL_TYPES)
    SUN_CLOSEUP = util.add_to_list("assets/cutscenes/sun_closeup.png", ALL_TYPES)
    TRANSPORT = util.add_to_list("assets/cutscenes/transport.png", ALL_TYPES)
    DIG = util.add_to_list("assets/cutscenes/dig.png", ALL_TYPES)


# global sheet instances
_OBJECTS = None
_BLOCKS = None

_CUTSCENES = {}  # sheet_id -> Sheet


def object_sheet() -> _ObjectSheet:
    return _OBJECTS


def block_sheet() -> _BlockSheet:
    return _BLOCKS


def cutscene_image(sheet_type) -> sprites.ImageModel:
    if sheet_type in _CUTSCENES and _CUTSCENES[sheet_type] is not None:
        return _CUTSCENES[sheet_type].get_img()


def initialize_sheets() -> typing.List[spritesheets.SpriteSheet]:
    global _OBJECTS, _BLOCKS, _CUTSCENES
    _OBJECTS = _ObjectSheet()
    _BLOCKS = _BlockSheet()

    all_sheets = [_OBJECTS, _BLOCKS]

    for sheet_id in CutsceneTypes.ALL_TYPES:
        cutscene_sheet = spritesheets.SingleImageSheet(sheet_id)
        _CUTSCENES[sheet_id] = cutscene_sheet

        all_sheets.append(cutscene_sheet)

    return all_sheets


