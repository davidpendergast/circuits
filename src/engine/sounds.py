import pygame
import src.utils.util as util
import traceback
import random


_MASTER_VOLUME = 1.0

_LOADED_EFFECTS = {}  # effect_id -> Effect object

_RECENTLY_PLAYED = {}  # effect_id -> ticks since last play

RECENCY_LIMIT = 4  # if an effect was already played X ticks ago, don't play it again


def set_volume(volume):
    global _MASTER_VOLUME
    _MASTER_VOLUME = util.bound(volume, 0.0, 1.0)


def update():
    to_remove = []
    for effect in _RECENTLY_PLAYED:
        if _RECENTLY_PLAYED[effect] >= RECENCY_LIMIT:
            to_remove.append(effect)
        else:
            _RECENTLY_PLAYED[effect] = _RECENTLY_PLAYED[effect] + 1
    for effect in to_remove:
        del _RECENTLY_PLAYED[effect]


def resolve_path_and_volume(sound, vol=1.0):
    """
    sound: either an effect_path, or a tuple (effect_path, volume), or a collection of sounds (also a path or tuple)
           (in which case one will be chosen randomly).
    vol: volume multiplier for the sound.
    """
    if sound is None or len(sound) == 0:
        return None, 1.0
    elif isinstance(sound, str):
        return util.resource_path(sound), vol
    elif isinstance(sound, tuple) and len(sound) == 2 and isinstance(sound[1], (int, float)):
        return util.resource_path(sound[0]), sound[1] * vol
    else:
        # it's some kind of collection of sounds
        # XXX hopefully it isn't recursive~
        try:
            all_sounds = [resolve_path_and_volume(item, vol=vol) for item in sound]
            all_sounds = [s for s in all_sounds if s[0] is not None]
            if len(all_sounds) > 0:
                return random.choice(all_sounds)
        except Exception:
            print("ERROR: failed to resolve sound: {}".format(sound))
            traceback.print_exc()

    return None, vol


def play_sound(sound, vol=1.0):
    effect_path, volume = resolve_path_and_volume(sound, vol=vol)

    if _MASTER_VOLUME == 0 or volume <= 0 or effect_path is None:
        return

    if effect_path in _RECENTLY_PLAYED:
        return

    if effect_path in _LOADED_EFFECTS:
        effect = _LOADED_EFFECTS[effect_path]
    else:
        try:
            effect = pygame.mixer.Sound(effect_path)
            effect.set_volume(_MASTER_VOLUME * volume)
        except Exception:
            print("ERROR: failed to load sound effect {}".format(effect_path))
            traceback.print_exc()
            effect = None
        _LOADED_EFFECTS[effect_path] = effect

    if effect is not None:
        _RECENTLY_PLAYED[effect_path] = 0

        # TODO remove
        # import configs
        # if configs.is_dev:
        #     print("INFO: playing sound effect: {}".format(effect_path))

        effect.set_volume(_MASTER_VOLUME * volume)
        effect.play()

