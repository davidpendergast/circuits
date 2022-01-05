import traceback
import os

import configs
import src.utils.util as util
import src.game.colors as colors


class SaveAndLoadJsonBlob:

    def __init__(self):
        self.json_blob = {}

    def load_from_disk(self, filepath) -> 'SaveAndLoadJsonBlob':
        try:
            print("INFO: loading {}...".format(filepath))
            if os.path.exists(filepath):
                json_blob = util.load_json_from_path(filepath)
                for k in json_blob:
                    self.set(k, self._safe_clean(k, json_blob[k]))
                print("INFO: file loaded successfully")
            else:
                print("INFO: file not found, using defaults")
        except Exception:
            print("ERROR: failed to load data from \"{}\"".format(filepath))
            traceback.print_exc()

        return self

    def save_to_disk(self, filepath):
        try:
            if os.path.exists(filepath):
                print("INFO: overwriting {}...".format(filepath))
            else:
                print("INFO: creating {}...".format(filepath))
            util.save_json_to_path(self.json_blob, filepath, make_pretty=True)
            print("INFO: saved data successfully")
        except Exception:
            print("ERROR: failed to write {}".format(filepath))
            traceback.print_exc()

    def _safe_clean(self, attrib, new_val):
        try:
            return self.clean(attrib, new_val)
        except Exception:
            print("ERROR: failed to clean value for attribute {}: {}".format(attrib, str(new_val)))
            traceback.print_exc()
            return self.get_default_val(attrib)

    def get_default_val(self, attrib):
        raise NotImplementedError()

    def clean(self, attrib, new_val):
        raise NotImplementedError()

    def get(self, attrib):
        if attrib in self.json_blob:
            return self.json_blob[attrib]
        else:
            return self.get_default_val(attrib)

    def set(self, attrib, val):
        if attrib in self.json_blob and self.json_blob != val:
            old_val = self.json_blob[attrib]
        else:
            old_val = None
        self.json_blob[attrib] = val
        self.value_changed(attrib, old_val, val)

    def value_changed(self, attrib, old_val, new_val):
        pass


class SaveData(SaveAndLoadJsonBlob):

    COMPLETED_LEVELS = "completed_levels"
    IN_GAME_PLAYTIME = "in_game_playtime"  # number of ticks in a RealGameScene.
    TOTAL_PLAYTIME = "total_playtime"      # number of ticks spent with the game open

    _DEFAULTS = {
        COMPLETED_LEVELS: {},
        IN_GAME_PLAYTIME: 0,
        TOTAL_PLAYTIME: 0
    }

    def __init__(self):
        super().__init__()

    def get_default_val(self, attrib):
        if attrib in SaveData._DEFAULTS:
            return SaveData._DEFAULTS[attrib]
        else:
            return None

    def clean(self, attrib, new_val):
        if attrib == SaveData.COMPLETED_LEVELS:
            return {k: new_val[k] for k in new_val if (new_val[k] is not None and new_val[k] >= 0)}
        elif attrib in (SaveData.IN_GAME_PLAYTIME, SaveData.TOTAL_PLAYTIME):
            return int(new_val)
        else:
            raise ValueError("unrecognized attribute: {}".format(attrib))

    def completed_levels(self) -> dict:
        return self.get(SaveData.COMPLETED_LEVELS)

    def is_completed(self, level_id):
        return self.get_time(level_id) is not None

    def get_time(self, level_id):
        if level_id in self.completed_levels():
            t = self.completed_levels()[level_id]
            if t is not None and t >= 0:
                return t
        else:
            return None

    def set_completed(self, level_id, completion_time):
        c = self.completed_levels()

        if completion_time is not None and completion_time >= 0:
            c[level_id] = completion_time
        elif level_id in c:
            del c[level_id]

        self.set(SaveData.COMPLETED_LEVELS, c)

    def get_total_playtime(self):
        return self.get(SaveData.TOTAL_PLAYTIME)

    def get_total_in_game_playtime(self):
        return self.get(SaveData.IN_GAME_PLAYTIME)


