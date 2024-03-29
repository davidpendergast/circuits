import typing
import src.engine.spritesheets as spritesheets
import src.engine.sprites as sprites
import src.engine.threedee as threedee
import src.utils.util as util
import src.utils.artutils as artutils

import src.game.const as const
import src.game.colors as colors
import src.game.particles as particles

import configs

# layers listed roughly from bottom to top

THREEDEE_LAYER = "3d_layer"

POLYGON_LAYER = "polygon_layer"
BLOCK_LAYER = "block_layer"
ENTITY_LAYER = "entity_layer"
WORLD_UI_LAYER = "world_ui_layer"

POLYGON_UI_BG_LAYER = "polygon_ui_bg_layer"
UI_BG_LAYER = "ui_bg_layer"
UI_FG_LAYER = "ui_fg_layer"
POLYGON_ULTRA_OMEGA_TOP_LAYER = "polygon_ui_fg_layer"
ULTRA_OMEGA_GAMMA_TOP_IMAGE_LAYER = "actual_top_image_layer"


def all_world_layers():
    yield BLOCK_LAYER
    yield ENTITY_LAYER
    yield POLYGON_LAYER
    yield WORLD_UI_LAYER


def all_3d_layers():
    yield THREEDEE_LAYER


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
    elif color_id == 5:
        return colors.DARK_GRAY if not dark else colors.LIGHT_GRAY
    else:
        return colors.PERFECT_RED


class PlayerState:

    def __init__(self, state_id, fallback=None):
        self.state_id = state_id
        self._fallback_state = fallback

        self._carrying_link = None
        self._non_carrying_link = None

    def get_fallback(self):
        return self._fallback_state

    def as_carrying(self) -> 'PlayerState':
        if self._carrying_link is not None:
            return self._carrying_link
        else:
            return self

    def as_non_carrying(self) -> 'PlayerState':
        if self._non_carrying_link is not None:
            return self._non_carrying_link
        else:
            return self

    def is_carrying(self):
        return self.as_carrying() is self

    @staticmethod
    def make_carrying_link(non_carrying_state, carrying_state):
        non_carrying_state._carrying_link = carrying_state
        carrying_state._non_carrying_link = non_carrying_state

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

    IDLE_CARRYING = PlayerState("idle_carrying", fallback=IDLE)
    CROUCH_IDLE_CARRYING = PlayerState("crouch_idle_carrying", fallback=CROUCH_IDLE)
    CROUCH_WALKING_CARRYING = PlayerState("crouch_walking_carrying", fallback=CROUCH_WALKING)
    AIRBORNE_CARRYING = PlayerState("airborne_carrying", fallback=AIRBORNE)
    WALLSLIDE_CARRYING = PlayerState("wallslide_carrying", fallback=WALLSLIDE)
    WALKING_CARRYING = PlayerState("walking_carrying", fallback=WALKING)

    PlayerState.make_carrying_link(IDLE, IDLE_CARRYING)
    PlayerState.make_carrying_link(CROUCH_IDLE, CROUCH_IDLE_CARRYING)
    PlayerState.make_carrying_link(CROUCH_WALKING, CROUCH_WALKING_CARRYING)
    PlayerState.make_carrying_link(AIRBORNE, AIRBORNE_CARRYING)
    PlayerState.make_carrying_link(WALLSLIDE, WALLSLIDE_CARRYING)
    PlayerState.make_carrying_link(WALKING, WALKING_CARRYING)


