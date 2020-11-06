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
SOFT_RESET = "soft_reset"

NEXT_LEVEL_DEBUG = "next"
TOGGLE_SPRITE_MODE_DEBUG = "toggle_sprite_mode"
TOGGLE_PLAYER_TYPE = "toggle_player_type"
SAVE_LEVEL_DEBUG = "save_level_debug"
TOGGLE_EDIT_MODE = "toggle_edit_mode"

MOVE_SELECTION_UP = "move_selection_up"
MOVE_SELECTION_LEFT = "move_selection_left"
MOVE_SELECTION_DOWN = "move_selection_down"
MOVE_SELECTION_RIGHT = "move_selection_right"

MOVE_CAMERA_UP = "move_camera_up"
MOVE_CAMERA_LEFT = "move_camera_left"
MOVE_CAMERA_DOWN = "move_camera_down"
MOVE_CAMERA_RIGHT = "move_camera_right"

CYCLE_SELECTION_FORWARD = "cycle_selection_forward"
CYCLE_SELECTION_BACKWARD = "cycle_selection_backward"

SHRINK_SELECTION_VERT = "shrink_selection_vert"
SHRINK_SELECTION_HORZ = "shrink_selection_horz"

GROW_SELECTION_VERT = "grow_selection_vert"
GROW_SELECTION_HORZ = "grow_selection_horz"

UNDO = "undo"
REDO = "redo"
DELETE = "delete_selection"

INCREASE_EDIT_RESOLUTION = "increase_edit_resolution"
DECREASE_EDIT_RESOLUTION = "decrease_edit_resolution"

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

