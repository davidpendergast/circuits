import pygame
from src.utils.util import Utils
import traceback


_MASTER_VOLUME = 1.0

_LOADED_EFFECTS = {}  # effect_id -> Effect object

_RECENTLY_PLAYED = {}  # effect_id -> ticks since last play

RECENCY_LIMIT = 4  # if an effect was already played X ticks ago, don't play it again


def set_volume(volume):
    global _MASTER_VOLUME
    _MASTER_VOLUME = Utils.bound(volume, 0.0, 1.0)


def update():
    to_remove = []
    for effect in _RECENTLY_PLAYED:
        if _RECENTLY_PLAYED[effect] >= RECENCY_LIMIT:
            to_remove.append(effect)
        else:
            _RECENTLY_PLAYED[effect] = _RECENTLY_PLAYED[effect] + 1
    for effect in to_remove:
        del _RECENTLY_PLAYED[effect]


def play_sound(sound):
    """
    :param sound: either an effect_path, or a tuple (effect_path, volume)
    """
    if sound is None:
        return

    if isinstance(sound, tuple):
        effect_path = sound[0]
        volume = sound[1]
    else:
        effect_path = sound
        volume = 1.0

    if _MASTER_VOLUME == 0 or volume <= 0 or effect_path is None:
        return

    if effect_path in _RECENTLY_PLAYED:
        return

    if effect_path in _LOADED_EFFECTS:
        effect = _LOADED_EFFECTS[effect_path]
        effect.set_volume(_MASTER_VOLUME * volume)
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
        # print("INFO: playing sound effect: {}".format(effect_path))
        effect.play()

