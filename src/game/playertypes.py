import traceback

import src.utils.util as util
import src.game.const as const
import src.game.spriteref as spriteref

import src.game.soundref as soundref
import src.engine.sounds as sounds


DEFAULT_GRAVITY = -0.15 / 16


class PlayerType:

    def __init__(self, name, color_id, id_num, size=(0.75, 1.75),
                 move_speed=7.5,
                 jump_height=3.2, jump_duration=None, gravity=DEFAULT_GRAVITY,
                 can_walljump=False, can_fly=False, can_crouch=False, can_grab=False, can_be_grabbed=False,
                 can_swap=False, can_be_swapped_with=True,
                 anim_rate_overrides=None, should_ever_xflip=True, breaks_blocks=False, sound_overrides=None):
        self._name = name
        self._color_id = color_id
        self._id = id_num
        self._size = size

        self._move_speed = move_speed

        jump_info = util.calc_missing_jump_info(H=jump_height, T=jump_duration, g=gravity)
        self._jump_height = jump_info.H
        self._jump_gravity = jump_info.g
        self._jump_duration = jump_info.T
        self._jump_vel = jump_info.vel

        self._can_walljump = can_walljump
        self._can_fly = can_fly
        self._can_crouch = can_crouch
        self._can_grab = can_grab
        self._can_be_grabbed = can_be_grabbed
        self._can_swap = can_swap
        self._can_be_swapped_with = can_be_swapped_with
        self._breaks_blocks = breaks_blocks

        self._should_ever_xflip = should_ever_xflip

        self._anim_rates = {
            spriteref.PlayerStates.WALKING: 1,
            spriteref.PlayerStates.CROUCH_WALKING: 2,
            spriteref.PlayerStates.IDLE: 8,
            spriteref.PlayerStates.CROUCH_IDLE: 8,
            spriteref.PlayerStates.AIRBORNE: 8,
            spriteref.PlayerStates.WALLSLIDE: 8
        }

        if anim_rate_overrides is not None:
            self._anim_rates.update(anim_rate_overrides)

        self._sound_mappings = {}
        if sound_overrides is not None:
            self._sound_mappings.update(sound_overrides)

    def get_id(self):
        return self._id

    def get_color_id(self):
        return self._color_id

    def get_name(self):
        return self._name

    def get_letter(self):
        return self.get_name()

    def translate_sound(self, sound_id):
        if isinstance(sound_id, list):
            effect_path, _ = sounds.resolve_path_and_volume(sound_id)
            if effect_path in self._sound_mappings:
                return self._sound_mappings[effect_path]
            else:
                return sound_id
        elif isinstance(sound_id, (tuple, str)) and sound_id in self._sound_mappings:
            return self._sound_mappings[sound_id]
        else:
            return sound_id

    def can_walljump(self):
        return self._can_walljump

    def can_fly(self):
        return self._can_fly

    def can_crouch(self):
        return self._can_crouch

    def can_grab(self):
        return self._can_grab

    def can_be_grabbed(self):
        return self._can_be_grabbed

    def can_break_blocks(self):
        return self._breaks_blocks

    def can_swap(self):
        return self._can_swap

    def can_be_swapped_with(self):
        return self._can_be_swapped_with

    def get_size(self):
        """returns: size of player in cells"""
        return self._size

    def get_jump_height(self):
        """returns: maximum jump height in cells"""
        return self._jump_height

    def get_jump_duration(self):
        """returns: jump duration in ticks"""
        return self._jump_duration

    def get_jump_info(self):
        """returns: jump info in cells and ticks"""
        return util.JumpInfo(self._jump_height, self._jump_duration, self._jump_gravity, self._jump_vel)

    def get_move_speed(self):
        """returns: maximum x velocity in cells per second"""
        return self._move_speed

    def get_anim_rate(self, player_state, player_ent):
        player_state = player_state.as_non_carrying()
        if player_state in self._anim_rates:
            rate = self._anim_rates[player_state]
            if isinstance(rate, int) or isinstance(rate, float):
                return int(rate)
            else:
                try:
                    # should be a lambda: Entity -> int
                    return rate(player_ent)
                except Exception:
                    print("{} failed to calculate animation rate for {}, {}".format(self, player_state, player_ent))
                    traceback.print_exc()
        else:
            return 1  # very fast because something is very wrong

    def should_ever_xflip(self):
        return self._should_ever_xflip

    def get_player_img(self, player_state, frame=0):
        return spriteref.object_sheet().get_player_sprite(self._id, player_state, frame)

    def __eq__(self, other):
        if isinstance(other, PlayerType):
            return self._id == other._id
        else:
            return None

    def __hash__(self):
        return hash(self._id)

    def __repr__(self):
        return type(self).__name__ + "({}, {})".format(self.get_name(), self.get_id())


class PlayerTypes:

    FAST = PlayerType("A", 1, const.PLAYER_FAST, size=(0.75, 1.75), can_walljump=True, can_crouch=True,
                      move_speed=7.5, jump_height=3.2)
    SMALL = PlayerType("B", 2, const.PLAYER_SMALL, size=(0.875, 0.75), can_be_grabbed=True, can_crouch=True,
                       move_speed=5.5, jump_height=2.1,
                       sound_overrides={
                           soundref.PLAYER_JUMP: soundref.ModernUI.generic_button_9,
                       })
    HEAVY = PlayerType("C", 3, const.PLAYER_HEAVY, size=(1.25, 1.25), can_grab=True,
                       move_speed=5, jump_height=3.2, can_crouch=True, breaks_blocks=True,
                       anim_rate_overrides={
                           spriteref.PlayerStates.WALKING: 1
                       })
    FLYING = PlayerType("D", 4, const.PLAYER_FLYING, size=(0.75, 1.5),
                        can_fly=True, can_swap=False, can_be_swapped_with=False,
                        can_crouch=True, move_speed=6, jump_height=4.3, gravity=DEFAULT_GRAVITY / 2,
                        should_ever_xflip=False,
                        anim_rate_overrides={
                            spriteref.PlayerStates.AIRBORNE: lambda _ent: 1 if _ent.get_y_vel() < 0 else 1,
                            spriteref.PlayerStates.WALKING: 2,
                            spriteref.PlayerStates.IDLE: 4
                        })

    _ALL_TYPES = [FAST, SMALL, HEAVY, FLYING]

    @staticmethod
    def all_types():
        return PlayerTypes._ALL_TYPES

    @staticmethod
    def get_type(ident, or_else_throw=True):
        for ptype in PlayerTypes._ALL_TYPES:
            if ident == ptype.get_id() or str(ident).upper() == ptype.get_letter().upper():
                return ptype
        if or_else_throw:
            raise ValueError("unrecognized player type: {}".format(ident))
        else:
            return None