class Settings(SaveAndLoadJsonBlob):

    SHOW_LIGHTING = "show_lighting"

    MUTE_MUSIC = "mute_music"
    MUSIC_VOLUME = "music_volume"

    MUTE_EFFECTS = "mute_effects"
    EFFECTS_VOLUME = "effects_volume"

    _DEFAULTS = {
        SHOW_LIGHTING: True,
        MUTE_MUSIC: False,
        MUSIC_VOLUME: 0.25,
        MUTE_EFFECTS: False,
        EFFECTS_VOLUME: 1
    }

    def __init__(self):
        super().__init__()

    def get_default_val(self, attrib):
        if attrib in Settings._DEFAULTS:
            return Settings._DEFAULTS[attrib]
        else:
            return None

    def clean(self, attrib, new_val):
        if Settings.SHOW_LIGHTING == attrib:
            return bool(new_val)
        else:
            return new_val
            # return super().clean(attrib, new_val)

    def value_changed(self, attrib, old_val, new_val):
        if attrib in (Settings.MUTE_MUSIC, Settings.MUSIC_VOLUME):
            import src.game.songsystem as songsystem
            songsystem.get_instance().mark_dirty()

    def music_volume(self):
        return 0.0 if self.get(Settings.MUTE_MUSIC) else float(self.get(Settings.MUSIC_VOLUME))

    def effects_volume(self):
        return 0.0 if self.get(Settings.MUTE_EFFECTS) else float(self.get(Settings.EFFECTS_VOLUME))


class GlobalState:

    def __init__(self):
        self.debug_render = False       # draw collision boxes
        self.player_type_override = None

        self.cell_size = 16             # affects collisions
        self.subpixel_resolution = 10   # affects movement

        self._tick_count = 0

        self._save_data = SaveData()
        self._settings = Settings()

        self._should_quit_for_real = False

        self._fullscreen_fade_sprite = None
        self._fullscreen_fade_info = None  # (ticks_active, duration, opacity, end_opacity, color, end_color)

    def tick_count(self):
        return self._tick_count

    def anim_tick(self):
        return self.tick_count() // 4

    def inc_in_game_playtime(self):
        self._save_data.set(SaveData.IN_GAME_PLAYTIME, self._save_data.get_total_in_game_playtime() + 1)

    def update(self):
        self._update_fullscreen_fade()
        self._tick_count += 1
        self._save_data.set(SaveData.TOTAL_PLAYTIME, self._save_data.get_total_playtime() + 1)

    def all_sprites(self):
        if self._fullscreen_fade_sprite is not None:
            yield self._fullscreen_fade_sprite

    def do_fullscreen_fade(self, duration, color, start_opacity, end_opacity, end_color=None):
        end_color = end_color if end_color is not None else color
        self._fullscreen_fade_info = (0, duration, start_opacity, end_opacity, color, end_color)
        self._fullscreen_fade_sprite = None

    def do_simple_fade_in(self):
        self.do_fullscreen_fade(15, colors.PERFECT_BLACK, 1, 0)

    def _update_fullscreen_fade(self):
        if self._fullscreen_fade_info is not None:
            ticks_active, duration, start_opacity, end_opacity, start_color, end_color = self._fullscreen_fade_info

            if ticks_active <= duration:
                # XXX holy bad project structure batman
                import src.engine.renderengine as renderengine
                import src.engine.sprites as sprites
                import src.engine.spritesheets as spritesheets
                import src.game.spriteref as spriteref

                if self._fullscreen_fade_sprite is None:
                    self._fullscreen_fade_sprite = sprites.ImageSprite.new_sprite(spriteref.ULTRA_OMEGA_GAMMA_TOP_IMAGE_LAYER)

                screen_size = renderengine.get_instance().get_game_size()

                prog = ticks_active / duration
                opacity = util.linear_interp(start_opacity, end_opacity, prog)
                color = util.linear_interp(start_color, end_color, prog)

                self._fullscreen_fade_sprite = self._fullscreen_fade_sprite.update(
                    new_model=spritesheets.get_white_square_img(opacity=opacity),
                    new_raw_size=screen_size,
                    new_color=color)

                self._fullscreen_fade_info = (ticks_active + 1, duration, start_opacity, end_opacity, start_color, end_color)
            else:
                self._fullscreen_fade_info = None
                self._fullscreen_fade_sprite = None
        else:
            self._fullscreen_fade_sprite = None

    def get_save_data(self) -> SaveData:
        return self._save_data

    def get_settings(self) -> Settings:
        return self._settings

    def load_data_from_disk(self):
        self._save_data.load_from_disk(util.user_data_path(configs.save_data_path, forcelocal=configs.use_local_paths))
        self._settings.load_from_disk(util.user_data_path(configs.settings_path, forcelocal=configs.use_local_paths))

    def save_data_to_disk(self):
        self._save_data.save_to_disk(util.user_data_path(configs.save_data_path, forcelocal=configs.use_local_paths))
        self._settings.save_to_disk(util.user_data_path(configs.settings_path, forcelocal=configs.use_local_paths))

    def quit_game_for_real(self):
        self._should_quit_for_real = True

    def should_exit(self):
        return self._should_quit_for_real


_INSTANCE = GlobalState()


def set_instance(gstate):
    global _INSTANCE
    _INSTANCE = gstate


def get_instance() -> GlobalState:
    global _INSTANCE
    return _INSTANCE

