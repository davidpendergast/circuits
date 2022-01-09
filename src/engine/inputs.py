import pygame

import src.engine.globaltimer as globaltimer
import src.engine.keybinds as keybinds

import configs

_INSTANCE = None  # should access this via get_instance(), at the bottom of the file


def create_instance():
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = InputState()
        return _INSTANCE
    else:
        raise ValueError("There is already an InputState initialized.")


class InputState:

    def __init__(self):
        self._current_time = 0
        self._pressed_this_frame = {}  # keycode -> num times
        self._held_keys = {}           # keycode -> time pressed

        self._ascii_pressed_this_frame = []  # list of ascii chars typed this frame

        self._mouse_pos_last_frame = (0, 0)
        self._mouse_pos = (0, 0)

        # to track mouse drags
        self._mouse_down_pos = {}  # mouse code -> (x, y, tick_pressed)
        self._end_drags_when_mouse_leaves_window = False  # configurable
    
    def set_key(self, key, held, ascii_val=''):
        if held:
            if key not in self._pressed_this_frame:
                self._pressed_this_frame[key] = 1
                if ascii_val is not None and len(ascii_val) > 0:
                    self._ascii_pressed_this_frame.append(ascii_val)
            else:
                self._pressed_this_frame[key] += 1

        if held and key not in self._held_keys:
            self._held_keys[key] = self._current_time
        elif not held and key in self._held_keys:
            del self._held_keys[key]

    def to_key_code(self, mouse_button):
        return "MOUSE_BUTTON_" + str(mouse_button)

    def set_mouse_down(self, down, button=1):
        keycode = self.to_key_code(button)
        self.set_key(keycode, down)

        m_pos = self.mouse_pos() if self.mouse_in_window() else (-1, -1)
        if down:
            self._mouse_down_pos[keycode] = (m_pos[0], m_pos[1], self._current_time)
        else:
            if keycode in self._mouse_down_pos:
                del self._mouse_down_pos[keycode]

    def set_mouse_pos(self, pos):
        if pos is not None and self._mouse_pos != pos:
            # update any mouse downs that also happened this frame
            for k in self._mouse_down_pos:
                x, y, tick = self._mouse_down_pos[k]
                if tick == self._current_time:
                    self._mouse_down_pos[k] = (pos[0], pos[1], tick)

        self._mouse_pos = pos
    
    def is_held(self, key):
        """:param key - Binding, single key, or list of keys"""
        if isinstance(key, list) or isinstance(key, tuple):
            return any(map(lambda k: self.is_held(k), key))
        elif isinstance(key, keybinds.Binding):
            return key.is_held(self)
        elif isinstance(key, int):
            return key in self._held_keys
        elif isinstance(key, str):
            binding = keybinds.get_instance().get_binding_or_none(key)
            return binding is not None and binding.is_held(self)
        else:
            raise ValueError("Unrecognized key type: {}".format(key))
    
    def time_held(self, key):
        """:param key - Binding, single key, or list of keys"""
        if isinstance(key, list) or isinstance(key, tuple):
            return max(map(lambda k: self.time_held(k), key))
        elif isinstance(key, keybinds.Binding):
            return key.time_held(self)
        elif isinstance(key, int) or (isinstance(key, str) and key.startswith("MOUSE_BUTTON")):
            if key not in self._held_keys:
                return -1
            else:
                return self._current_time - self._held_keys[key]
        elif isinstance(key, str):
            binding = keybinds.get_instance().get_binding_or_none(key)
            return binding is not None and binding.time_held(self)
        else:
            raise ValueError("Unrecognized key type: {}".format(key))

    def was_pressed(self, key):
        """:param key - Binding, single key, the id of a binding, or a list/tuple of any of these"""
        if isinstance(key, list) or isinstance(key, tuple):
            for k in key:
                if self.was_pressed(k):
                    return True
            return False
        elif isinstance(key, keybinds.Binding):
            return key.was_pressed(self)
        elif isinstance(key, int) or (isinstance(key, str) and key.startswith("MOUSE_BUTTON")):
            # it's a single key, hopefully
            return key in self._pressed_this_frame and self._pressed_this_frame[key] > 0
        elif isinstance(key, str):
            binding = keybinds.get_instance().get_binding_or_none(key)
            return binding is not None and binding.was_pressed(self)
        else:
            raise ValueError("Unrecognized key type: {}".format(key))

    def was_pressed_or_held_and_repeated(self, key, delay=configs.key_repeat_delay, freq=configs.key_repeat_period):
        if self.was_pressed(key):
            return True
        elif self.is_held(key):
            held_time = self.time_held(key)
            return held_time > delay and (held_time - delay) % freq == 0
        else:
            return False

    def is_held_four_way(self, left=None, right=None, up=None, down=None):
        x = 0
        if left is not None and self.is_held(left):
            x -= 1
        if right is not None and self.is_held(right):
            x += 1
        y = 0
        if up is not None and self.is_held(up):
            y += 1
        if down is not None and self.is_held(down):
            y -= 1
        return (x, y)

    def was_pressed_four_way(self, left=None, right=None, up=None, down=None):
        x = self.was_pressed_two_way(left, right)
        y = self.was_pressed_two_way(up, down)  # down is always positive
        return (x, y)

    def was_pressed_two_way(self, lower, upper):
        x = 0
        if lower is not None and self.was_pressed(lower):
            x -= 1
        if upper is not None and self.was_pressed(upper):
            x += 1
        return x

    def shift_is_held(self):
        return self.is_held(pygame.K_LSHIFT) or self.is_held(pygame.K_RSHIFT)

    def ctrl_is_held(self):
        return self.is_held(pygame.K_LCTRL) or self.is_held(pygame.K_RCTRL)

    def alt_is_held(self):
        return self.is_held(pygame.K_LALT) or self.is_held(pygame.K_RALT)
    
    def mouse_is_held(self, button=1):
        keycode = self.to_key_code(button)
        return self.is_held(keycode)
    
    def mouse_held_time(self, button=1):
        keycode = self.to_key_code(button)
        return self.time_held(keycode)

    def mouse_was_pressed(self, button=1):
        """
        button: 1 = left, 2 = middle, 3 = right, 4, 5 = something fancy
        """
        keycode = self.to_key_code(button)
        return self.was_pressed(keycode) and self.mouse_in_window()

    def mouse_drag_total(self, button=1):
        """returns: (start_xy, current_xy) or None if not dragging."""
        keycode = self.to_key_code(button)
        if self.mouse_in_window() and self.mouse_is_held(button=button) and keycode in self._mouse_down_pos:
            mouse_pos = self.mouse_pos()
            start_x, start_y, tick = self._mouse_down_pos[keycode]
            if start_x >= 0 and start_y >= 0 and mouse_pos != (start_x, start_y):
                return ((start_x, start_y), mouse_pos)
        return None

    def mouse_drag_this_frame(self, button=1):
        """returns: (last_xy, current_xy) or None if not dragging or there was no movement."""
        if self.mouse_is_dragging(button=button):
            last_pos = self._mouse_pos_last_frame
            cur_pos = self._mouse_pos
            if last_pos is not None and cur_pos is not None and last_pos != cur_pos:
                return (last_pos, cur_pos)

    def mouse_is_dragging(self, button=1):
        return self.mouse_drag_total(button=button) is not None
        
    def mouse_pos(self):
        return self._mouse_pos

    def mouse_moved(self):
        return self._mouse_pos_last_frame != self._mouse_pos
        
    def mouse_in_window(self):
        return self._mouse_pos is not None
    
    def all_held_keys(self):
        return self._held_keys.keys()

    def all_pressed_keys(self):
        return [x for x in self._pressed_this_frame if self._pressed_this_frame[x] > 0]

    def all_pressed_ascii_keys(self):
        return self._ascii_pressed_this_frame

    def was_anything_pressed(self):
        if len(self.all_pressed_keys()) > 0:
            return True
        else:
            for i in range(0, 3):
                if self.mouse_was_pressed(button=i):
                    return True
        return False

    def pre_update(self):
        """
        Called *before* inputs are passed in.
        """
        self._mouse_pos_last_frame = self._mouse_pos
        self._pressed_this_frame.clear()
        self._ascii_pressed_this_frame.clear()
        
    def update(self):
        """
        Relies on globaltimer.tick_count().
        Remember that this gets called *after* inputs are passed in, and *before* game updates occur.
        """
        self._current_time = globaltimer.tick_count()

        if self._end_drags_when_mouse_leaves_window and not self.mouse_in_window():
            self._mouse_down_pos.clear()


def get_instance() -> InputState:
    return _INSTANCE

