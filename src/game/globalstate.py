import src.utils.util as util
import src.game.colors as colors


class SaveAndLoadJsonBlob:

    def __init__(self, filepath):
        self.filepath = filepath
        self.json_blob = {}
        self.set_defaults()

    def load_from_disk(self) -> 'SaveAndLoadJsonBlob':
        # TODO implement
        return self

    def save_to_disk(self, filepath=None):
        pass  # TODO

    def set_defaults(self):
        pass


class SaveData(SaveAndLoadJsonBlob):

    COMPLETED_LEVELS = "completed_levels"

    def __init__(self, filepath):
        super().__init__(filepath)

    def set_defaults(self):
        self.json_blob[SaveData.COMPLETED_LEVELS] = {}  # level_id -> completion time (in ticks)

    def completed_levels(self) -> dict:
        return self.json_blob[SaveData.COMPLETED_LEVELS]


class Settings(SaveAndLoadJsonBlob):

    SHOW_LIGHTING = "show_lighting"

    def __init__(self, filepath):
        super().__init__(filepath)

    def set_defaults(self):
        self.json_blob[Settings.SHOW_LIGHTING] = True

    def get(self, attrib):
        if attrib in self.json_blob:
            return self.json_blob[attrib]
        else:
            return None

    def set(self, attrib, val):
        self.json_blob[attrib] = val


class GlobalState:

    def __init__(self):
        self.debug_render = False       # draw collision boxes
        self.player_type_override = None

        self.cell_size = 16             # affects collisions
        self.subpixel_resolution = 10   # affects movement

        self._tick_count = 0

        self._save_data = SaveData("save_data.txt").load_from_disk()
        self._settings = Settings("settings.txt").load_from_disk()

        self._should_quit_for_real = False

        self._fullscreen_fade_sprite = None
        self._fullscreen_fade_info = None  # (ticks_active, duration, start_opacity, end_opacity, start_color, end_color)

    def tick_count(self):
        return self._tick_count

    def anim_tick(self):
        return self.tick_count() // 4

    def update(self):
        self._update_fullscreen_fade()

        self._tick_count += 1

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

    def save_data(self) -> SaveData:
        return self._save_data

    def settings(self) -> Settings:
        return self._settings

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

