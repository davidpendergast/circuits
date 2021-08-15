import pygame

import traceback

import src.utils.util as util

_INSTANCE = None


def create_instance():
    global _INSTANCE
    _INSTANCE = KeyBindings()
    return _INSTANCE


class KeyBindings:

    def __init__(self):
        self._binds = {}  # action_code -> list of keys
        self._global_bindings = {}  # int: key_code -> (str: name, lambda: action)

    def load_from_file(self, filepath):
        pass

    def set_binding(self, action_code, binding):
        if binding is None:
            if action_code in self._binds:
                del self._binds[action_code]
        elif isinstance(binding, Binding):
            self._binds[action_code] = binding
        else:
            # assume it's a raw keycode or list of keycodes
            keylist = util.listify(binding)
            self._binds[action_code] = Binding(keylist)

    def get_binding(self, action_code):
        if action_code in self._binds:
            return self._binds[action_code]
        else:
            return None

    def set_global_action(self, key, name, action):
        if action is None:
            if key in self._global_bindings:
                del self._global_bindings[key]
        else:
            if not callable(action):
                raise ValueError("action \"{}\" isn't callable: {}".format(name, action))
            if key in self._global_bindings and self._global_bindings[key][0] != name:
                print("WARN: overwriting global key action \"{}\" with \"{}\" (key={})".format(
                    self._global_bindings[key][0], name, util.stringify_key(key)
                ))
            self._global_bindings[key] = (name, action)

    def do_global_action_if_necessary(self, key):
        if key in self._global_bindings:
            name, action = self._global_bindings[key]
            try:
                action()
            except Exception:
                print("ERROR: global key action \"{}\" failed with exception".format(name))
                traceback.print_exc()

    def get_keys(self, action_code):
        if action_code not in self._binds:
            raise ValueError("unrecognized action code: {}".format(action_code))
        else:
            return self._binds[action_code]


def get_instance() -> KeyBindings:
    return _INSTANCE


def modifier_to_key(key):
    if key == pygame.KMOD_CTRL:
        return [pygame.K_LCTRL, pygame.K_RCTRL]
    elif key == pygame.KMOD_LCTRL:
        return pygame.K_LCTRL
    elif key == pygame.KMOD_RCTRL:
        return pygame.K_RCTRL

    elif key == pygame.KMOD_ALT:
        return [pygame.K_LALT, pygame.K_RALT]
    elif key == pygame.KMOD_LALT:
        return pygame.K_LALT
    elif key == pygame.KMOD_RALT:
        return pygame.K_RALT

    elif key == pygame.KMOD_SHIFT:
        return [pygame.K_LSHIFT, pygame.K_RSHIFT]
    elif key == pygame.KMOD_LSHIFT:
        return pygame.K_LSHIFT
    elif key == pygame.KMOD_RSHIFT:
        return pygame.K_RSHIFT

    else:
        return []


_ALL_MODS = [pygame.KMOD_CTRL, pygame.KMOD_LCTRL, pygame.KMOD_RCTRL,
             pygame.KMOD_SHIFT, pygame.KMOD_LSHIFT, pygame.KMOD_RSHIFT,
             pygame.KMOD_ALT, pygame.KMOD_LALT, pygame.KMOD_RALT,
             pygame.KMOD_CAPS,
             pygame.KMOD_META, pygame.KMOD_LMETA, pygame.KMOD_RMETA,
             pygame.KMOD_MODE, pygame.KMOD_NONE, pygame.KMOD_NUM]


_ALL_MOD_KEYS = util.flatten_list([modifier_to_key(_m) for _m in _ALL_MODS])


def _is_mod(code):
    return code in _ALL_MODS


class Binding:

    def __init__(self, keycode, mods=()):
        """
        keycode: a pygame keycode or list of pygame keycodes.
        mods: a pygame key modifier or a list of pygame key modifiers.
        """
        self.keycode = util.tuplify(keycode)
        self.mods = util.tuplify(mods)

    def _mods_satisfied(self, input_state):
        for m in self.mods:
            if m == pygame.KMOD_NONE:
                if input_state.is_held(_ALL_MOD_KEYS):
                    # if we have NO_MODS, and any mods are held, fail the binding
                    return False
            elif not input_state.is_held(modifier_to_key(m)):
                return False
        return True

    def is_held(self, input_state):
        if not input_state.is_held(self.keycode):
            return False
        return self._mods_satisfied(input_state)

    def was_pressed(self, input_state):
        if not input_state.was_pressed(self.keycode):
            return False
        return self._mods_satisfied(input_state)

    def time_held(self, input_state):
        min_time = input_state.time_held(self.keycode)
        if min_time < 0:
            return min_time
        else:
            for m in self.mods:
                min_time = min(min_time, modifier_to_key(m))
                if min_time < 0:
                    return min_time
        return min_time


def pg_const_val_to_var_name(const_val: int, starts_with="K_", default=None) -> str:
    """
    Converts a pygame constant's value to its pygame variable name (filtering by an optional prefix).
    This is useful for writing keys and such to disk in a version-safe way. (Constants are not guaranteed
    to remain the same between different pygame versions).

    Example: pygame.K_SPACE (32) -> "K_SPACE"
    """
    for key in pygame.__dict__:
        if str(key).startswith(starts_with):
            if pygame.__dict__[key] == const_val:
                return key
    return default


def pg_var_name_to_const_val(varname: str) -> int:
    """
    Converts a pygame constant's variable name to its int value.
    Example: "K_SPACE" -> pygame.K_SPACE (32)
    """
    return getattr(pygame, varname, -1)


if __name__ == "__main__":
    left = pygame.K_LEFT

    maps = {
        "jump": pygame.K_SPACE,
        "left": pygame.K_LEFT,
        "right": pygame.K_RIGHT,
        "pause": pygame.K_p
    }

    sanitized_maps = {k: pg_const_val_to_var_name(maps[k]) for k in maps}
    print("sanitized_maps =", sanitized_maps)

    desanitized_maps = {k: pg_var_name_to_const_val(sanitized_maps[k]) for k in sanitized_maps}
    print("desanitized_maps =", desanitized_maps)
