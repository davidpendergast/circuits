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
        self._binds = {}  # action_code -> Binding
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

    def get_binding_or_none(self, action_code) -> 'Binding':
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

    def get_keys(self, action_code) -> 'Binding':
        if action_code not in self._binds:
            raise ValueError("unrecognized action code: {}".format(action_code))
        else:
            return self._binds[action_code]


def get_instance() -> KeyBindings:
    return _INSTANCE


_MOD_TO_KEYS_MAPPING = {}  # mod_id -> list of key_ids (ex. KMOD_CTRL -> [K_LCTRL, R_RCTRL])
_KEY_TO_MOD_MAPPING = {}   # key_id -> mod_ids (ex. R_RCTRL -> [KMOD_CTRL, KMOD_RCTRL])

def _add_mod_mapping(mod_id, key_ids):
    key_ids = util.listify(key_ids)
    _MOD_TO_KEYS_MAPPING[mod_id] = key_ids
    for k in key_ids:
        _KEY_TO_MOD_MAPPING[k] = mod_id

_add_mod_mapping(pygame.KMOD_CTRL, [pygame.K_LCTRL, pygame.K_RCTRL])
_add_mod_mapping(pygame.KMOD_LCTRL, pygame.K_LCTRL)
_add_mod_mapping(pygame.KMOD_RCTRL, pygame.K_RCTRL)

_add_mod_mapping(pygame.KMOD_ALT, [pygame.K_LALT, pygame.K_RALT])
_add_mod_mapping(pygame.KMOD_LALT, pygame.K_LALT)
_add_mod_mapping(pygame.KMOD_RALT, pygame.K_RALT)

_add_mod_mapping(pygame.KMOD_SHIFT, [pygame.K_LSHIFT, pygame.K_RSHIFT])
_add_mod_mapping(pygame.KMOD_LSHIFT, pygame.K_LSHIFT)
_add_mod_mapping(pygame.KMOD_RSHIFT, pygame.K_RSHIFT)

def modifier_to_keys(mod_id):
    if mod_id in _MOD_TO_KEYS_MAPPING:
        return _MOD_TO_KEYS_MAPPING[mod_id]
    else:
        return []

def key_to_modifiers(key_id):
    if key_id in _KEY_TO_MOD_MAPPING:
        return _KEY_TO_MOD_MAPPING[key_id]
    else:
        return []


_KEYCODE_TO_KEYNAME = {}
_KEYNAME_TO_KEYCODE = {}

# big yikes
for name in dir(pygame):
    if name.startswith("K_"):
        keycode = getattr(pygame, name)
        if isinstance(keycode, int):
            try:
                keyname = name[2:]  # slice off the K_
                if len(keyname) > 1:
                    keyname = keyname[0].upper() + keyname[1:].lower()
                else:
                    keyname = keyname.upper()

                _KEYCODE_TO_KEYNAME[keycode] = keyname
                _KEYNAME_TO_KEYCODE[keyname] = keycode
            except Exception:
                print("Failed to store key name/code: pygame.{} = {}".format(name, keycode))
                traceback.print_exc()
    elif name.startswith("KMOD_"):
        keycode = getattr(pygame, name)
        if isinstance(keycode, int):
            keyname = None
            if "CTRL" in name:
                keyname = "Ctrl"
            elif "SHIFT" in name:
                keyname = "Shift"
            elif "ALT" in name:
                keyname = "Alt"
            elif "CAPS" in name:
                keyname = "Caps"
            elif "META" in name:
                keyname = "Meta"

            if keyname is not None:
                _KEYCODE_TO_KEYNAME[keycode] = keyname
                _KEYNAME_TO_KEYCODE[keyname] = keycode


def get_pretty_key_name(keycode) -> str:
    if keycode in _KEYCODE_TO_KEYNAME:
        return _KEYCODE_TO_KEYNAME[keycode]
    else:
        return None


def get_keycode(keyname) -> str:
    if keyname in _KEYNAME_TO_KEYCODE:
        return _KEYNAME_TO_KEYCODE[keyname]
    else:
        return None


_ALL_MODS = [pygame.KMOD_CTRL, pygame.KMOD_LCTRL, pygame.KMOD_RCTRL,
             pygame.KMOD_SHIFT, pygame.KMOD_LSHIFT, pygame.KMOD_RSHIFT,
             pygame.KMOD_ALT, pygame.KMOD_LALT, pygame.KMOD_RALT,
             pygame.KMOD_CAPS,
             pygame.KMOD_META, pygame.KMOD_LMETA, pygame.KMOD_RMETA,
             pygame.KMOD_MODE, pygame.KMOD_NONE, pygame.KMOD_NUM]


_ALL_MOD_KEYS = util.flatten_list([modifier_to_keys(_m) for _m in _ALL_MODS])


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

    def __len__(self):
        return len(self.keycode)

    def _mods_satisfied(self, input_state):
        require_exact = False
        allowed_keys = set()
        for m in self.mods:
            if m == pygame.KMOD_NONE:
                # if KMOD_NONE is here, that means other mods must match exactly (i.e. no extra mod keys held).
                require_exact = True
            else:
                keys_that_satisfy_mod = modifier_to_keys(m)
                if not input_state.is_held(keys_that_satisfy_mod):
                    return False
                else:
                    allowed_keys.update(keys_that_satisfy_mod)

        if require_exact:
            prohibited_keys = [k for k in _ALL_MOD_KEYS if k not in allowed_keys]
            if input_state.is_held(prohibited_keys):
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

    _ARROW_MAPPING = {
        "up": "↑", "left": "←", "down": "↓", "right": "→"
    }

    def get_pretty_names(self, ignore_mods=False, convert_arrows=True):
        res = []
        for code in self.keycode:
            name = ""
            if not ignore_mods:
                for mod in self.mods:
                    modname = get_pretty_key_name(mod)
                    if modname is not None:
                        name += "{} + ".format(modname)
            keyname = get_pretty_key_name(code)
            if keyname is not None:
                if convert_arrows and keyname.lower() in Binding._ARROW_MAPPING:
                    keyname = Binding._ARROW_MAPPING[keyname.lower()]
                name += keyname
                res.append(name)
        return res

    def to_pretty_string_for_display(self, first_only=True, ignore_mods=False, delim=", ", final_delim=", or ", convert_arrows=True):
        all_keys = self.get_pretty_names(ignore_mods=ignore_mods, convert_arrows=convert_arrows)
        if len(all_keys) == 0:
            return "?"
        else:
            first = all_keys[0]
            if first_only:
                # returns "[MOD1 + MOD2 + ... + MODN +] K1"
                return first
            else:
                # returns "[MOD1 + MOD2 + ... + MODN +] K1, K2, ..., or KM"
                all_keys = self.get_pretty_names(ignore_mods=True)[1:]
                res = first
                for i, k in enumerate(all_keys):
                    if i < len(all_keys) - 1:
                        res += delim + k
                    else:
                        res += final_delim + k
                return res

    def __repr__(self):
        for s in self.get_pretty_names():
            return s  # return first binding
        return " "    # if it's unbound


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
