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

    def set_binding(self, action_code, keylist):
        if keylist is None:
            if action_code in self._binds:
                del self._binds[action_code]
        else:
            keylist = util.listify(keylist)
            self._binds[action_code] = keylist

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

