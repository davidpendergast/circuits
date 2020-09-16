import src.game.colors as colors

# action codes
MOVE_LEFT = "move_left"
MOVE_RIGHT = "move_right"
JUMP = "jump"
CROUCH = "crouch"
ACTION_1 = "action_1"

MENU_UP = "menu_up"
MENU_DOWN = "menu_down"
MENU_RIGHT = "menu_right"
MENU_LEFT = "menu_left"
MENU_ACCEPT = "menu_accept"
MENU_CANCEL = "menu_cancel"

RESET = "reset"

NEXT_LEVEL_DEBUG = "next"
TOGGLE_SPRITE_MODE_DEBUG = "toggle_sprite_mode"
TOGGLE_PLAYER_TYPE = "toggle_player_type"
SAVE_LEVEL_DEBUG = "save_level_debug"

# player ids
PLAYER_FAST = "player_fast"
PLAYER_SMALL = "player_small"
PLAYER_HEAVY = "player_heavy"
PLAYER_FLYING = "player_flying"


ALL_PLAYER_IDS = [PLAYER_FAST, PLAYER_SMALL, PLAYER_HEAVY, PLAYER_FLYING]


_PLAYER_COLOR_MAP = {
    PLAYER_FAST: (colors.BLUE, colors.DARK_BLUE),
    PLAYER_SMALL: (colors.TAN, colors.DARK_TAN),
    PLAYER_HEAVY: (colors.GREEN, colors.DARK_GREEN),
    PLAYER_FLYING: (colors.PURPLE, colors.DARK_PURPLE)
}


def get_player_color(player_type, dark=False):
    if player_type is not None and player_type.get_id() in _PLAYER_COLOR_MAP:
        return _PLAYER_COLOR_MAP[player_type.get_id()][1 if dark else 0]
    else:
        return colors.WHITE