class _ObjectSheet(spritesheets.SpriteSheet):

    def __init__(self):
        spritesheets.SpriteSheet.__init__(self, "objects", "assets/circuits.png")

        self.extra_space = (0, 512)
        self.extra_space_rect = None
        self.extra_space_xy = [0, 0]
        self.extra_space_row_h = 0

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

        self.player_c = {  # other "real" animations are in _PlayerCSheet
            PlayerStates.IDLE: [],
        }

        self.player_d = {
            PlayerStates.IDLE: [],
            PlayerStates.AIRBORNE: [],
            PlayerStates.WALKING: []
        }

        self._player_id_to_sprite_lookup = {
            const.PLAYER_FAST: self.player_a,
            const.PLAYER_SMALL: self.player_b,
            const.PLAYER_FLYING: self.player_d
        }

        self.player_broken_pieces = {
            const.PLAYER_FAST: [],
            const.PLAYER_SMALL: [],
            const.PLAYER_HEAVY: [],
            const.PLAYER_FLYING: [],
        }

        self.speaker_portraits = {}

        self.thin_block_broken_pieces_horz = []
        self.thin_block_broken_pieces_vert = []
        self.falling_block_pieces = []  # TL, TR, BL, BR

        self.toggle_block_bases = []
        self.toggle_block_icons = []
        self._toggle_blocks = {}

        self.pushable_blocks = {}  # (w, h, color_id) -> list of ImageModel

        self.character_arrows = []
        self.character_arrow_fills = {}  # player_id -> ImageModel

        self.goal_arrows = {}  # player_id -> list of ImageModels (for transparency)

        self.player_orb_sprites = []  # list of (ImageModel, ImageModel, ImageModel)

        self.particles = {}

        self.phasing_sprites = {}  # player_id -> list of ImageModels

        self.spike_tops_1 = None
        self.spike_tops_2 = None
        self.spike_tops_4 = None
        self.spike_tops_8 = None
        self.all_spike_tops = []

        self.spike_bottoms_1 = None
        self.spike_bottoms_2 = None
        self.spike_bottoms_4 = None
        self.spike_bottoms_8 = None
        self.all_spike_bottoms = []

        self.info_exclamation = (None, None)
        self.info_question = (None, None)
        self.info_invis = (None, None)

        self.teleporter_blocks = []  # list of (rim, arrow, inner_detail, outer_detail)
        self.camera_boundary_blocks = []

        self.skull_icon = None

    def get_size(self, img_size):
        return (img_size[0] + self.extra_space[0], img_size[1] + self.extra_space[1])

    def _next_extra_space_rect(self, size):
        if self.extra_space_xy[0] + size[0] > self.extra_space_rect[2]:
            self.extra_space_xy[0] = 0
            self.extra_space_xy[1] += self.extra_space_row_h
            self.extra_space_row_h = size[1]
        res = [self.extra_space_xy[0] + self.extra_space_rect[0],
               self.extra_space_xy[1] + self.extra_space_rect[1], size[0], size[1]]
        # XXX without the +1, pixels can leak into other sprites. not sure why
        self.extra_space_row_h = max(self.extra_space_row_h, size[1] + 1)
        self.extra_space_xy[0] += size[0]
        return res

    def get_player_sprites(self, player_id, player_state) -> typing.List[sprites.ImageModel]:
        if player_id == const.PLAYER_HEAVY:
            lookup = _player_c_sheet().player_c
        elif player_id not in self._player_id_to_sprite_lookup:
            raise ValueError("unrecognized player id: {}".format(player_id))
        else:
            lookup = self._player_id_to_sprite_lookup[player_id]

        if player_state in lookup and len(lookup[player_state]) > 0:
            return lookup[player_state]
        elif player_state.get_fallback() is not None:
            return self.get_player_sprites(player_id, player_state.get_fallback())
        else:
            return []  # no sprites exist, apparently

    def get_speaker_portrait_sprites(self, speaker_id):
        if speaker_id in self.speaker_portraits:
            return self.speaker_portraits[speaker_id]
        else:
            return []

    def get_goal_arrow(self, player_id, alpha=1):
        return util.index_into(self.goal_arrows[player_id], alpha)

    def get_player_sprite(self, player_id, player_state, frame) -> typing.Optional[sprites.ImageModel]:
        spr_list = self.get_player_sprites(player_id, player_state)
        if len(spr_list) == 0:
            return None
        else:
            return spr_list[frame % len(spr_list)]

    def get_carrying_position(self, spr):
        if spr in _player_c_sheet().carrying_pos:
            return _player_c_sheet().carrying_pos[spr]
        else:
            return (spr.width() // 2 - 2, 0, 4, 1)

    def get_broken_player_sprite(self, player_id, part_idx, rotation=0):
        """
        :param rotation: [0, 1)
        """
        if player_id not in self.player_broken_pieces:
            return None
        part_list = self.player_broken_pieces[player_id]
        if 0 <= part_idx < len(part_list):
            return util.index_into(part_list[part_idx], rotation, wrap=True)
        return None

    def num_broken_player_parts(self, player_id):
        if player_id not in self.player_broken_pieces:
            return 0
        else:
            return len(self.player_broken_pieces[player_id])

    def get_toggle_block_sprite(self, idx, w, h, solid):
        key = (idx, w, h, solid)
        if key in self._toggle_blocks:
            return self._toggle_blocks[key]
        else:
            print("WARN: no sprite for toggle block: {}".format(key))
            return None

    def get_phasing_sprite(self, player_id, fade_pcnt, fade_out, anim_idx):
        return util.index_into(self.phasing_sprites[(player_id, fade_out)], fade_pcnt)

    def draw_to_atlas(self, atlas, sheet, start_pos=(0, 0)):
        super().draw_to_atlas(atlas, sheet, start_pos=start_pos)

        self.extra_space_rect = [0 + start_pos[0],
                                 sheet.get_height() + start_pos[1],
                                 sheet.get_width(),
                                 self.extra_space[1]]
        self.extra_space_xy = [0, 0]

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

        # needed for stuff like fadeout animations
        self.player_c[PlayerStates.IDLE] = [_img(0 + 32 * i, 64, 32, 32, offs=start_pos) for i in range(0, 2)]

        self.player_d[PlayerStates.IDLE] = [_img(0 + i * 16, 96, 16, 32, offs=start_pos) for i in range(0, 8)]
        self.player_d[PlayerStates.WALKING] = [_img(0 + i * 16, 128, 16, 32, offs=start_pos) for i in range(0, 8)]
        self.player_d[PlayerStates.CROUCH_IDLE] = [_img(0 + i * 16, 176, 16, 16, offs=start_pos) for i in range(0, 2)]
        self.player_d[PlayerStates.AIRBORNE] = [_img(32 + i * 16, 160, 16, 32, offs=start_pos) for i in range(0, 6)]

        self.player_broken_pieces[const.PLAYER_FAST] = self._handle_rotated_player_pieces([624, 0, 8, 8], 7, 8, atlas, start_pos)
        self.player_broken_pieces[const.PLAYER_SMALL] = self._handle_rotated_player_pieces([624, 32, 8, 8], 7, 8, atlas, start_pos)
        self.player_broken_pieces[const.PLAYER_HEAVY] = self._handle_rotated_player_pieces([624, 64, 8, 8], 8, 8, atlas, start_pos)
        self.player_broken_pieces[const.PLAYER_FLYING] = self._handle_rotated_player_pieces([624, 96, 8, 8], 6, 8, atlas, start_pos)

        self.speaker_portraits[const.PLAYER_FAST] = [_img(176, 392 + i * 32, 24, 32, offs=start_pos) for i in range(0, 2)]
        self.speaker_portraits[const.PLAYER_SMALL] = [_img(176 + 24, 392 + i * 32, 24, 32, offs=start_pos) for i in range(0, 2)]
        self.speaker_portraits[const.PLAYER_HEAVY] = [_img(176 + 24 * 2, 392 + i * 32, 24, 32, offs=start_pos) for i in range(0, 2)]
        player_d_portrait_width = 25  # needed another pixel, sue me~
        self.speaker_portraits[const.PLAYER_FLYING] = [_img(176 + 24 * 3, 392 + i * 32, player_d_portrait_width, 32, offs=start_pos) for i in range(0, 2)]
        self.speaker_portraits["overseer"] = [_img(296, 392 + i * 32, 24, 32, offs=start_pos) for i in range(0, 2)]

        temp = self._handle_rotated_player_pieces([624, 128, 8, 8], 2, 8, atlas, start_pos)
        self.thin_block_broken_pieces_horz = temp[0]
        self.thin_block_broken_pieces_vert = temp[1]
        self.falling_block_pieces = self._handle_rotated_player_pieces([624, 136, 8, 8], 2, 8, atlas, start_pos) + \
                                    self._handle_rotated_player_pieces([624, 144, 8, 8], 2, 8, atlas, start_pos)

        self.player_orb_sprites = [(_img(32, 368 + i * 8, 8, 8, offs=start_pos),
                                    _img(40, 368 + i * 8, 8, 8, offs=start_pos),
                                    _img(48, 368 + i * 8, 8, 8, offs=start_pos)) for i in range(0, 2)]

        self.particles[particles.ParticleTypes.CROSS_TINY] = [_img(56 + i * 3, 368, 3, 3, offs=start_pos) for i in range(0, 2)]
        self.particles[particles.ParticleTypes.CROSS_SMALL] = [_img(64 + i * 5, 368, 5, 5, offs=start_pos) for i in range(0, 2)]
        self.particles[particles.ParticleTypes.BUBBLES_SMALL] = [_img(56 + i * 3, 381, 3, 3, offs=start_pos) for i in range(0, 2)]
        self.particles[particles.ParticleTypes.BUBBLES_MEDIUM] = [_img(56 + i * 4, 376, 4, 4, offs=start_pos) for i in range(0, 2)]
        self.particles[particles.ParticleTypes.BUBBLES_LARGE] = [_img(64 + i * 5, 376, 5, 5, offs=start_pos) for i in range(0, 2)]

        self.toggle_block_bases = []
        self.toggle_block_icons = []
        self._toggle_blocks = {}  # (idx, w, h, solid) -> ImageModel

        tb_xy = (0, 224)
        for i in range(0, 4):
            self.toggle_block_icons.append(_img(tb_xy[0], tb_xy[1] + i * 32, 16, 16, offs=start_pos))
            self.toggle_block_bases.append(_img(tb_xy[0], tb_xy[1] + 16 + i * 32, 16, 16, offs=start_pos))
            self._toggle_blocks[(i, 16, 16, True)] = _img(tb_xy[0] + 16, tb_xy[1] + 32 * i, 16, 16, offs=start_pos)
            self._toggle_blocks[(i, 32, 16, True)] = _img(tb_xy[0] + 32, tb_xy[1] + 32 * i, 32, 16, offs=start_pos)
            self._toggle_blocks[(i, 16, 32, True)] = _img(tb_xy[0] + 64, tb_xy[1] + 32 * i, 16, 32, offs=start_pos)
            self._toggle_blocks[(i, 32, 32, True)] = _img(tb_xy[0] + 96, tb_xy[1] + 32 * i, 32, 32, offs=start_pos)
            self._toggle_blocks[(i, 16, 16, False)] = _img(tb_xy[0] + 16, tb_xy[1] + 16 + 32 * i, 16, 16, offs=start_pos)
            self._toggle_blocks[(i, 32, 16, False)] = _img(tb_xy[0] + 32, tb_xy[1] + 16 + 32 * i, 32, 16, offs=start_pos)
            self._toggle_blocks[(i, 16, 32, False)] = _img(tb_xy[0] + 80, tb_xy[1] + 32 * i, 16, 32, offs=start_pos)
            self._toggle_blocks[(i, 32, 32, False)] = _img(tb_xy[0] + 128, tb_xy[1] + 32 * i, 32, 32, offs=start_pos)

        self.pushable_blocks = {}
        for i in range(0, 5):
            self.pushable_blocks[(1, 1, (i + 1) % 5)] = _img(160, 224 + i * 32, 16, 16, offs=start_pos)
            self.pushable_blocks[(2, 2, (i + 1) % 5)] = _img(176, 224 + i * 32, 24, 24, offs=start_pos)
            self.pushable_blocks[(3, 3, (i + 1) % 5)] = _img(200, 224 + i * 32, 32, 32, offs=start_pos)

        for i in range(0, 4):
            self.character_arrows.append(_img(24 * i, 416, 24, 24, offs=start_pos))
        self.character_arrow_fills[const.PLAYER_FAST] = _img(0, 440, 24, 24, offs=start_pos)
        self.character_arrow_fills[const.PLAYER_SMALL] = _img(24, 440, 24, 24, offs=start_pos)
        self.character_arrow_fills[const.PLAYER_HEAVY] = _img(48, 440, 24, 24, offs=start_pos)
        self.character_arrow_fills[const.PLAYER_FLYING] = _img(72, 440, 24, 24, offs=start_pos)

        self.goal_arrows[const.PLAYER_FAST] = self._make_transparent_sprites([96, 416, 16, 24], sheet, 10, atlas)
        self.goal_arrows[const.PLAYER_SMALL] = self._make_transparent_sprites([112, 416, 16, 24], sheet, 10, atlas)
        self.goal_arrows[const.PLAYER_HEAVY] = self._make_transparent_sprites([128, 416, 16, 24], sheet, 10, atlas)
        self.goal_arrows[const.PLAYER_FLYING] = self._make_transparent_sprites([144, 416, 16, 24], sheet, 10, atlas)

        self.phasing_sprites[(const.PLAYER_FAST, True)] = self._handle_phasing_sprites(self.player_a[PlayerStates.IDLE][0].rect(), 30, atlas, fade_out=True)
        self.phasing_sprites[(const.PLAYER_SMALL, True)] = self._handle_phasing_sprites(self.player_b[PlayerStates.IDLE][0].rect(), 30, atlas, fade_out=True)
        self.phasing_sprites[(const.PLAYER_HEAVY, True)] = self._handle_phasing_sprites(self.player_c[PlayerStates.IDLE][0].rect(), 30, atlas, fade_out=True)
        self.phasing_sprites[(const.PLAYER_FLYING, True)] = self._handle_phasing_sprites(self.player_d[PlayerStates.IDLE][0].rect(), 30, atlas, fade_out=True)
        self.phasing_sprites[(const.PLAYER_FAST, False)] = self._handle_phasing_sprites(self.player_a[PlayerStates.IDLE][0].rect(), 30, atlas, fade_out=False)
        self.phasing_sprites[(const.PLAYER_SMALL, False)] = self._handle_phasing_sprites(self.player_b[PlayerStates.IDLE][0].rect(), 30, atlas, fade_out=False)
        self.phasing_sprites[(const.PLAYER_HEAVY, False)] = self._handle_phasing_sprites(self.player_c[PlayerStates.IDLE][0].rect(), 30, atlas, fade_out=False)
        self.phasing_sprites[(const.PLAYER_FLYING, False)] = self._handle_phasing_sprites(self.player_d[PlayerStates.IDLE][0].rect(), 30, atlas, fade_out=False)

        self.spike_tops_1 = _img(32, 384, 4, 4, offs=start_pos)
        self.spike_tops_2 = _img(32, 384, 8, 4, offs=start_pos)
        self.spike_tops_4 = _img(32, 384, 16, 4, offs=start_pos)
        self.spike_tops_8 = _img(32, 384, 32, 4, offs=start_pos)
        self.all_spike_tops = [self.spike_tops_1, self.spike_tops_2, self.spike_tops_4, self.spike_tops_8]

        self.spike_bottoms_1 = _img(32, 392, 4, 8, offs=start_pos)
        self.spike_bottoms_2 = _img(32, 392, 8, 8, offs=start_pos)
        self.spike_bottoms_4 = _img(32, 392, 16, 8, offs=start_pos)
        self.spike_bottoms_8 = _img(32, 392, 32, 8, offs=start_pos)
        self.all_spike_bottoms = [self.spike_bottoms_1, self.spike_bottoms_2, self.spike_bottoms_4, self.spike_bottoms_8]

        self.info_exclamation = (_img(160, 438, 8, 2, offs=start_pos), _img(160, 416, 8, 16, offs=start_pos))
        self.info_question = (_img(168, 438, 8, 2, offs=start_pos), _img(168, 416, 8, 16, offs=start_pos))
        self.info_invis = (_img(160, 462, 8, 2, offs=start_pos), _img(160, 440, 8, 16, offs=start_pos))

        tp_xy = (232, 224)
        self.teleporter_blocks = []
        for i in range(8):
            tp_sprites = tuple([_img(tp_xy[0] + j * 32, tp_xy[1] + i * 16, 32, 16, offs=start_pos) for j in range(4)])
            self.teleporter_blocks.append(tp_sprites)

        self.camera_boundary_blocks = [_img(232 + 16 * i, 352, 16, 16, offs=start_pos) for i in range(5)]
        self.skull_icon = _img(232, 368, 16, 16, offs=start_pos)

    def get_spikes_with_length(self, length, tops=True, overflow_if_not_divisible=True):
        all_spikes = self.all_spike_tops if tops else self.all_spike_bottoms
        res = []
        while all_spikes[0].width() <= length:
            for spr in reversed(all_spikes):
                if spr.width() <= length:
                    res.append(spr)
                    length -= spr.width()
                    break
        if length > 0 and overflow_if_not_divisible:
            res.append(all_spikes[0])
        return res

    def get_teleporter_sprites(self, angle_pcnt: float):
        """
        :param angle_pcnt: value from 0.0 to 1.0 (0 = down, 0.5 = up, 1.0 = down again)
        :return: (main_sprite, arrow_fill, inner_detail, outer_detail)
        """
        return util.index_into(self.teleporter_blocks, angle_pcnt + 0.5 / len(self.teleporter_blocks), wrap=True)

    def get_camera_boundary_sprite(self, idx):
        return self.camera_boundary_blocks[idx % len(self.camera_boundary_blocks)]

    def get_particle_sprite(self, particle_type: particles.ParticleType, idx):
        sprites = self.particles[particle_type]
        return sprites[idx % len(sprites)]

    def get_pushable_block_sprite(self, size, color_id):
        key = (size[0], size[1], color_id if color_id >= 0 else 0)
        if key in self.pushable_blocks:
            return self.pushable_blocks[key]
        else:
            return None

    def _make_transparent_sprites(self, base_rect, src_sheet, n, atlas):
        result_models = []
        for i in range(0, n):
            dest_rect = self._next_extra_space_rect((base_rect[2], base_rect[3]))
            artutils.draw_with_transparency(src_sheet, base_rect, atlas, dest_rect, (i + 1) / n)
            result_models.append(_img(dest_rect[0], dest_rect[1], dest_rect[2], dest_rect[3]))
        return result_models

    def _handle_rotated_player_pieces(self, base_rect, n_pieces, n_rots, atlas, start_pos):
        res = []
        for p_i in range(0, n_pieces):
            piece_base_rect = [base_rect[0] + (p_i % 2) * base_rect[2] + start_pos[0],
                               base_rect[1] + (p_i // 2) * base_rect[3] + start_pos[1],
                               base_rect[2], base_rect[3]]
            rots_for_piece = []
            rots_for_piece.append(_img(piece_base_rect[0], piece_base_rect[1], piece_base_rect[2], piece_base_rect[3]))
            for r_i in range(1, n_rots):
                dest_rect = [piece_base_rect[0] - r_i * piece_base_rect[2] * 2,
                             piece_base_rect[1], piece_base_rect[2], piece_base_rect[3]]
                artutils.draw_rotated_sprite(atlas, piece_base_rect, atlas, dest_rect, r_i / n_rots)
                rots_for_piece.append(_img(dest_rect[0], dest_rect[1], dest_rect[2], dest_rect[3]))
            res.append(rots_for_piece)
        return res

    def _handle_phasing_sprites(self, base_rect, n_frames, atlas, fade_out=True):
        def get_pos(i):
            # hope this is only called once per img~
            rect = self._next_extra_space_rect((base_rect[2], base_rect[3]))
            return (rect[0], rect[1])
        raw_rects = artutils.draw_vertical_line_phasing_animation(atlas, base_rect, n_frames, atlas, get_pos,
                                                                  min_fade_dur=10, rand_seed=12345, fade_out=fade_out)
        return [_img(r[0], r[1], r[2], r[3]) for r in raw_rects]  # start_pos offset is already baked in


class _PlayerCSheet(spritesheets.SpriteSheet):

    def __init__(self):
        spritesheets.SpriteSheet.__init__(self, "player_c", "assets/player_c.png")

        self.player_c = {}  # state -> list of models
        self.carrying_pos = {}  # image model -> rect

    def draw_to_atlas(self, atlas, sheet, start_pos=(0, 0)):
        super().draw_to_atlas(atlas, sheet, start_pos=start_pos)

        self.player_c[PlayerStates.IDLE] = [_img(0 + i * 32, 0, 32, 32, offs=start_pos) for i in range(0, 2)]
        self.player_c[PlayerStates.WALKING] = [_img(i * 32, 32, 32, 32, offs=start_pos) for i in range(0, 8)]
        self.player_c[PlayerStates.AIRBORNE] = [_img(64 + i * 32, 0, 32, 32, offs=start_pos) for i in range(0, 2)]
        self.player_c[PlayerStates.CROUCH_IDLE] = [_img(128 + i * 32, 0, 32, 32, offs=start_pos) for i in range(0, 2)]
        self.player_c[PlayerStates.CROUCH_WALKING] = self.player_c[PlayerStates.CROUCH_IDLE]

        def move(model, dxy):
            return _img(model.x + dxy[0], model.y + dxy[1], model.width(), model.height())

        carrying_y_offs = 64
        self.player_c[PlayerStates.IDLE_CARRYING] = [move(m, (0, carrying_y_offs)) for m in self.player_c[PlayerStates.IDLE]]
        self.player_c[PlayerStates.WALKING_CARRYING] = [move(m, (0, carrying_y_offs)) for m in self.player_c[PlayerStates.WALKING]]
        self.player_c[PlayerStates.AIRBORNE_CARRYING] = [move(m, (0, carrying_y_offs)) for m in self.player_c[PlayerStates.AIRBORNE]]
        self.player_c[PlayerStates.CROUCH_IDLE_CARRYING] = [move(m, (0, carrying_y_offs)) for m in self.player_c[PlayerStates.CROUCH_IDLE]]
        self.player_c[PlayerStates.CROUCH_WALKING_CARRYING] = self.player_c[PlayerStates.CROUCH_IDLE_CARRYING]

        for k in self.player_c:
            if k.is_carrying():
                for spr in self.player_c[k]:
                    self._calc_carrying_pos_and_rm_markers(atlas, spr)

    def _calc_carrying_pos_and_rm_markers(self, atlas, spr: sprites.ImageModel, marker=(255, 0, 0, 255)):
        reds = []
        for x in range(0, spr.width()):
            for y in range(0, spr.height()):
                atlas_xy = (spr.x + x, spr.y + y)
                if atlas.get_at(atlas_xy) == marker:
                    reds.append((x, y))
                    atlas.set_at(atlas_xy, (255, 255, 255, 0))
        if len(reds) > 0:
            self.carrying_pos[spr] = util.get_rect_containing_points(reds)


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

    def num_block_sprites(self, size):
        if size in self.blocks:
            return 1 + len(self.blocks[size])
        else:
            return 1

    def get_quad_block_sprite(self, art_id):
        if len(self.quad_blocks) > 0:
            return self.quad_blocks[art_id % len(self.quad_blocks)]
        else:
            return None

    def num_quad_block_sprites(self):
        return len(self.quad_blocks)

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

        self.blocks[(1, 1)] = _make_blocks((1, 1), 16, 0, n=6, offs=start_pos)
        self.blocks[(2, 1)] = _make_blocks((2, 1), 0, 16, n=3, offs=start_pos)
        self.blocks[(3, 1)] = _make_blocks((3, 1), 0, 32, n=2, offs=start_pos)

        self.blocks[(2, 0.5)] = _make_blocks((2, 0.5), 0, 48, n=1, offs=start_pos)

        self.blocks[(1, 2)] = _make_blocks((1, 2), 0, 64, n=6, offs=start_pos)
        self.blocks[(2, 2)] = _make_blocks((2, 2), 0, 96, n=5, offs=start_pos)
        self.blocks[(3, 2)] = _make_blocks((3, 2), 0, 128, n=1, offs=start_pos)

        self.quad_blocks = _make_blocks((2, 2), 0, 160, n=3, offs=start_pos)

        player_ids = const.ALL_PLAYER_IDS
        for start_block, player_id in zip(_make_blocks((1, 1), 0, 432, n=4, offs=start_pos), player_ids):
            self.start_blocks[(1, 1, player_id)] = start_block
        for start_block, player_id in zip(_make_blocks((2, 1), 0, 448, n=4, offs=start_pos), player_ids):
            self.start_blocks[(2, 1, player_id)] = start_block
        for end_block, player_id in zip(_make_blocks((2, 1), 0, 416, n=4, offs=start_pos), player_ids):
            self.end_blocks[(2, 1, player_id)] = end_block


class _DecorationSheet(spritesheets.SpriteSheet):

    def __init__(self):
        spritesheets.SpriteSheet.__init__(self, "decorations", "assets/decorations.png")

        self.sprites = {}  # (w, h) -> list of ImageModels, bool: can_recolor

    def draw_to_atlas(self, atlas, sheet, start_pos=(0, 0)):
        super().draw_to_atlas(atlas, sheet, start_pos=start_pos)

        def _make_blocks(xy, dims, n=1, offs=(0, 0), can_recolor=True):
            return [_img(xy[0] + i * dims[0], xy[1], dims[0], dims[1], offs=offs) for i in range(0, n)], can_recolor

        self.sprites.clear()
        self.sprites[(16, 16)] = _make_blocks((0, 0), (16, 16), n=2, offs=start_pos)
        self.sprites[(16, 8)] = _make_blocks((0, 16), (16, 8), n=3, offs=start_pos)
        self.sprites[(24, 8)] = _make_blocks((0, 24), (24, 8), n=2, offs=start_pos)
        self.sprites[(8, 8)] = _make_blocks((0, 32), (8, 8), n=3, offs=start_pos)
        self.sprites[(32, 32)] = _make_blocks((0, 40), (32, 32), n=2, offs=start_pos)
        self.sprites[(32, 16)] = _make_blocks((0, 72), (32, 16), n=3, offs=start_pos)
        self.sprites[(128, 112)] = _make_blocks((0, 128), (128, 112), n=1, offs=start_pos, can_recolor=False)

    def get_sprite(self, size, idx):
        """ returns: ImageModel, can_recolor """
        if size in self.sprites:
            imgs, can_recolor = self.sprites[size]
            return imgs[idx % len(imgs)], can_recolor
        else:
            return None, True


class _UiSheet(spritesheets.SpriteSheet):

    N_PROGRESS_BARS = 288

    def __init__(self):
        spritesheets.SpriteSheet.__init__(self, "ui", "assets/ui.png")

        self.title_img = None
        self.title_img_small = None

        self.top_panel_bg = None
        self.top_panel_progress_bar_bg = None
        self.top_panel_progress_bar_full = None
        self.top_panel_progress_bar_empty = None
        self.top_panel_progress_bars = []

        self._character_cards = {}              # (str: player_id, bool: flared) -> ImageModel
        self._character_card_animations = {}    # (boolean first, boolean: last) -> list of ImageModel
        self._character_card_anim_done = None

    def get_size(self, img_size):
        size = super().get_size(img_size)
        bar_size = _UiSheet.N_PROGRESS_BARS * 6
        return (size[0], size[1] + bar_size)

    def draw_to_atlas(self, atlas, sheet, start_pos=(0, 0)):
        super().draw_to_atlas(atlas, sheet, start_pos=start_pos)

        self.title_img = _img(0, 0, 168, 56, offs=start_pos)
        self.title_img_small = _img(0, 168, 88, 32, offs=start_pos)

        self.top_panel_bg = _img(16, 80, 288, 32, offs=start_pos)
        self.top_panel_progress_bar_bg = _img(16, 112, 288, 10, offs=start_pos)

        self._character_cards = {}
        chars = [const.PLAYER_FAST, const.PLAYER_SMALL, const.PLAYER_HEAVY, const.PLAYER_FLYING]
        for i in range(0, 4):
            for j in range(0, 2):
                key = (chars[i], j == 0)
                self._character_cards[key] = _img(16 + 48 * i, 144 + 32 * j, 48, 32, offs=start_pos)

        n_frames = 16
        for i in range(0, 4):
            first = i == 0 or i == 1
            last = i == 0 or i == 2
            row_1_sprs = [_img(16 + j * 48, 208 + 64 * i, 48, 32) for j in range(0, n_frames // 2)]
            row_2_sprs = [_img(16 + j * 48, 208 + 64 * i + 32, 48, 32) for j in range(0, n_frames // 2)]
            self._character_card_animations[(first, last)] = row_1_sprs + row_2_sprs

        self._character_card_anim_done = _img(16, 464, 48, 32)

        bar_x = 16
        bar_y = 128
        bar_w = 288
        bar_h = 6
        self.top_panel_progress_bar_full = _img(bar_x, bar_y, bar_w, bar_h, offs=start_pos)
        self.top_panel_progress_bar_empty = _img(bar_x, bar_y + 8, bar_w, bar_h, offs=start_pos)
        self.top_panel_progress_bars = []

        bar_anim_xy = (16 + start_pos[0], sheet.get_height() + start_pos[1])
        n_frames = _UiSheet.N_PROGRESS_BARS
        rects_drawn = artutils.draw_decay_animation_effect(sheet, [bar_x, bar_y, bar_w, bar_h], n_frames,
                             atlas, lambda frm_idx: [bar_anim_xy[0], bar_anim_xy[1] + bar_h * frm_idx, bar_w, bar_h],
                             lambda frm_idx: [bar_x, bar_y, int(bar_w * frm_idx / n_frames), bar_h],
                             lambda frm_idx: [bar_x, bar_y, int(bar_w * frm_idx * 1.2 / n_frames), bar_h],
                             decay_chance_provider=lambda frm_idx, xy: 0.1 - (0.08 * frm_idx / n_frames))
        for r in rects_drawn:
            self.top_panel_progress_bars.append(_img(r[0], r[1], r[2], r[3], offs=(0, 0)))

    def get_character_card_sprite(self, player_type, is_first):
        return self._character_cards[(player_type.get_id(), is_first)]

    def get_character_card_anim(self, is_first, is_last, frm, done=False):
        if done:
            return self._character_card_anim_done
        else:
            res_list = self._character_card_animations[(is_first, is_last)]
            return res_list[frm % len(res_list)]

    def get_bar_sprite(self, pcnt_full):
        if pcnt_full >= 1:
            return self.top_panel_progress_bar_full
        elif pcnt_full <= 0:
            return self.top_panel_progress_bar_empty
        else:
            n_bars = len(self.top_panel_progress_bars)
            idx = util.bound(round((1 - pcnt_full) * n_bars), 0, n_bars - 1)
            return self.top_panel_progress_bars[idx]


class _OverworldSheet(spritesheets.SpriteSheet):

    def __init__(self):
        spritesheets.SpriteSheet.__init__(self, "overworld", "assets/overworld.png")

        # [0, 1, 2,
        #  3, 4, 5,
        #  6, 7, 8]
        self.level_icon_empty_pieces = []
        self.level_icon_full_pieces = []
        self.level_icon_empty_gray_pieces = []
        self.level_icon_full_gray_pieces = []

        self.level_small_border = None
        self.level_small_icon_exclam = None
        self.level_small_icon_unit = None
        self.level_small_icon_dot = None
        self.level_small_icon_connections = []  # [up, right, south, left]

        self.connectors = {}  # (north: bool, east: bool, south: bool, west: bool) -> ImageModel

        self.border_thin = []
        self.border_thick = []
        self.border_double_thin = []
        self.border_double_thick = []
        self.border_single_line = []

        self.lock_icons = []
        self.lock_icons_with_anim_weights = []

    def get_connection_sprite(self, n=False, e=False, s=False, w=False):
        # TODO gray sprites?
        connections = (n, e, s, w)
        if connections in self.connectors:
            return self.connectors[connections]
        else:
            return None

    def get_lock_icon(self, prog=0):
        return util.index_into(self.lock_icons_with_anim_weights, prog, wrap=False)

    def _make_pieces(self, rect, offs=(0, 0)):
        corner_size = 9
        inner_size = 5
        res = []
        y = 0
        for yi in range(0, 3):
            x = 0
            y_size = corner_size if yi != 1 else inner_size
            for xi in range(0, 3):
                x_size = corner_size if xi != 1 else inner_size
                res.append(_img(rect[0] + x, rect[1] + y, x_size, y_size, offs=offs))
                x += x_size
            y += y_size
        return res

    def _make_borders(self, rect, thickness, offs=(0, 0)):
        res = []
        for y_idx in range(0, 3):
            if y_idx == 0:
                y = 0
                h = thickness
            elif y_idx == 1:
                y = thickness
                h = rect[3] - thickness * 2
            else:
                y = rect[3] - thickness
                h = thickness

            for x_idx in range(0, 3):
                if x_idx == 0:
                    x = 0
                    w = thickness
                elif x_idx == 1:
                    x = thickness
                    w = rect[2] - thickness * 2
                else:
                    x = rect[2] - thickness
                    w = thickness

                res.append(sprites.ImageModel(rect[0] + x, rect[1] + y, w, h, offset=offs))
        return res

    def draw_to_atlas(self, atlas, sheet, start_pos=(0, 0)):
        super().draw_to_atlas(atlas, sheet, start_pos=start_pos)

        self.level_icon_empty_pieces = self._make_pieces([0, 0, 24, 24], offs=start_pos)
        self.level_icon_full_pieces = self._make_pieces([24, 0, 24, 24], offs=start_pos)
        self.level_icon_empty_gray_pieces = self._make_pieces([0, 24, 24, 24], offs=start_pos)
        self.level_icon_full_gray_pieces = self._make_pieces([24, 24, 24, 24], offs=start_pos)

        self.connectors[(True, False, True, False)] = _img(48, 0, 24, 24, offs=start_pos)
        self.connectors[(False, True, False, True)] = _img(72, 0, 24, 24, offs=start_pos)
        self.connectors[(True, False, False, True)] = _img(96, 0, 24, 24, offs=start_pos)
        self.connectors[(True, True, False, False)] = _img(120, 0, 24, 24, offs=start_pos)
        self.connectors[(False, True, True, False)] = _img(144, 0, 24, 24, offs=start_pos)
        self.connectors[(False, False, True, True)] = _img(168, 0, 24, 24, offs=start_pos)

        # fade-out connectors
        self.connectors[(True, False, False, False)] = _img(48, 48, 24, 24, offs=start_pos)
        self.connectors[(False, True, False, False)] = _img(72, 48, 24, 24, offs=start_pos)
        self.connectors[(False, False, True, False)] = _img(96, 48, 24, 24, offs=start_pos)
        self.connectors[(False, False, False, True)] = _img(120, 48, 24, 24, offs=start_pos)

        self.level_small_border = _img(0, 48, 12, 12, offs=start_pos)
        self.level_small_icon_exclam = _img(12, 48, 12, 12, offs=start_pos)
        self.level_small_icon_unit = _img(24, 48, 12, 12, offs=start_pos)
        self.level_small_icon_dot = _img(36, 48, 12, 12, offs=start_pos)
        self.level_small_icon_connections = [_img(192 + 24 * (i % 2), 0 + 24 * (i // 2), 24, 24, offs=start_pos) for i in range(4)]

        # borders
        self.border_thin = self._make_borders([0, 72, 24, 24], 4, offs=start_pos)
        self.border_thick = self._make_borders([0, 96, 24, 24], 4, offs=start_pos)

        self.border_double_thin = self._make_borders([24, 72, 24, 24], 5, offs=start_pos)
        self.border_double_thick = self._make_borders([24, 96, 24, 24], 6, offs=start_pos)

        self.border_single_line = self._make_borders([0, 120, 24, 24], 1, offs=start_pos)

        # lock icons
        self.lock_icons = [_img(48 + (i % 8) * 24, 72 + (i // 8) * 24, 24, 24, offs=start_pos) for i in range(0, 12)]
        self.lock_icons_with_anim_weights = util.add_repeats(self.lock_icons, [32, 1, 1, 16, 2, 2, 2, 2, 2, 2, 2, 60])


class _LevelBuilderSheet(spritesheets.SpriteSheet):

    def __init__(self):
        spritesheets.SpriteSheet.__init__(self, "levelbuilder", "assets/levelbuilder.png")

        self.level_builder_page_buttons = []  # (deselected_img, selected_img)
        self.level_builder_button_outline = None
        self.level_builder_new_obj_buttons = []
        self.level_builder_misc_buttons = []
        self.level_builder_panel_top_outline = None
        self.level_builder_panel_mid_outline = None
        self.level_builder_panel_divider_outline = None
        self.level_builder_panel_bottom_outline = None
        self.level_builder_expand_button = None
        self.level_builder_contract_button = None

        self.number_icons = []
        self.clock_icon = None

    def draw_to_atlas(self, atlas, sheet, start_pos=(0, 0)):
        super().draw_to_atlas(atlas, sheet, start_pos=start_pos)

        n_page_btns = 5
        self.level_builder_page_buttons = [(_img(i * 16, 0, 16, 16, offs=start_pos),
                                            _img(n_page_btns * 16 + i * 16, 0, 16, 16, offs=start_pos)) for i in range(n_page_btns)]
        self.level_builder_button_outline = _img(96, 16, 16, 16, offs=start_pos)
        self.level_builder_new_obj_buttons = [_img((i % 10) * 16, 48 + (i // 10) * 16, 16, 16, offs=start_pos) for i in range(50)]
        self.level_builder_misc_buttons = [_img(160 + (i % 5) * 16, (i // 5) * 16, 16, 16, offs=start_pos) for i in range(8)]

        self.level_builder_panel_top_outline = _img(0, 16, 96, 8, offs=start_pos)
        self.level_builder_panel_mid_outline = _img(0, 24, 96, 8, offs=start_pos)
        self.level_builder_panel_divider_outline = _img(0, 32, 96, 8, offs=start_pos)
        self.level_builder_panel_bottom_outline = _img(0, 40, 96, 8, offs=start_pos)

        self.level_builder_expand_button = _img(112, 16, 8, 24, offs=start_pos)
        self.level_builder_contract_button = _img(120, 16, 8, 24, offs=start_pos)

        offs = (160, 96)
        self.number_icons = [_img(offs[0] + 5 * i, offs[1], 5, 7, offs=start_pos) for i in range(10)]
        self.clock_icon = _img(offs[0], offs[1] + 7, 7, 7, offs=start_pos)


class _StarSheet(spritesheets.SpriteSheet):

    N_OPACITY_LEVELS = 8

    def __init__(self):
        spritesheets.SpriteSheet.__init__(self, "stars", "assets/stars.png")

        self.stars = []

    def get_size(self, img_size):
        w = img_size[0]
        h = img_size[1] * _StarSheet.N_OPACITY_LEVELS
        return (w, h)

    def draw_to_atlas(self, atlas, sheet, start_pos=(0, 0)):
        super().draw_to_atlas(atlas, sheet, start_pos=start_pos)

        sheet_h = sheet.get_height()

        for i in range(1, _StarSheet.N_OPACITY_LEVELS):
            opacity = 1 - i / (_StarSheet.N_OPACITY_LEVELS + 1)
            x = start_pos[0]
            y = start_pos[1] + sheet_h * i
            artutils.draw_with_transparency(sheet, sheet.get_rect(), atlas, (x, y), opacity)

        small_rects = [[(i % 3) * 16, (i // 3) % 2, 16, 16] for i in range(0, 6)]
        large_rects = [[48, 0, 32, 32], [80, 0, 32, 32]]

        self.stars = []
        for i in range(1, _StarSheet.N_OPACITY_LEVELS):
            y = sheet_h * i
            table = {"small": [],
                     "large": []}
            for r in small_rects:
                table["small"].append(_img(r[0], r[1] + y, r[2], r[3], offs=start_pos))
            for r in large_rects:
                table["large"].append(_img(r[0], r[1] + y, r[2], r[3], offs=start_pos))
            self.stars.append(table)
        self.stars.reverse()

    def get_small_star(self, idx, opacity):
        return self.get_star(idx, "small", opacity)

    def get_large_star(self, idx, opacity):
        return self.get_star(idx, "large", opacity)

    def get_star(self, idx, ident, opacity):
        table = util.index_into(self.stars, opacity, wrap=False)
        if ident in table:
            return table[ident][idx % len(table[ident])]
        else:
            return None


class TextureSheet(spritesheets.SpriteSheet):

    def __init__(self, sheet_id, filename):
        spritesheets.SpriteSheet.__init__(self, sheet_id, filename)

        self._texture_coord_to_atlas_coord = lambda xy: None

    def get_xform_to_atlas(self):
        return self._texture_coord_to_atlas_coord

    def draw_to_atlas(self, atlas, sheet, start_pos=(0, 0)):
        super().draw_to_atlas(atlas, sheet, start_pos=start_pos)
        atlas_size = (atlas.get_width(), atlas.get_height())
        sheet_rect = [start_pos[0], start_pos[1], sheet.get_width(), sheet.get_height()]

        def _map_to_atlas(xy):
            atlas_x = (sheet_rect[0] + xy[0] * sheet_rect[2])
            atlas_y = atlas_size[1] - (sheet_rect[1] + (1 - xy[1]) * sheet_rect[3])
            return (atlas_x, atlas_y)

        self._texture_coord_to_atlas_coord = _map_to_atlas


class TextureSheetTypes:
    ALL_TYPES = []
    RAINBOW = util.add_to_list(("rainbow", "assets/textures/rainbow.png"), ALL_TYPES)
    SHIP = util.add_to_list(("ship_texture", "assets/textures/ship_texture.png"), ALL_TYPES)
    SUN_FLAT = util.add_to_list(("sun_texture_flat", "assets/textures/sun_flat.png"), ALL_TYPES)


class ThreeDeeModels:
    SHIP = None
    POINTY_BOX = None
    AXIS = None
    SUN_FLAT = None

    _2D_MODEL_CACHE = {}  # ImageModel -> ThreeDeeModel

    @staticmethod
    def _get_xform_for_texture(texture_id):
        if configs.rainbow_3d:
            texture_id = "rainbow"
        return lambda xy: _3D_TEXTURES[texture_id].get_xform_to_atlas()(xy)

    @staticmethod
    def load_models_from_disk():
        xform = lambda ident: ThreeDeeModels._get_xform_for_texture(ident)

        ThreeDeeModels.SHIP = threedee.ThreeDeeModel.load_from_disk("ship", "assets/models/ship.obj", xform("ship_texture"))
        ThreeDeeModels.POINTY_BOX = threedee.ThreeDeeModel.load_from_disk("pointy_box", "assets/models/pointy_box.obj", xform("ship_texture"))
        ThreeDeeModels.AXIS = threedee.ThreeDeeModel.load_from_disk("axis", "assets/models/axis.obj", xform("ship_texture"))
        ThreeDeeModels.SUN_FLAT = threedee.ThreeDeeModel.load_from_disk("sun_flat", "assets/models/sun_flat.obj", xform("sun_texture_flat"))

    @staticmethod
    def from_2d_model(model_2d):
        if model_2d not in ThreeDeeModels._2D_MODEL_CACHE:
            ThreeDeeModels._2D_MODEL_CACHE[model_2d] = threedee.ThreeDeeModel.build_from_2d_model(model_2d)
        return ThreeDeeModels._2D_MODEL_CACHE[model_2d]


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
_PLAYER_C = None
_BLOCKS = None
_OVERWORLD = None
_UI = None
_DECORATIONS = None
_LEVEL_BUILDER = None
_STARS = None

_CUTSCENES = {}    # sheet_id -> Sheet
_3D_TEXTURES = {}  # sheet_id -> TextureSheet


def object_sheet() -> _ObjectSheet:
    return _OBJECTS


def _player_c_sheet() -> _PlayerCSheet:
    return _PLAYER_C


def block_sheet() -> _BlockSheet:
    return _BLOCKS


def overworld_sheet() -> _OverworldSheet:
    return _OVERWORLD


def ui_sheet() -> _UiSheet:
    return _UI


def decoration_sheet() -> _DecorationSheet:
    return _DECORATIONS


def level_builder_sheet() -> _LevelBuilderSheet:
    return _LEVEL_BUILDER


def star_sheet() -> _StarSheet:
    return _STARS


def cutscene_image(sheet_type) -> sprites.ImageModel:
    if sheet_type in _CUTSCENES and _CUTSCENES[sheet_type] is not None:
        return _CUTSCENES[sheet_type].get_img()


def initialize_sheets() -> typing.List[spritesheets.SpriteSheet]:
    global _OBJECTS, _PLAYER_C, _BLOCKS, _OVERWORLD, _CUTSCENES, _UI, _DECORATIONS, _LEVEL_BUILDER, _STARS
    _OBJECTS = _ObjectSheet()
    _PLAYER_C = _PlayerCSheet()
    _BLOCKS = _BlockSheet()
    _UI = _UiSheet()
    _DECORATIONS = _DecorationSheet()
    _OVERWORLD = _OverworldSheet()
    _LEVEL_BUILDER = _LevelBuilderSheet()
    _STARS = _StarSheet()

    all_sheets = [_OBJECTS, _PLAYER_C, _BLOCKS, _OVERWORLD, _UI, _DECORATIONS, _LEVEL_BUILDER, _STARS]

    for sheet_id in CutsceneTypes.ALL_TYPES:
        _CUTSCENES[sheet_id] = spritesheets.SingleImageSheet(sheet_id)
        all_sheets.append(_CUTSCENES[sheet_id])

    for id_and_file in TextureSheetTypes.ALL_TYPES:
        sheet_id, filepath = id_and_file
        _3D_TEXTURES[sheet_id] = TextureSheet(sheet_id, filepath)
        all_sheets.append(_3D_TEXTURES[sheet_id])

    ThreeDeeModels.load_models_from_disk()

    return all_sheets


