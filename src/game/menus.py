import traceback
import random
import json
import os
import math

import src.engine.scenes as scenes
import src.game.blueprints as blueprints
import src.game.worldview as worldview
import src.engine.inputs as inputs
import src.engine.keybinds as keybinds
import src.engine.sprites as sprites
import src.engine.sounds as sounds
import src.game.globalstate as gs
import src.engine.renderengine as renderengine
import src.game.const as const
import configs as configs
import src.game.debug as debug
import src.utils.util as util
import src.utils.artutils as artutils
import src.utils.matutils as matutils
import src.game.spriteref as spriteref
import src.game.colors as colors
import src.game.overworld as overworld
import src.game.ui as ui
import src.engine.spritesheets as spritesheets
import src.game.worlds as worlds
import src.game.cinematics as cinematics
import src.game.dialog as dialog
import src.game.songsystem as songsystem
import src.game.soundref as soundref


class CircuitsSceneManager(scenes.SceneManager):

    def __init__(self, cur_scene):
        super().__init__(cur_scene)

    def set_next_scene(self, scene, delay=0, do_fade=True):
        if do_fade and not delay:
            gs.get_instance().do_simple_fade_in()
        super().set_next_scene(scene, delay=delay)


def _make_overworlds_scene():
    # TODO may want to just move this into assets (and del from make_exe too).
    overworlds_base_dir = util.resource_path("overworlds")
    return overworld.OverworldScene.create_new_from_path(overworlds_base_dir)


class MainMenuScene(scenes.Scene):

    def __init__(self):
        scenes.Scene.__init__(self)
        self._title_element = ui.SpriteElement()

        self._options_list = ui.OptionsList(outlined=True)
        self._options_list.add_option("start", lambda: self._do_start())
        if configs.is_dev:  # TODO user-facing level editor
            self._options_list.add_option("create", lambda: self.jump_to_scene(LevelSelectForEditScene(configs.level_edit_dirs)))
        self._options_list.add_option("controls", lambda: self.jump_to_scene(ControlsScene(self)))
        self._options_list.add_option("stats", lambda: self.jump_to_scene(self._make_stats_scene()))
        self._options_list.add_option("credits", lambda: self.jump_to_scene(CreditsScene(self)))
        self._options_list.add_option("exit", lambda: gs.get_instance().quit_game_for_real(), esc_option=True)
        self._options_list.update_sprites()

        self._option_pane_bg = None
        self._option_pane_border = None

        self._version_text_sprite = None
        self._version_text_bg = None

        self.cine_seq = cinematics.CinematicFactory.make_cinematic(cinematics.CinematicScenes.MAIN_MENU)

    def _do_start(self):
        do_instructions = True
        overworld_scene = _make_overworlds_scene()
        if do_instructions:
            next_scene = InstructionsScene(overworld_scene, self)
            sounds.play_sound(soundref.MENU_ACCEPT)
        else:
            next_scene = overworld_scene
            sounds.play_sound(soundref.MENU_START)
        self.jump_to_scene(next_scene)

    def _make_stats_scene(self):
        return StatsScene(None, self, title="Stats")

    def should_do_cursor_updates(self):
        return True

    def get_cursor_id_at(self, xy):
        return self._options_list.get_cursor_id_from_self_and_kids(xy, absolute=True)

    def update(self):
        self.cine_seq.update()
        cam = self.cine_seq.get_camera().get_snapshot()
        renderengine.get_instance().get_layer(spriteref.THREEDEE_LAYER).set_camera(cam)

        self.update_sprites()

        self._title_element.update_self_and_kids()
        self._options_list.update_self_and_kids()

    def update_sprites(self):
        total_size = renderengine.get_instance().get_game_size()

        title_scale = 1.5
        if self._title_element.get_sprite() is None:
            text_sprite = sprites.ImageSprite(spriteref.ui_sheet().title_img, 0, 0, spriteref.UI_FG_LAYER, scale=title_scale)
            self._title_element.set_sprite(text_sprite)

        title_w = self._title_element.get_size()[0]
        title_h = self._title_element.get_size()[1]
        title_x = total_size[0] // 2 - title_w // 2
        title_y = total_size[1] // 4 - title_h // 2
        self._title_element.set_xy((title_x, title_y))

        options_xy = (
            total_size[0] // 2 - title_w // 4 - self._options_list.get_size()[0] // 2,
            title_y + 48 * title_scale  # want it to be "connected" to bottom of title image's border
        )
        self._options_list.set_xy(options_xy)

        if self._option_pane_bg is None:
            model = spritesheets.get_instance().get_sheet(spritesheets.WhiteSquare.SHEET_ID).get_sprite(opacity=0.5)
            self._option_pane_bg = sprites.ImageSprite(model, options_xy[0], options_xy[1], spriteref.UI_BG_LAYER)

        bg_inset = 4
        options_size = self._options_list.get_size()
        options_bg_rect = [
            options_xy[0] - bg_inset,
            options_xy[1] - bg_inset,
            options_size[0] + 2 * bg_inset,
            options_size[1] + 2 * bg_inset
        ]
        self._option_pane_bg = self._option_pane_bg.update(new_x=options_bg_rect[0],
                                                           new_y=options_bg_rect[1],
                                                           new_color=colors.PERFECT_BLACK,
                                                           new_raw_size=(options_bg_rect[2], options_bg_rect[3]))

        if self._option_pane_border is None:
            self._option_pane_border = sprites.BorderBoxSprite(spriteref.UI_BG_LAYER, options_bg_rect,
                                                               all_borders=spriteref.overworld_sheet().border_single_line,
                                                               hollow_center=True,
                                                               scale=1, color=colors.PERFECT_BLACK, depth=-10)
        self._option_pane_border.update(new_rect=options_bg_rect)

        if self._version_text_sprite is None:
            self._version_text_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0,
                                                           "v" + configs.version,
                                                           color=colors.LIGHT_GRAY,
                                                           font_lookup=spritesheets.get_default_font(mono=False, small=True))
        version_text_rect = self._version_text_sprite.get_rect()
        self._version_text_sprite.update(new_x=total_size[0] - version_text_rect[2],
                                         new_y=total_size[1] - version_text_rect[3])
        if self._version_text_bg is None:
            self._version_text_bg = sprites.ImageSprite(spritesheets.get_white_square_img(opacity=0.5), 0, 0, spriteref.UI_BG_LAYER)
        self._version_text_bg = self._version_text_bg.update(new_x=version_text_rect[0],
                                                             new_y=version_text_rect[1],
                                                             new_color=colors.PERFECT_BLACK,
                                                             new_raw_size=version_text_rect[2:4])

    def all_sprites(self):
        for spr in self._title_element.all_sprites_from_self_and_kids():
            yield spr
        for spr in self._options_list.all_sprites_from_self_and_kids():
            yield spr
        yield self._option_pane_bg
        yield self._option_pane_border
        yield self._version_text_bg
        yield self._version_text_sprite
        for spr in self.cine_seq.all_sprites():
            yield spr

    def became_active(self):
        songsystem.get_instance().set_song(songsystem.MAIN_MENU_SONG, fadein=0.5, fadeout=0.5)


class InstructionsScene(scenes.Scene):

    def __init__(self, next_scene, prev_scene):
        super().__init__()
        self.next_scene = next_scene
        self.prev_scene = prev_scene

        self._text_scale = 1
        self._text_sprite = None
        self._ticks_active = 0

    def _build_text(self):
        wasd_keys, arrow_keys, jump_alt = gs.get_instance().get_user_friendly_movement_keys()
        reset_key, hard_reset_key, *_ = gs.get_instance().get_user_friendly_misc_keys()
        return "Objective:\n" \
               "Guide each robot to their respective goal, indicated by a capital letter. " \
               "To pass a level, all units must be at their goals simultaneously.\n\n" \
               f"[{wasd_keys}] or [{arrow_keys}] and [{jump_alt}] to move.\n" \
               f"[{reset_key}] to reset the current unit.\n" \
               f"[{hard_reset_key}] to reset the entire level."

    def update(self):
        if inputs.get_instance().was_pressed(const.MENU_CANCEL):
            self.get_manager().set_next_scene(self.prev_scene)
            sounds.play_sound(soundref.MENU_BACK)
            return

        if self._ticks_active > 15:
            if inputs.get_instance().was_pressed(const.MENU_ACCEPT) or inputs.get_instance().mouse_was_pressed(button=1):
                self.get_manager().set_next_scene(self.next_scene)
                sounds.play_sound(soundref.MENU_START)
                return

        self._ticks_active += 1

        if self._text_sprite is None:
            self._text_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, "abc", scale=self._text_scale)

        # XXX wrapping before removing the []s, kinda cringe~
        screen_size = renderengine.get_instance().get_game_size()
        wrapped_text = "\n".join(sprites.TextSprite.wrap_text_to_fit(self._build_text(),
                                                                     width=screen_size[0] * 0.8,
                                                                     scale=self._text_scale))
        colored_text = sprites.TextBuilder(text=wrapped_text).recolor_chars_between("[", "]", colors.KEYBIND_COLOR)

        self._text_sprite = self._text_sprite.update(new_text=colored_text.text, new_color_lookup=colored_text.colors)
        self._text_sprite = self._text_sprite.update(new_x=screen_size[0] // 2 - self._text_sprite.size()[0] // 2,
                                                     new_y=screen_size[1] // 2 - self._text_sprite.size()[1] // 2)

    def all_sprites(self):
        if self._text_sprite is not None:
            for spr in self._text_sprite.all_sprites():
                yield spr

    def get_cursor_id_at(self, xy):
        return const.CURSOR_HAND

    def became_active(self):
        songsystem.get_instance().set_song(songsystem.INSTRUCTION_MENU_SONG, fadein=0.5, fadeout=0.5)


class CreditsScene(scenes.Scene):
    # most of this is yoinked from Skeletris

    SMALL = 1
    NORMAL = 1.5

    SLIDE_TEXT = [
        ("created by", SMALL),
        "David Pendergast",
        ("2022", SMALL),
        "",
        ("art, coding, and design by", SMALL),
        "David Pendergast",
        "",
        ("twitter", SMALL),
        "@Ghast_NEOH",
        "",
        ("github", SMALL),
        "davidpendergast",
        "",
        ("itch", SMALL),
        "ghastly.itch.io",
        "",
        ("music by", SMALL),
        "Of Far Different Nature",
        ("fardifferent.bandcamp.com", SMALL),
        "",
        ("songs (used under CC-BY 4.0)", SMALL)
    ]
    for titles in songsystem.OFDN_ALL_TITLES:
        SLIDE_TEXT.append(("'" + "', '".join(titles) + "'", SMALL))
    SLIDE_TEXT.append("")

    SLIDE_TEXT.extend([
        ("sound effects by", SMALL),
        "Andrea Baroni",
        ("\"ModernUI Pack\"", SMALL),
        ("andreabaroni.com", SMALL)
    ])

    SLIDE_TEXT.extend([
        "",
        ("made with pygame and OpenGL", SMALL),
        "",
        ("thanks for playing <3", SMALL)
    ])

    def __init__(self, next_scene, lines=None):
        super().__init__()
        self.scroll_speeds = (1.5, 4)  # pixels per tick
        self.scroll_speed_idx = 0
        self.tick_count = 0
        self.empty_line_height = 160
        self.text_y_spacing = 10

        self.next_scene = next_scene

        self.scroll_y_pos = 0  # distance from bottom of screen

        self._text_lines = []
        if lines is not None:
            for l in lines:
                if isinstance(l, (list, tuple)) and len(l) >= 2:
                    text, size = l
                    if isinstance(size, str):
                        size = CreditsScene.SMALL if size.lower() == "small" else CreditsScene.NORMAL
                else:
                    text = str(l)
                    size = CreditsScene.NORMAL
                self._text_lines.append((text, size))
        else:
            self._text_lines.extend(CreditsScene.SLIDE_TEXT)

        self._all_images = []

        self._onscreen_img_indexes = set()

        self.build_images()

    def _scroll_speed(self):
        return self.scroll_speeds[self.scroll_speed_idx]

    def build_images(self):
        for line in self._text_lines:
            if line == "":
                self._all_images.append(None)
            else:
                if isinstance(line, tuple):
                    text = line[0]
                    size = line[1]
                else:
                    text = line
                    size = CreditsScene.NORMAL

                self._all_images.append(sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, text, scale=size, color=colors.WHITE))

    def update(self):
        self.tick_count += 1

        enter_keys = keybinds.get_instance().get_keys(const.MENU_ACCEPT)
        if self.tick_count > 5 and inputs.get_instance().was_pressed(enter_keys):
            self.scroll_speed_idx = (self.scroll_speed_idx + 1) % len(self.scroll_speeds)
        elif inputs.get_instance().was_pressed(const.MENU_CANCEL) and isinstance(self.next_scene, MainMenuScene):
            self.jump_to_scene(self.next_scene)

        self.scroll_y_pos += self._scroll_speed()

        screen_size = renderengine.get_instance().get_game_size()
        y_pos = screen_size[1] - int(self.scroll_y_pos)

        for i in range(0, len(self._all_images)):
            text_img = self._all_images[i]
            if text_img is None:
                y_pos += self.empty_line_height
            else:
                w = text_img.size()[0]
                x_pos = screen_size[0] // 2 - w // 2
                text_img = text_img.update(new_x=x_pos, new_y=y_pos)
                self._all_images[i] = text_img

                renderengine.get_instance().update(text_img)

                y_pos += text_img.size()[1] + self.text_y_spacing

        if y_pos < 0:
            self.get_manager().set_next_scene(self.next_scene)

    def all_sprites(self):
        for text_spr in self._all_images:
            yield text_spr


class OptionSelectScene(scenes.Scene):

    def __init__(self, title=None, opts_per_page=6):
        scenes.Scene.__init__(self)
        self.title_text = title
        self.title_sprite = None
        self.title_scale = 2

        self.desc_text = None
        self.desc_sprite = None
        self.desc_scale = 1
        self.desc_horz_inset = 32
        self.desc_alignment = sprites.TextSprite.LEFT
        self.desc_wrap = True

        self.vert_spacing = 32

        self.option_pages = ui.MultiPageOptionsList(opts_per_page=opts_per_page)

        self._esc_option = None

    def add_option(self, text, do_action, is_enabled=lambda: True, esc_option=False):
        self.option_pages.add_option(text, do_action, is_enabled=is_enabled, esc_option=esc_option)

    def set_description(self, text, scale=1, alignment=sprites.TextSprite.LEFT, wrap=True):
        """Sets the description text for the menu.
        text: str or TextBuilder, or None to disable it.
        """
        self.desc_text = text
        self.desc_scale = scale
        self.desc_alignment = alignment
        self.desc_wrap = wrap

    def update(self):
        if self.title_sprite is None:
            self.title_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, self.title_text, scale=self.title_scale)
        screen_size = renderengine.get_instance().get_game_size()
        title_x = screen_size[0] // 2 - self.title_sprite.size()[0] // 2
        title_y = max(16, screen_size[1] // 5 - self.title_sprite.size()[1] // 2)
        self.title_sprite.update(new_x=title_x, new_y=title_y)
        y_pos = title_y + self.title_sprite.size()[1] + self.vert_spacing

        if self.desc_text is None or len(self.desc_text) == 0:
            self.desc_sprite = None
        else:
            if self.desc_sprite is None:
                self.desc_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, "abc", scale=self.desc_scale)

            if isinstance(self.desc_text, sprites.TextBuilder):
                desc_text_to_use = self.desc_text.text
                desc_color_lookup = self.desc_text.colors
            else:
                desc_text_to_use = self.desc_text
                desc_color_lookup = None

            if self.desc_wrap:
                wrapped_desc = sprites.TextSprite.wrap_text_to_fit(desc_text_to_use,
                                                                   screen_size[0] - self.desc_horz_inset * 2,
                                                                   scale=self.desc_scale)
                desc_color_lookup = None  # TODO impl text wrapping with per-char colors
                desc_text_to_use = "\n".join(wrapped_desc)

            self.desc_sprite.update(new_text=desc_text_to_use, new_color_lookup=desc_color_lookup, new_alignment=self.desc_alignment)
            desc_x = screen_size[0] // 2 - self.desc_sprite.size()[0] // 2
            desc_y = y_pos
            self.desc_sprite.update(new_x=desc_x, new_y=desc_y)
            y_pos += self.desc_sprite.size()[1] + self.vert_spacing

        options_y = y_pos
        options_x = screen_size[0] // 2 - self.option_pages.get_size()[0] // 2
        self.option_pages.set_xy((options_x, options_y))
        self.option_pages.update_self_and_kids()
        y_pos += self.option_pages.get_size()[1] + self.vert_spacing

    def all_sprites(self):
        if self.title_sprite is not None:
            for spr in self.title_sprite.all_sprites():
                yield spr
        if self.desc_sprite is not None:
            for spr in self.desc_sprite.all_sprites():
                yield spr
        for spr in self.option_pages.all_sprites_from_self_and_kids():
            yield spr

    def get_cursor_id_at(self, xy):
        return self.option_pages.get_cursor_id_from_self_and_kids(xy, absolute=True)


class ControlsScene(OptionSelectScene):

    def __init__(self, next_scene):
        self.next_scene = next_scene

        super().__init__(title="Controls")
        self.set_description(self._build_desc(), alignment=sprites.TextSprite.CENTER, wrap=False)
        # TODO add ability to edit controls in-game
        # TODO (did anyone EVER actually do this in skeletris? not that I saw~)

        self._ticks_active = 0

    def update(self):
        super().update()

        if self._ticks_active > 5 and inputs.get_instance().was_pressed((const.MENU_ACCEPT, const.MENU_CANCEL)):
            self.jump_to_scene(self.next_scene)

        self._ticks_active += 1

    def _build_desc(self):
        wasd_keys, arrow_keys, alt_jump = gs.get_instance().get_user_friendly_movement_keys()
        right_action_key, left_action_key, alt_action_key = gs.get_instance().get_user_friendly_action_keys()
        reset_key, hard_reset_key, pause_key, mute_key, fullscreen_key = gs.get_instance().get_user_friendly_misc_keys()

        text = "\n".join([
            f"move: [{arrow_keys}] or [{wasd_keys}] or [{alt_jump}]",
            f"interact: [{right_action_key}] or [{left_action_key}] or [{alt_action_key}]",
            "",
            f"reset: [{reset_key}] and [{hard_reset_key}]",
            f"toggle fullscreen: [{fullscreen_key}]",
            f"mute music: [{mute_key}]",
            f"pause: [{pause_key}]"
        ])

        # re-color the keys to make them stand out
        return sprites.TextBuilder(text=text).recolor_chars_between("[", "]", colors.KEYBIND_COLOR)


class LevelSelectForEditScene(OptionSelectScene):

    def __init__(self, dirpaths):
        """
        :param dirpaths: map of name -> path
        """
        OptionSelectScene.__init__(self, "Create Level")

        self.all_levels = {}

        level_names = {}

        for key in dirpaths:
            dirpath = dirpaths[key]
            levels_in_dir = blueprints.load_all_levels_from_dir(dirpath)
            for level_id in levels_in_dir:
                level_names[level_id] = "{}: {}".format(key, level_id)
                self.all_levels[level_id] = levels_in_dir[level_id]

        sorted_ids = [k for k in self.all_levels]
        sorted_ids.sort()

        self.add_option("create new", lambda: self.jump_to_scene(LevelEditGameScene(blueprints.get_template_blueprint())))

        for level_id in sorted_ids:
            level_bp = self.all_levels[level_id]

            def _action(bp=level_bp):  # lambdas in loops, yikes
                self.jump_to_scene(LevelEditGameScene(bp))

            self.add_option(level_names[level_id], _action)

    def update(self):
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_CANCEL)):
            self.jump_to_scene(MainMenuScene())
            sounds.play_sound(soundref.MENU_BACK)
        else:
            super().update()


class LevelEditorPauseMenu(OptionSelectScene):

    def __init__(self, level_bp, on_cancel, on_quit, edit_scene_provider, description=None):
        """
        :param level_bp: current LevelBlueprint
        :param on_cancel: manager, LevelBlueprint -> None
        :param on_quit: () -> None
        :param edit_scene_provider: new_bp -> Scene
        """
        super().__init__(title="editing {}".format(level_bp.name()))
        self.set_description(description)
        self.add_option("resume", lambda: on_cancel(level_bp), esc_option=True)
        self.add_option("edit metadata", lambda: self.jump_to_scene(
            LevelMetaDataEditScene(level_bp, lambda new_bp: self.jump_to_scene(edit_scene_provider(new_bp)))
        ))

        self.add_option("quit", on_quit)
        # self.add_option("save and quit", on_save_and_quit)  # TODO?


class TextEditScene(scenes.Scene):

    def __init__(self, prompt_text, default_text="", on_cancel=None, on_accept=None, char_limit=32,
                 allowed_chars=ui.TextEditElement.ASCII_CHARS):
        """
        :param on_exit: lambda (MenuManager) -> None
        :param on_accept: lambda (MenuManager, final_text) -> None
        """
        scenes.Scene.__init__(self)
        self.prompt_text = prompt_text
        self.prompt_element = ui.SpriteElement()

        self.text_box = ui.TextEditElement(default_text, scale=1, char_limit=char_limit,
                                           outline_color=colors.LIGHT_GRAY, allowed_chars=allowed_chars)

        self.on_cancel = on_cancel
        self.on_accept = on_accept

    def update(self):
        if self.prompt_element.get_sprite() is None:
            self.prompt_element.set_sprite(sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, self.prompt_text, scale=2))

        total_size = renderengine.get_instance().get_game_size()
        title_size = self.prompt_element.get_size()
        title_x = total_size[0] // 2 - title_size[0] // 2
        title_y = max(16, total_size[1] // 5 - title_size[1] // 2)
        self.prompt_element.set_xy((title_x, title_y))
        self.prompt_element.update_self_and_kids()

        text_x = total_size[0] // 2 - self.text_box.get_size()[0] // 2
        text_y = max(self.prompt_element.get_xy()[1] + 32, total_size[1] // 2 - self.text_box.get_size()[1] // 2)
        self.text_box.set_xy((text_x, text_y))
        self.text_box.update_self_and_kids()

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_CANCEL)):
            if self.on_cancel is not None:
                self.on_cancel(self.get_manager())
                sounds.play_sound(soundref.MENU_BACK)
                return

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_ACCEPT)):
            if self.on_accept is not None:
                self.on_accept(self.get_manager(), self.text_box.get_text())
                sounds.play_sound(soundref.MENU_ACCEPT)
                return

    def all_sprites(self):
        for spr in self.text_box.all_sprites():
            yield spr
        for spr in self.prompt_element.all_sprites():
            yield spr


class CutsceneScene(scenes.Scene):

    def __init__(self):
        scenes.Scene.__init__(self)
        self._text_sprite = None
        self._text_bg_sprite = None

        self._bg_sprite = None

        self.tick_count = 0

    def update(self):
        self.update_sprites()
        self.handle_inputs()
        self.tick_count += 1

    def get_text(self) -> sprites.TextBuilder:
        raise NotImplementedError()

    def get_bg_image(self) -> sprites.ImageModel:
        raise NotImplementedError()

    def get_next_scene(self) -> scenes.Scene:
        raise NotImplementedError()

    def get_bg_image_scale(self) -> int:
        return 1

    def get_text_scale(self) -> int:
        return 1

    def handle_inputs(self):
        if self.tick_count > 5 and inputs.get_instance().was_anything_pressed():
            self.jump_to_scene(self.get_next_scene())

    def update_sprites(self):
        game_size = renderengine.get_instance().get_game_size()

        bg_img = self.get_bg_image()
        if bg_img is None:
            self._bg_sprite = None
        else:
            if self._bg_sprite is None:
                self._bg_sprite = sprites.ImageSprite(bg_img, 0, 0, spriteref.UI_BG_LAYER)

            bg_x = game_size[0] // 2 - self._bg_sprite.width() // 2
            bg_y = 0
            bg_scale = self.get_bg_image_scale()

            self._bg_sprite = self._bg_sprite.update(new_model=bg_img, new_x=bg_x, new_y=bg_y, new_scale=bg_scale)

        cur_text = self.get_text()
        if cur_text is None:
            self._text_sprite = None
            self._text_bg_sprite = None
        else:
            if self._text_sprite is None:
                self._text_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, "abc")
            if self._text_bg_sprite is None:
                self._text_bg_sprite = sprites.ImageSprite.new_sprite(spriteref.UI_BG_LAYER)

            text_w = int(game_size[0] * 0.8)
            text_scale = self.get_text_scale()
            wrapped_text = sprites.TextSprite.wrap_text_to_fit(cur_text.text, text_w, scale=text_scale)
            text_color = colors.WHITE if 0 not in cur_text.colors else cur_text.colors[0]  # TODO nuking per-char colors
            self._text_sprite.update(new_text="\n".join(wrapped_text),
                                     new_scale=text_scale,
                                     new_color=text_color)

            text_w = self._text_sprite.get_rect()[2]
            text_h = self._text_sprite.get_rect()[3]

            if self._bg_sprite is not None:
                space_remaining = game_size[1] - (self._bg_sprite.y() + self._bg_sprite.height())
                if space_remaining >= text_h:
                    # if there's room under the image, put the text there.
                    target_y = self._bg_sprite.y() + self._bg_sprite.height() + space_remaining // 2
                else:
                    target_y = int(game_size[3] * 0.9) - text_h  # otherwise just cram it in
            else:
                target_y = game_size[1] // 2  # center it

            self._text_sprite.update(new_x=game_size[0] // 2 - text_w // 2,
                                     new_y=target_y - text_h // 2)

    def all_sprites(self):
        yield self._bg_sprite
        # yield self._text_bg_sprite
        yield self._text_sprite


class MultiPageCutsceneScene(CutsceneScene):

    def __init__(self, pages, page=0, next_scene_provider=None):
        CutsceneScene.__init__(self)
        if page < 0 or page >= len(pages):
            raise ValueError("page out of bounds: {}".format(page))
        self.all_pages = pages
        self.page = page
        self.next_scene_provider = next_scene_provider

    def get_text(self) -> sprites.TextBuilder:
        text = self.all_pages[self.page][1]
        if text is None:
            return None
        else:
            res = sprites.TextBuilder()
            res.add(text, color=colors.WHITE)
            return res

    def get_bg_image(self) -> sprites.ImageModel:
        img_type = self.all_pages[self.page][0]
        if img_type is not None:
            return spriteref.cutscene_image(img_type)
        else:
            return None

    def get_next_scene(self) -> scenes.Scene:
        if self.page < len(self.all_pages) - 1:
            return MultiPageCutsceneScene(self.all_pages, self.page + 1, next_scene_provider=self.next_scene_provider)
        elif self.next_scene_provider is not None:
            return self.next_scene_provider()
        else:
            return MainMenuScene()


class IntroCutsceneScene(MultiPageCutsceneScene):

    _PAGES = [
        (spriteref.CutsceneTypes.SUN, "The sun."),
        (spriteref.CutsceneTypes.SUN_CLOSEUP, "Close up."),
        (spriteref.CutsceneTypes.SHIP, "Ship."),
        (spriteref.CutsceneTypes.DIG, "Resources."),
        (spriteref.CutsceneTypes.BARREN, "Exhausted"),
        (spriteref.CutsceneTypes.TRANSPORT, "Transport"),
        (spriteref.CutsceneTypes.SPLIT, "Done")
    ]

    def __init__(self, next_scene_provider):
        super().__init__(IntroCutsceneScene._PAGES, next_scene_provider=next_scene_provider)


class EndOfGameScene(MultiPageCutsceneScene):

    ENDING_TURN_ON = "turn_on"
    ENDING_LEAVE_OFF = "leave_off"

    def __init__(self, next_scene_provider, ending=None):
        pages = [(None, "You win!")]
        # TODO alt endings

        def _get_next_scene():
            if next_scene_provider is not None:
                final_scene = next_scene_provider()
            else:
                final_scene = MainMenuScene()
            return StatsScene(None, CreditsScene(final_scene))

        super().__init__(pages, next_scene_provider=_get_next_scene)


class _BaseGameScene(scenes.Scene):

    def __init__(self):
        scenes.Scene.__init__(self)

        self._world = None
        self._world_view = None

    def setup_new_world(self, bp):
        if bp is None:
            self._world = None
            self._world_view = None
        else:
            print("INFO: activating blueprint: {}".format(bp.name()))
            self._world = bp.create_world()
            self._world_view = worldview.WorldView(self._world)
            self._world_view.set_free_camera(False)

    def get_world(self) -> worlds.World:
        return self._world

    def get_world_view(self) -> worldview.WorldView:
        return self._world_view

    def update_world_and_view(self):
        pass

    def update_sprites(self):
        if self._world_view is not None:
            self._world_view.update()

    def update_song(self):
        pass

    def update(self):
        if self._world is not None:
            self._world.update()

        self.update_song()

        # TODO why process inputs *after* updating world? because it never matters...?
        if inputs.get_instance().mouse_in_window():
            screen_pos = inputs.get_instance().mouse_pos()
            pos_in_world = self._world_view.screen_pos_to_world_pos(screen_pos)
            if inputs.get_instance().mouse_was_pressed(button=1):
                self.handle_click_at(screen_pos, pos_in_world, button=1)
            if inputs.get_instance().mouse_was_pressed(button=2):
                self.handle_click_at(screen_pos, pos_in_world, button=2)
            if inputs.get_instance().mouse_was_pressed(button=3):
                self.handle_click_at(screen_pos, pos_in_world, button=3)

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_CANCEL)):
            self.handle_esc_pressed()

    def handle_esc_pressed(self):
        pass

    def handle_click_at(self, screen_xy, world_xy, button=1):
        if configs.is_dev:
            cell_size = gs.get_instance().cell_size
            print("INFO: mouse pressed at ({}, {})".format(int(world_xy[0]) // cell_size,
                                                           int(world_xy[1]) // cell_size))
    def all_sprites(self):
        if self._world_view is not None:
            for spr in self._world_view.all_sprites():
                yield spr
        else:
            return []


class Status:

    def __init__(self, ident, player_control, can_hard_reset, can_soft_reset, world_ticks_inc=True, is_success=False):
        self.ident = ident
        self.can_player_control = player_control
        self.can_hard_reset = can_hard_reset
        self.can_soft_reset = can_soft_reset
        self.world_ticks_inc = world_ticks_inc
        self.is_success = is_success

    def __eq__(self, other):
        if isinstance(other, Status):
            return self.ident == other.ident
        else:
            return False

    def __str__(self):
        return self.ident


class Statuses:

    WAITING = Status("waiting", False, True, False, world_ticks_inc=False)
    IN_PROGRESS = Status("in_progress", True, True, True)
    FAIL_DELAY = Status("fail_delay", False, True, True)
    PARTIAL_SUCCESS = Status("partial_success", False, True, True, is_success=True)
    TOTAL_SUCCESS = Status("success", False, True, True, is_success=True)
    EXIT_NOW_SUCCESSFULLY = Status("exit_success", False, False, False, is_success=True)

    DIALOG = Status("dialog", False, False, False, world_ticks_inc=False, is_success=False)


class _GameState:

    def __init__(self, bp: blueprints.LevelBlueprint, status=Statuses.WAITING):
        self.bp = bp

        self._status = status
        self._status_elapsed_time = 0
        self._next_status = None
        self._next_status_countdown = 0

        self._players_in_level = bp.get_player_types()
        n_players = len(self._players_in_level)

        self._currently_playing = [False] * n_players
        self._currently_satisfied = [False] * n_players
        self._recorded_runs = [None] * n_players  # list of PlaybackPlayerController
        self._currently_alive = [False] * n_players
        self._has_ever_died = [None] * n_players  # list of DeathReasons

        self._total_ticks = bp.time_limit()
        self._time_elapsed = 0

        self._active_player_idx = 0

    def get_status(self) -> Status:
        return self._status

    def set_status(self, status, delay=0):
        if delay == 0:
            if status != self._status:
                print("INFO: status set to: {}".format(status))
                self._status = status
                self._status_elapsed_time = 0
        else:
            self._next_status = status
            self._next_status_countdown = delay

    def is_waiting(self):
        return self.get_status() == Statuses.WAITING

    def status_changed_this_frame(self):
        return self._status_elapsed_time <= 1

    def reset(self, idx=-1):
        if idx == -1:
            idx = self.get_active_player_idx()

        self._time_elapsed = 0
        for i in range(0, len(self._currently_satisfied)):
            self._currently_satisfied[i] = False
        for i in range(0, len(self._currently_playing)):
            self._currently_playing[i] = False
        for i in range(0, len(self._currently_playing)):
            self._has_ever_died[i] = None
        if idx == 0:  # reset all players
            self._active_player_idx = 0
            self._recorded_runs = [None] * self.num_players()
        self.set_status(Statuses.WAITING)

    def active_player_succeeded(self, recording):
        self._recorded_runs[self._active_player_idx] = recording

        self._active_player_idx += 1
        self.reset()

    def has_recording(self, player_idx):
        return self._recorded_runs[player_idx] is not None

    def get_recording(self, player_idx):
        return self._recorded_runs[player_idx]

    def get_player_type(self, player_idx):
        return self._players_in_level[player_idx]

    def get_index_of_player_type(self, player_type):
        if player_type in self._players_in_level:
            return self._players_in_level.index(player_type)
        else:
            return None

    def num_players(self):
        return len(self._players_in_level)

    def get_ticks_remaining(self):
        return max(0, self._total_ticks - self._time_elapsed)

    def get_pcnt_ticks_remaining(self):
        if self._total_ticks == 0 or self._time_elapsed <= 0:
            return 1
        elif self._time_elapsed > self._total_ticks:
            return 0
        else:
            return (self._total_ticks - self._time_elapsed) / self._total_ticks

    def get_elapsed_ticks(self):
        return self._time_elapsed

    def get_active_player_idx(self):
        return self._active_player_idx

    def get_active_player_type(self):
        return self.get_player_type(self.get_active_player_idx())

    def is_satisfied(self, player_idx):
        return self._currently_satisfied[player_idx] and not self.has_ever_died(player_idx)

    def all_satisfied(self):
        for idx in range(0, self.num_players()):
            if not self.is_satisfied(idx):
                return False
        return True

    def get_failure_message(self):
        """return: list of str (representing the lines in the failure message) or an empty list.
        """
        res_lines = []
        for idx in range(0, self._active_player_idx + 1):
            death_reason = self._has_ever_died[idx]
            if death_reason is not None:
                player_type = self.get_player_type(idx)
                res_lines.append(f"Unit {player_type.get_name()} {death_reason.get_description()}.")

        if len(res_lines) == 0 and self.get_ticks_remaining() <= 0:
            res_lines.append("Time's Up!")

        if len(res_lines) > 0:
            active_player_type = self.get_player_type(self._active_player_idx)
            soft_reset_keys = keybinds.get_instance().get_keys(const.SOFT_RESET)
            if len(soft_reset_keys) > 0:
                res_lines.append(f"[{soft_reset_keys}] to reset Unit {active_player_type.get_name()}")

            if self._active_player_idx > 0:
                hard_reset_keys = keybinds.get_instance().get_keys(const.RESET)
                if len(hard_reset_keys) > 0:
                    res_lines.append(f"[{hard_reset_keys}] to reset all")

        return res_lines

    def is_playing_back(self, player_idx):
        return self._currently_playing[player_idx]

    def set_playing_back(self, player_idx, val):
        self._currently_playing[player_idx] = val

    def is_alive(self, player_idx):
        """returns: Whether any copy of of a player are alive.
        """
        return self._currently_alive[player_idx]

    def is_dead(self, player_idx, or_has_ever_died=True):
        """returns: Whether all copies of a player are dead.
        """
        if not self.is_waiting() and player_idx <= self._active_player_idx:
            return not self.is_alive(player_idx) or (or_has_ever_died and self.has_ever_died(player_idx))

    def has_ever_died(self, player_idx):
        """returns: Whether any copies of a player have died.
        """
        return not self.is_waiting() and player_idx <= self._active_player_idx and self._has_ever_died[player_idx] is not None

    def set_player_died(self, player_type, death_reason):
        idx = self.get_index_of_player_type(player_type)
        if idx is not None:
            self._has_ever_died[idx] = death_reason

    def set_alive(self, player_idx, val):
        self._currently_alive[player_idx] = val

    def was_playing_back(self, player_idx):
        return player_idx < self.get_active_player_idx()

    def set_satisfied(self, player_idx, val):
        self._currently_satisfied[player_idx] = val

    def is_active_character_satisfied(self):
        return self.is_satisfied(self._active_player_idx)

    def update(self, world):
        if self._next_status is not None and self._next_status_countdown <= 1:
            self.set_status(self._next_status)
            self._next_status_countdown = 0
            self._next_status = None
        elif self._next_status is not None:
            self._next_status_countdown -= 1

        self._status_elapsed_time += 1

        if self.get_status().can_player_control:
            self._time_elapsed += 1

        p_type_to_players_and_end_blocks = {p_type: ([], []) for p_type in self._players_in_level}
        for p in world.all_players(must_be_active=False):
            if p.get_player_type() in p_type_to_players_and_end_blocks:
                p_type_to_players_and_end_blocks[p.get_player_type()][0].append(p)
        for eb in world.all_end_blocks():
            if eb.get_player_type() in p_type_to_players_and_end_blocks:
                p_type_to_players_and_end_blocks[eb.get_player_type()][1].append(eb)

        for idx in range(0, self.num_players()):
            p_type = self.get_player_type(idx)

            is_alive = len(p_type_to_players_and_end_blocks[p_type][0]) > 0
            is_playing_back = False

            # every copy of a player type must be satisfied for that character to be satisfied
            all_satisfied = True and is_alive

            for p in p_type_to_players_and_end_blocks[p_type][0]:
                p_is_satisfied = False
                for eb in p_type_to_players_and_end_blocks[p_type][1]:
                    if eb.is_satisfied(by=p):
                        p_is_satisfied = True
                        break
                all_satisfied = all_satisfied and p_is_satisfied

                if not p.is_active() and not p.get_controller().is_finished(world.get_tick()):
                    is_playing_back = True

            self.set_satisfied(idx, all_satisfied)
            self.set_playing_back(idx, is_playing_back)
            self.set_alive(idx, is_alive)

    def get_song(self):
        song_id = self.bp.song_id()
        if song_id is None:
            return songsystem.SILENCE
        else:
            # TODO seems like we're not doing the multi-track song stuff, delete?
            # volumes = [0] * songsystem.num_instruments(song_id)
            # for i in range(0, self.get_active_player_idx() + 1):
            #     if not self.is_dead(i):
            #         p_type = self.get_player_type(i)
            #         for inst_idx in self.bp.get_instruments(p_type.get_id()):
            #             if 0 <= inst_idx < len(volumes):
            #                 volumes[inst_idx] = 1

            # soften music when you've failed
            return song_id, [1] if not self.get_failure_message() else [0.666]


class TopPanelUi(ui.UiElement):

    def __init__(self, state: _GameState, layer_id):
        ui.UiElement.__init__(self)
        self._state = state
        self._layer_id = layer_id
        self.bg_sprite = None
        self.clock_text_sprite = None
        self.character_panel_sprites = []
        self.character_panel_animation_sprites = []  # arrows that spin around

    def get_clock_text(self):
        ticks_rm = self._state.get_ticks_remaining()
        return util.ticks_to_time_string(ticks_rm, fps=60, n_decimals=1)

    def update(self):
        rect = self.get_rect(absolute=True)
        if self.bg_sprite is None:
            self.bg_sprite = sprites.ImageSprite.new_sprite(self._layer_id, depth=100)
        self.bg_sprite = self.bg_sprite.update(new_model=spriteref.ui_sheet().top_panel_bg,
                                               new_x=rect[0], new_y=rect[1], new_color=colors.DARK_GRAY)

        player_types = [self._state.get_player_type(i) for i in range(0, self._state.num_players())]
        active_idx = self._state.get_active_player_idx()

        util.extend_or_empty_list_to_length(self.character_panel_sprites, len(player_types),
                                            creator=lambda: sprites.ImageSprite.new_sprite(self._layer_id, depth=15))
        util.extend_or_empty_list_to_length(self.character_panel_animation_sprites, len(player_types),
                                            creator=lambda: None)
        for i in range(0, len(player_types)):
            model = spriteref.ui_sheet().get_character_card_sprite(player_types[i], i == 0)
            color = const.get_player_color(player_types[i], dark=i > active_idx)
            card_x = rect[0] - 7 + 40 * i
            card_y = rect[1]
            self.character_panel_sprites[i] = self.character_panel_sprites[i].update(new_x=card_x,
                                                                                     new_y=card_y,
                                                                                     new_model=model,
                                                                                     new_color=color)
            if i == active_idx or self._state.was_playing_back(i):
                if self.character_panel_animation_sprites[i] is None:
                    self.character_panel_animation_sprites[i] = sprites.ImageSprite.new_sprite(self._layer_id)

                is_first = i == 0
                is_last = i == len(player_types) - 1
                is_done = self._state.is_satisfied(i) or self._state.get_status().is_success
                frm = gs.get_instance().anim_tick()
                model = spriteref.ui_sheet().get_character_card_anim(is_first, is_last, frm, done=is_done)

                if is_done:
                    color = colors.PERFECT_GREEN
                elif self._state.is_dead(i):
                    color = colors.PERFECT_RED
                elif i == active_idx:
                    color = colors.WHITE
                elif self._state.is_playing_back(i) or self._state.get_status() == Statuses.WAITING:
                    color = colors.LIGHT_GRAY
                else:
                    color = colors.PERFECT_RED  # actor was knocked off-track and failed

                anim_spr = self.character_panel_animation_sprites[i].update(new_x=card_x,
                                                                            new_y=card_y,
                                                                            new_model=model,
                                                                            new_color=color,
                                                                            new_depth=25)
                self.character_panel_animation_sprites[i] = anim_spr
            else:
                self.character_panel_animation_sprites[i] = None

        clock_text = self.get_clock_text()
        if self.clock_text_sprite is None:
            self.clock_text_sprite = sprites.TextSprite(self._layer_id, 0, 0, clock_text,
                                                        font_lookup=spritesheets.get_default_font(mono=True))
        self.clock_text_sprite.update(new_text=clock_text)
        clock_x = rect[0] + 270 - self.clock_text_sprite.size()[0]
        clock_y = rect[1] + 10
        self.clock_text_sprite.update(new_x=clock_x, new_y=clock_y, new_color=colors.WHITE)

    def get_size(self):
        return (288, 32)

    def all_sprites(self):
        yield self.bg_sprite
        yield self.clock_text_sprite
        for spr in self.character_panel_sprites:
            yield spr
        for spr in self.character_panel_animation_sprites:
            if spr is not None:
                yield spr


class ProgressBarUi(ui.UiElement):

    def __init__(self, state, layer_id):
        ui.UiElement.__init__(self)
        self._state = state
        self._layer_id = layer_id
        self.bg_sprite = None
        self.bar_sprite = None

    def update(self):
        rect = self.get_rect(absolute=True)
        if self.bg_sprite is None:
            self.bg_sprite = sprites.ImageSprite.new_sprite(self._layer_id, depth=80)
        self.bg_sprite = self.bg_sprite.update(new_model=spriteref.ui_sheet().top_panel_progress_bar_bg,
                                               new_x=rect[0], new_y=rect[1], new_color=colors.DARK_GRAY)
        if self.bar_sprite is None:
            self.bar_sprite = sprites.ImageSprite.new_sprite(self._layer_id, depth=60)
        # active_color = const.get_player_color(self._state.get_active_player_type(), dark=False)
        active_color = colors.WHITE
        pcnt_remaining = self._state.get_pcnt_ticks_remaining()
        self.bar_sprite = self.bar_sprite.update(new_model=spriteref.ui_sheet().get_bar_sprite(pcnt_remaining),
                                                 new_x=rect[0], new_y=rect[1] + 2, new_color=active_color)

    def get_size(self):
        return (288, 10)

    def all_sprites(self):
        yield self.bg_sprite
        yield self.bar_sprite


class RealGameScene(_BaseGameScene, dialog.DialogScene):

    def __init__(self, bp, on_level_completion, on_level_exit):
        """
        :param bp: LevelBlueprint
        :param on_level_completion: (time) -> None
        :param on_level_exit: () -> None
        """
        self._state = _GameState(bp)

        # babby's first attempt at multiple inheritance
        _BaseGameScene.__init__(self)
        dialog.DialogScene.__init__(self)

        self._on_level_completion = on_level_completion
        self._on_level_exit = on_level_exit

        self._top_panel_ui = None
        self._progress_bar_ui = None

        self._failure_message_text = None
        self._failure_message_bg = None

        self._fadeout_duration = 90

        self.setup_new_world(bp)
        self._handled_level_fail = False

        self._queued_next_world = None
        self._next_world_countdown = 0

    def on_level_complete(self, time):
        if self._on_level_completion is not None:
            self._on_level_completion(time)

    def on_level_exit(self):
        if self._on_level_exit is not None:
            self._on_level_exit()

    def on_level_fail(self):
        self.get_world_view().set_bg_colors([colors.PERFECT_DARK_RED, colors.PERFECT_VERY_DARK_RED], period=15, loop=False)
        # self.get_world_view().fade_to_bg_color(colors.PERFECT_VERY_DARK_RED, delay=20)
        sounds.play_sound(soundref.LEVEL_FAILED)
        # TODO sound / music change
        # TODO screenshake

    def get_state(self) -> _GameState:
        return self._state

    def update_sprites(self):
        _BaseGameScene.update_sprites(self)
        dialog.DialogScene.update_sprites(self)
        self._update_ui()

    def update_song(self):
        songsystem.get_instance().set_song(self._state.get_song(), fadein=1)

    def update(self):
        dialog.DialogScene.update(self)
        gs.get_instance().inc_in_game_playtime()

    def update_impl(self):
        if self._queued_next_world is not None:
            if self._next_world_countdown <= 0:
                bp, new_status, runnable = self._queued_next_world
                self._state.set_status(new_status)
                runnable()

                self.setup_new_world(bp)
            else:
                self._next_world_countdown -= 1

        if self._state.get_status() == Statuses.WAITING:
            player = self.get_world().get_player()
            if player is not None and player.has_inputs_at_tick(-1):
                print("INFO: player moved! starting level")
                self._state.set_status(Statuses.IN_PROGRESS)
        elif self._state.get_status() == Statuses.EXIT_NOW_SUCCESSFULLY:
            self._on_level_completion(self._state.get_elapsed_ticks())

        _BaseGameScene.update(self)

        self._state.update(self.get_world())

        hard_reset_keys = keybinds.get_instance().get_keys(const.RESET)
        soft_reset_keys = keybinds.get_instance().get_keys(const.SOFT_RESET)

        fail_msg = self._state.get_failure_message()

        if inputs.get_instance().was_pressed(hard_reset_keys):
            self.do_reset(idx=0)
        elif inputs.get_instance().was_pressed(soft_reset_keys):
            self.do_reset(idx=-1)  # just current player

        elif self._state.all_satisfied():
            self._state.set_status(Statuses.TOTAL_SUCCESS)
            self.replace_players_with_fadeout(delay=self._fadeout_duration)
            self._state.set_status(Statuses.EXIT_NOW_SUCCESSFULLY, delay=self._fadeout_duration)

        elif len(fail_msg) > 0:
            if not self._handled_level_fail:
                self.on_level_fail()
            self._handled_level_fail = True
        else:
            active_satisfied = True
            for i in range(0, self._state.get_active_player_idx() + 1):
                if not self._state.is_satisfied(i):
                    active_satisfied = False
                    break

            if active_satisfied:
                player_ent = self.get_world().get_player()
                recording = player_ent.get_controller().get_recording()
                if recording is not None:
                    self._state.set_status(Statuses.PARTIAL_SUCCESS)
                    self.replace_players_with_fadeout(delay=self._fadeout_duration)
                    self.add_fade_in_sprites_at_start_locations([_i for _i in range(0, self._state.get_active_player_idx() + 2)],
                                                                delay=self._fadeout_duration)

                    self.setup_new_world_with_delay(self._state.bp, self._fadeout_duration, Statuses.WAITING,
                                                    runnable=lambda: self._state.active_player_succeeded(recording))
                else:
                    print("WARN: active player is satisfied but has no recording. hopefully we're in dev mode?")

    def do_reset(self, idx=-1):
        if ((idx == 0 and not self._state.get_status().can_hard_reset)
                or (idx != 0 and not self._state.get_status().can_soft_reset)):
            return False
        else:
            self._state.reset(idx=idx)
            self.setup_new_world(self._state.bp)
            return True

    def replace_players_with_fadeout(self, delay=60):
        for i in range(0, self._state.get_active_player_idx() + 1):
            player_type = self._state.get_player_type(i)
            player = self.get_world().get_player(must_be_active=False, with_type=player_type)
            if player is not None:
                player.spawn_fadeout_animation(delay)
                self.get_world().remove_entity(player)

    def add_fade_in_sprites_at_start_locations(self, player_idxes, delay=60):
        import src.game.entities as entities  # TODO pretty cringe
        for idx in player_idxes:
            player_type = self._state.get_player_type(idx)
            for xy in self.get_world().get_player_start_positions(player_type):
                anim = entities.PlayerFadeAnimation(0, 0, True, player_type, delay, False)
                anim.set_xy((xy[0] - anim.get_w() // 2, xy[1] - anim.get_h()))
                self.get_world().add_entity(anim)

    def handle_esc_pressed(self):
        def _on_quit():
            self.on_level_exit()
            sounds.play_sound(soundref.LEVEL_QUIT)
        sounds.play_sound(soundref.MENU_BACK)  # pause sound
        self.jump_to_scene(GamePausedScene(self, _on_quit))

    def start_dialog(self, dialog_frag):
        super().start_dialog(dialog_frag)

        def _get_center():
            p = self.get_world().get_player(must_be_active=True)
            if p is not None:
                return p.get_center()
            else:
                return None
        self.get_world_view().set_temp_zoom(2, center=_get_center, delay=20)

    def on_dialog_end(self):
        super().on_dialog_end()

        self.get_world_view().set_temp_zoom(None, delay=20)

    def setup_new_world_with_delay(self, bp, delay, new_state, runnable=lambda: None):
        self._queued_next_world = (bp, new_state, runnable)
        self._next_world_countdown = delay

    def setup_new_world(self, bp):
        old_show_grid = False if self.get_world_view() is None else self.get_world_view()._show_grid
        super().setup_new_world(bp)

        self._handled_level_fail = False

        # assume we don't intentionally have another new world queued up
        self._next_world_countdown = 0
        self._queued_next_world = None

        # gotta place the players down
        world = self.get_world()
        self.get_world_view()._show_grid = old_show_grid

        world.set_game_state(self._state)

        import src.game.entities as entities

        for i in range(0, self._state.num_players()):
            player_type = self._state.get_player_type(i)
            is_active = i == self._state.get_active_player_idx()

            if is_active:
                controller = entities.RecordingPlayerController()
            else:
                controller = self._state.get_recording(i)

            if controller is not None:
                for xy in world.get_player_start_positions(player_type):
                    player_ent = entities.PlayerEntity(0, 0, player_type, controller)
                    player_ent.set_xy((xy[0] - player_ent.get_w() // 2, xy[1] - player_ent.get_h()))
                    world.add_entity(player_ent, next_update=False)

                    if is_active:
                        world.add_entity(entities.PlayerIndicatorEntity(player_ent), next_update=False)
                        world.add_entity(entities.EndBlockIndicatorEntity(player_ent), next_update=False)

        world.update()
        self.get_world_view().update()

    def _update_ui(self):
        if self.get_world().should_show_timer():
            if self._top_panel_ui is None:
                self._top_panel_ui = TopPanelUi(self._state, spriteref.WORLD_UI_LAYER)
            top_panel_size = self._top_panel_ui.get_size()

            camera_cx = self.get_world_view().get_camera_center_in_world()[0]
            cx = camera_cx

            # let the UI follow the camera on wide levels, but don't let it go out of bounds.
            camera_bound = self.get_world().get_camera_bound()
            if camera_bound is not None:
                level_x_bounds = camera_bound[0], camera_bound[0] + camera_bound[2]

                insets = int((configs.optimal_window_size[0] / configs.optimal_pixel_scale - top_panel_size[0]) / 2)
                if level_x_bounds[0] is not None and level_x_bounds[1] is not None:
                    shift_right = cx - top_panel_size[0] // 2 - insets < level_x_bounds[0]
                    shift_left = cx + top_panel_size[0] // 2 + insets >= level_x_bounds[1]
                    if shift_left and not shift_right:
                        cx = level_x_bounds[1] - insets - top_panel_size[0] // 2
                    elif shift_right and not shift_left:
                        cx = level_x_bounds[0] + insets + top_panel_size[0] // 2

            # y-position in world to draw the UI panel
            y0 = 0 if camera_bound is None else camera_bound[1]

            y = 4
            self._top_panel_ui.set_xy((cx - top_panel_size[0] // 2, y0 + y))
            self._top_panel_ui.update()
            y += top_panel_size[1]

            if self._progress_bar_ui is None:
                self._progress_bar_ui = ProgressBarUi(self._state, spriteref.WORLD_UI_LAYER)

            prog_bar_size = self._progress_bar_ui.get_size()
            self._progress_bar_ui.set_xy((cx - prog_bar_size[0] // 2, y0 + y))
            self._progress_bar_ui.update()
        else:
            self._top_panel_ui = None
            self._progress_bar_ui = None

        fail_msg = "\n".join(self._state.get_failure_message())
        if len(fail_msg) > 0:
            if self._failure_message_bg is None:
                self._failure_message_bg = sprites.ImageSprite(spritesheets.get_white_square_img(0.5), 0, 0,
                                                               spriteref.WORLD_UI_LAYER,
                                                               color=colors.PERFECT_BLACK)
            if self._failure_message_text is None:
                self._failure_message_text = sprites.TextSprite(spriteref.WORLD_UI_LAYER, 0, 0, fail_msg,
                                                                scale=1, depth=-10, color=colors.WHITE,
                                                                alignment=sprites.TextSprite.CENTER,
                                                                outline_color=colors.PERFECT_BLACK)
            self._failure_message_text.update(new_text=fail_msg)

            size = self._failure_message_text.size()
            cxy = self.get_world_view().get_camera_center_in_world()
            fail_rect = [cxy[0] - size[0] // 2, cxy[1] - size[1] // 2, size[0], size[1]]

            bg_inset = 2
            self._failure_message_bg = self._failure_message_bg.update(new_x=fail_rect[0] - bg_inset,
                                                                       new_y=fail_rect[1] - bg_inset,
                                                                       new_raw_size=(fail_rect[2] + bg_inset * 2,
                                                                                     fail_rect[3] + bg_inset * 2))
            self._failure_message_text.update(new_x=fail_rect[0], new_y=fail_rect[1])
        else:
            self._failure_message_bg = None
            self._failure_message_text = None

    def all_sprites(self):
        for spr in _BaseGameScene.all_sprites(self):
            yield spr
        for spr in dialog.DialogScene.all_sprites(self):
            yield spr
        if self._top_panel_ui is not None:
            for spr in self._top_panel_ui.all_sprites():
                yield spr
        if self._progress_bar_ui is not None:
            for spr in self._progress_bar_ui.all_sprites():
                yield spr
        yield self._failure_message_text
        yield self._failure_message_bg

    def get_clear_color(self):
        return self.get_world_view().get_current_bg_color()


class DebugGameScene(RealGameScene):

    def __init__(self, bp, edit_scene):
        RealGameScene.__init__(self, bp,
                               lambda time: self.get_manager().set_next_scene(DebugGameScene(bp, edit_scene)),
                               lambda: self.get_manager().set_next_scene(self.edit_scene))
        self.edit_scene = edit_scene

    def update(self):
        super().update()

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.TOGGLE_EDIT_MODE)):
            self.handle_esc_pressed()

    def handle_esc_pressed(self):
        self.get_manager().set_next_scene(self.edit_scene)


class GamePausedScene(OptionSelectScene):

    def __init__(self, game_scene: RealGameScene, on_exit):
        self._game_scene = game_scene
        self._on_exit = on_exit

        OptionSelectScene.__init__(self, title="Paused")
        self.add_option("continue", lambda: self.jump_to_scene(game_scene), esc_option=True)

        self._bg_sprite = None

        def _do_reset(player_idx):
            self._game_scene.do_reset(idx=player_idx)
            self.jump_to_scene(self._game_scene)

        # iterate over [active_idx, active_idx - 1, active_idx - 2, ..., 1]
        active_idx = game_scene.get_state().get_active_player_idx()
        for i in range(active_idx, 0, -1):
            player_type = self._game_scene.get_state().get_player_type(i)
            self.add_option("reset Unit {}".format(player_type.get_name()), lambda idx=i: _do_reset(idx))
        self.add_option("restart level", lambda: _do_reset(0))
        self.add_option("quit", lambda: self._on_exit())

    def update_sprites(self):
        if self._bg_sprite is None:
            self._bg_sprite = sprites.ImageSprite.new_sprite(spriteref.UI_BG_LAYER, depth=500)
        model = spritesheets.get_white_square_img(0.75)
        size = renderengine.get_instance().get_game_size()
        self._bg_sprite = self._bg_sprite.update(new_model=model,
                                                 new_color=colors.PERFECT_BLACK,
                                                 new_raw_size=size)
        self._game_scene.update_sprites()

    def all_sprites(self):
        for spr in self._game_scene.all_sprites():
            yield spr
        yield self._bg_sprite
        for spr in super().all_sprites():
            yield spr


class StatsScene(OptionSelectScene):

    def __init__(self, overworld_state: overworld.OverworldState, next_scene, title="Stats"):
        super().__init__(title=title)
        if overworld_state is None:
            overworld_scene = _make_overworlds_scene()  # XXX eesh
            overworld_state = overworld_scene.state
        self.set_description(self._calc_stats_text(overworld_state), alignment=sprites.TextSprite.CENTER, wrap=False)
        self.add_option("continue", lambda: self.jump_to_scene(next_scene), esc_option=True)

    def _calc_stats_text(self, overworld_state):
        n_completed = 0
        n_total = 0
        total_level_time = 0
        total_playtime = gs.get_instance().get_save_data().get_total_playtime()
        in_game_playtime = gs.get_instance().get_save_data().get_total_in_game_playtime()
        for ow in overworld_state.overworld_pack.all_overworlds():
            n_completed_in_sector, n_levels_in_sector, total_ticks_in_sector = overworld_state.get_sector_stats(ow.ref_id)
            n_completed += n_completed_in_sector
            n_total += n_levels_in_sector
            total_level_time += total_ticks_in_sector

        if n_completed < n_total:
            completed_str = "{:.1f}%".format(100 * n_completed / n_total)
            best_time_str = None  # no reason to show this if you haven't 100%ed the game
        else:
            completed_str = f"{n_completed}/{n_total}"
            best_time_str = f"{util.ticks_to_time_string(total_level_time, show_minutes_if_zero=True)}"

        return "\n".join(s for s in [
            f"levels completed: {completed_str}",
            None if best_time_str is None else "sum of best times: {best_time_str}",
            "",
            f"total playtime: {util.ticks_to_time_string(total_playtime, show_minutes_if_zero=True)}",
            f"active playtime: {util.ticks_to_time_string(in_game_playtime, show_minutes_if_zero=True)}"
        ] if s is not None)


class LevelMetaDataEditScene(OptionSelectScene):

    def __init__(self, bp: blueprints.LevelBlueprint, on_exit):
        """
        :param bp:
        :param on_exit: LevelBlueprint -> None
        """
        OptionSelectScene.__init__(self, title="Edit Metadata", opts_per_page=7)
        self._base_bp = bp
        self._on_exit = on_exit

        self._add_text_edit_option("level name: ", blueprints.NAME, bp)
        self._add_popout_text_edit_option("description: ", blueprints.DESCRIPTION, bp)
        self._add_text_edit_option("level ID: ", blueprints.LEVEL_ID, bp)
        self._add_text_edit_option("time limit: ", blueprints.TIME_LIMIT, bp,
                                   to_str=lambda t: util.ticks_to_time_string(t),
                                   from_str=lambda t_str: util.time_string_to_ticks(t_str, or_else=3600),
                                   char_limit=8,
                                   allowed_chars="0123456789:")
        self._add_players_edit_option("players: ", bp)

        self.add_option("apply", lambda: self._on_exit(self._base_bp), esc_option=True)

    def _add_text_edit_option(self, name, attribute_id, bp, to_str=str, from_str=str, char_limit=32,
                              allowed_chars=ui.TextEditElement.ASCII_CHARS):
        current_val = to_str(bp.get_attribute(attribute_id))
        def _action():
            edit_scene = TextEditScene(name,
                                       default_text=current_val,
                                       on_accept=lambda manager, final_text: manager.set_next_scene(
                                           LevelMetaDataEditScene(self._base_bp.copy_with(
                                               edits={attribute_id: from_str(final_text)}),
                                                                  self._on_exit)),
                                       on_cancel=lambda manager: manager.set_next_scene(
                                           LevelMetaDataEditScene(self._base_bp, self._on_exit)),
                                       char_limit=char_limit,
                                       allowed_chars=allowed_chars)
            self.jump_to_scene(edit_scene)

        self.add_option(name + (current_val if len(current_val) < 16 else current_val[:13] + "..."), _action)

    def _add_popout_text_edit_option(self, name, attribute_id, bp, to_str=str, from_str=str):
        current_val = to_str(bp.get_attribute(attribute_id))

        def _action():
            import src.utils.threadutils as threadutils
            fut = threadutils.prompt_for_text("Edit Level Attribute: \"{}\"".format(attribute_id),
                                              "Enter the new value: ", current_val, do_async=True)
            import time
            import pygame

            while not fut.is_done():
                time.sleep(1 / 20)
                pygame.event.clear()
                pygame.display.flip()

            res = fut.get_val()
            if res is not None:
                new_bp = self._base_bp.copy_with(edits={attribute_id: from_str(res)})
                self.get_manager().set_next_scene(LevelMetaDataEditScene(new_bp, self._on_exit))
            else:
                self.get_manager().set_next_scene(LevelMetaDataEditScene(self._base_bp, self._on_exit)),

        self.add_option(name + (current_val if len(current_val) < 16 else current_val[:13] + "..."), _action)

    def _add_players_edit_option(self, name, bp):
        import src.game.playertypes as playertypes

        def _to_str(player_ids):
            res = []
            for pid in player_ids:
                res.append(playertypes.PlayerTypes.get_type(pid).get_letter())
            return "".join(res)

        def _to_player_ids(letters):
            res = []
            for letter in letters:
                try:
                    res.append(playertypes.PlayerTypes.get_type(letter.upper()).get_id())
                except ValueError:
                    print("ERROR: invalid player letter: {}".format(letter))
            if len(res) == 0:
                res.append(playertypes.PlayerTypes.FAST.get_id())
            return res

        self._add_text_edit_option(name, blueprints.PLAYERS, bp,
                                   to_str=_to_str,
                                   from_str=_to_player_ids,
                                   char_limit=4,
                                   allowed_chars="ABCDabcd")


class LevelEditObjectButton(ui.UiElement):

    def __init__(self, scene: 'LevelEditGameScene', icon, spec_type):
        super().__init__()
        self.scene: 'LevelEditGameScene' = scene
        self.icon = icon
        self.spec_type = spec_type

        self._outline_sprite = None
        self._icon_sprite = None

    def update(self):
        self.update_sprites()

    def is_selected(self):
        return self.spec_type is not None and self.scene.get_spec_type_to_place() == self.spec_type

    def _calc_outline_color(self):
        # TODO color for mouse hover
        return colors.DARK_GRAY if not self.is_selected() else colors.PERFECT_YELLOW

    def update_sprites(self):
        raw_xy = self.get_xy(absolute=True)

        if self._outline_sprite is None:
            self._outline_sprite = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER, depth=10)
        self._outline_sprite = self._outline_sprite.update(new_model=spriteref.level_builder_sheet().level_builder_button_outline,
                                                           new_x=raw_xy[0], new_y=raw_xy[1],
                                                           new_color=self._calc_outline_color())
        if self._icon_sprite is None:
            self._icon_sprite = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER)
        self._icon_sprite = self._icon_sprite.update(new_model=self.icon,
                                                     new_x=raw_xy[0], new_y=raw_xy[1],
                                                     new_color=colors.WHITE)  # TODO probably need special handling for colored buttons

    def all_sprites(self):
        yield self._outline_sprite
        yield self._icon_sprite

    def get_size(self):
        return (16, 16)

    def handle_click(self, xy, button=1) -> bool:
        self.scene.set_spec_type_to_place(self.spec_type)
        return True


class LevelEditObjectSidepanel(ui.UiElement):
    # NO STATE ALLOWED IN THIS CLASS
    # don't even think about it

    def __init__(self, scene):
        super().__init__()

        self.page_selector_imgs = [None] * 5  # imgs

        self.all_buttons = {}  # x, y -> LevelEditObjectButton
        self.bg_fill = None
        self.bg_panels = [None] * 5  # top, mid1, divider, mid2, bottom
        self.expand_button = None

        self.scene = scene
        self.bg_opacity = 0.8

    def add_button(self, xy, button):
        self.all_buttons[xy] = button
        self.add_child(button)

    def handle_click(self, xy, button=1):
        self.scene.set_spec_type_to_place(None)
        return True

    def update_sprites(self):
        xy = self.get_xy(absolute=True)
        xy = (xy[0] + 4, xy[1])
        size = self.get_panel_size()

        if self.bg_fill is None:
            model = spritesheets.get_instance().get_sheet(spritesheets.WhiteSquare.SHEET_ID).get_sprite(self.bg_opacity)
            self.bg_fill = sprites.ImageSprite(model, 0, 0, spriteref.UI_BG_LAYER)
        self.bg_fill = self.bg_fill.update(new_x=xy[0], new_y=xy[1], new_raw_size=size,
                                           new_color=colors.PERFECT_BLACK, new_depth=10)

        ys = [0, 8, size[1] - 64, size[1] - 64 + 8, size[1] - 8, size[1]]
        for i in range(len(self.bg_panels)):
            if i == 0:
                model = spriteref.level_builder_sheet().level_builder_panel_top_outline
            elif i == 2:
                model = spriteref.level_builder_sheet().level_builder_panel_divider_outline
            elif i == 4:
                model = spriteref.level_builder_sheet().level_builder_panel_bottom_outline
            else:
                model = spriteref.level_builder_sheet().level_builder_panel_mid_outline

            panel = self.bg_panels[i]
            if panel is None:
                panel = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER)
            self.bg_panels[i] = panel.update(new_model=model, new_x=xy[0], new_y=ys[i],
                                             new_raw_size=(size[0], ys[i + 1] - ys[i]),
                                             new_color=colors.WHITE)

        selected_page = self.scene.get_selected_object_page()
        for i in range(len(self.page_selector_imgs)):
            if self.page_selector_imgs[i] is None:
                self.page_selector_imgs[i] = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER)
            model = spriteref.level_builder_sheet().level_builder_page_buttons[i][1 if i == selected_page else 0]
            self.page_selector_imgs[i] = self.page_selector_imgs[i].update(new_model=model,
                                                                           new_x=xy[0] + 8 + 16 * i, new_y=xy[1] + 8,
                                                                           new_color=colors.WHITE)

        if self.expand_button is None:
            self.expand_button = sprites.ImageSprite.new_sprite(spriteref.UI_BG_LAYER)
        if self.scene.is_panel_expanded():
            expand_model = spriteref.level_builder_sheet().level_builder_contract_button
        else:
            expand_model = spriteref.level_builder_sheet().level_builder_expand_button
        self.expand_button = self.expand_button.update(new_model=expand_model, new_x=xy[0] - 8, new_y=xy[1])

    def _update_button_positions(self):
        for xy in self.all_buttons:
            xpos = 4 + 8 + xy[0] * 16
            ypos = 24 + xy[1] * 16
            self.all_buttons[xy].set_xy((xpos, ypos))

    def update(self):
        self._update_button_positions()
        self.update_sprites()

    def get_panel_size(self):
        return 96, renderengine.get_instance().get_game_size()[1]

    def get_size(self):
        panel_size = self.get_panel_size()
        # include width of the expand/contract button
        return (panel_size[0] + 4, panel_size[1])

    def all_sprites(self):
        yield self.bg_fill
        for page_btn in self.page_selector_imgs:
            yield page_btn
        for panel in self.bg_panels:
            yield panel
        yield self.expand_button


class LevelEditGameScene(_BaseGameScene):

    def __init__(self, bp: blueprints.LevelBlueprint, prev_scene_provider=None):
        """
        world_type: an int or level blueprint
        """
        _BaseGameScene.__init__(self)

        self.orig_bp = bp
        self._level_id = bp.level_id()

        self.mouse_mode = NormalMouseMode(self)

        self.edit_queue = []
        self.edit_queue_idx = -1
        self.edit_queue_max_size = 32

        self.selected_specs = set()
        self.all_spec_blobs = [s[0] for s in bp.all_entities()]
        self.entities_for_specs = {}  # SpecType -> List of Entities

        cs = gs.get_instance().cell_size
        self.edit_resolution = cs  # how far blocks move & change in size when you press the key commands
        self.resolution_options = [cs // 8, cs // 4, cs // 2, cs]  # essentially assumes cs >= 16
        self.camera_speed = 8  # ticks per move (smaller == faster)

        self.object_pallette = build_object_pallette()
        self.sidepanel = self._setup_sidepanel()

        self._dirty = False  # whether the current state is different from the last-saved state

        self.stamp_current_state()
        self.setup_new_world(bp)

        self._prev_scene_provider = prev_scene_provider

    def _setup_sidepanel(self):
        res = LevelEditObjectSidepanel(self)
        for i in range(0, 25):
            if i < len(spriteref.level_builder_sheet().level_builder_new_obj_buttons):
                icon = spriteref.level_builder_sheet().level_builder_new_obj_buttons[i]
            else:
                icon = None
            spec_type = self.get_pallette_object_type(i)
            res.add_button((i % 5, i // 5), LevelEditObjectButton(self, icon, spec_type))

        for i in range(0, 10):
            if i < len(spriteref.level_builder_sheet().level_builder_misc_buttons):
                icon = spriteref.level_builder_sheet().level_builder_misc_buttons[i]
            else:
                icon = None
            # TODO misc edit buttons
        return res

    def get_selected_object_page(self):
        return 0

    def is_panel_expanded(self):
        return True

    def get_spec_type_to_place(self):
        if isinstance(self.mouse_mode, ObjectPlacementMouseMode):
            return self.mouse_mode.spec_type
        else:
            return None

    def set_spec_type_to_place(self, spec_type):
        if spec_type is not None:
            self.set_mouse_mode(ObjectPlacementMouseMode(spec_type, self))
        else:
            self.set_mouse_mode(None)

    def stamp_current_state(self):
        cur_specs = [s.copy() for s in self.all_spec_blobs]
        cur_selection = set(self.selected_specs)
        state = EditorState(cur_specs, cur_selection)

        if 0 <= self.edit_queue_idx < len(self.edit_queue):
            if self.edit_queue[self.edit_queue_idx] == state:
                return  # no changes were made, just abort

        self.edit_queue_idx += 1
        if len(self.edit_queue) >= self.edit_queue_idx:
            # if there are non-applied edits ahead of us, blow them away
            self.edit_queue = self.edit_queue[0 : self.edit_queue_idx]
        self.edit_queue.append(state)

        if len(self.edit_queue) > self.edit_queue_max_size:
            self.edit_queue = self.edit_queue[-self.edit_queue_max_size:]

    def mark_dirty(self):
        self._dirty = True

    def is_dirty(self):
        return self._dirty

    def undo(self):
        self.edit_queue_idx = util.bound(self.edit_queue_idx, 0, len(self.edit_queue))
        if self.edit_queue_idx > 0:
            self.edit_queue_idx -= 1
        else:
            return
        state_to_apply = self.edit_queue[self.edit_queue_idx]
        self._apply_state(state_to_apply)
        self.mark_dirty()

    def redo(self):
        self.edit_queue_idx = util.bound(self.edit_queue_idx, 0, len(self.edit_queue))
        if self.edit_queue_idx < len(self.edit_queue) - 1:
            self.edit_queue_idx += 1
        else:
            return
        state_to_apply = self.edit_queue[self.edit_queue_idx]
        self._apply_state(state_to_apply)
        self.mark_dirty()

    def set_mouse_mode(self, mode):
        if self.mouse_mode is not None:
            self.mouse_mode.deactivate()

        if mode is None:
            self.mouse_mode = NormalMouseMode(self)
        else:
            self.mouse_mode = mode

        self.mouse_mode.activate()

    def get_selected_specs(self):
        # TODO pretty inefficient due to poor design
        return [s for s in self.all_spec_blobs if self.is_selected(s)]

    def _mutate_selected_specs(self, funct, select_results=True, undoable=True):
        """
        funct: lambda spec -> spec, or a list of specs
        returns: (list of orig specs, list of new specs)
        """
        # TODO this is all pretty inefficient
        orig_specs = []
        new_specs = []
        if len(self.selected_specs) > 0:
            to_modify = self.get_selected_specs()
            self.deselect_all()

            for orig_s in to_modify:
                orig_specs.append(orig_s)
                try:
                    res = util.listify(funct(orig_s))
                except Exception:
                    print("ERROR: failed to modify spec: {}".format(orig_s))
                    traceback.print_exc()
                    res = [orig_s]  # keep it as-is

                if len(res) == 0:
                    self.all_spec_blobs.remove(orig_s)
                else:
                    orig_idx = self.all_spec_blobs.index(orig_s)
                    self.all_spec_blobs[orig_idx] = res[0]
                    for i in range(1, len(res)):
                        self.all_spec_blobs.append(res[i])
                    for new_s in res:
                        new_specs.append(new_s)
                        if select_results:
                            self.set_selected(new_s, select=True)
            if undoable:
                self.stamp_current_state()

            self.setup_new_world(self.build_current_bp())
            self.mark_dirty()

        return orig_specs, new_specs

    def copy_selection_to_clipboard(self):
        selected_specs = self.get_selected_specs()
        as_json_str = json.dumps(selected_specs)  # these should always be serializable (that's the whole point)
        util.set_clipboard(as_json_str)
        print("INFO: copied {} spec(s) to clipboard".format(len(selected_specs)))

    def cut_selection_to_clipboard(self):
        self.copy_selection_to_clipboard()
        self.delete_selection()

    def paste_clipboard_at_mouse(self):
        raw_data = util.get_clipboard()
        needs_undo_stamp = False
        try:
            if inputs.get_instance().mouse_in_window():
                screen_pos = inputs.get_instance().mouse_pos()
                mouse_pos_in_world = self._world_view.screen_pos_to_world_pos(screen_pos)
                spawn_x = mouse_pos_in_world[0] - (mouse_pos_in_world[0] % self.edit_resolution)
                spawn_y = mouse_pos_in_world[1] - (mouse_pos_in_world[1] % self.edit_resolution)

                blob = json.loads(raw_data) # should be a list of specs
                min_xy = [float('inf'), float('inf')]
                for spec in blob:
                    if blueprints.X in spec:
                        min_xy[0] = min(min_xy[0], int(spec[blueprints.X]))
                    if blueprints.Y in spec:
                        min_xy[1] = min(min_xy[1], int(spec[blueprints.Y]))

                shifted_specs = []
                move_x = spawn_x - min_xy[0] if min_xy[0] < float('inf') else 0
                move_y = spawn_y - min_xy[1] if min_xy[1] < float('inf') else 0
                for spec in blob:
                    shifted_specs.append(blueprints.SpecUtils.move(spec, (move_x, move_y)))

                if len(shifted_specs) > 0:
                    needs_undo_stamp = True
                    self.deselect_all()
                    for spec in shifted_specs:
                        self.all_spec_blobs.append(spec)
                        self.set_selected(spec, select=True)

                    print("INFO: pasted {} spec(s) into world".format(len(shifted_specs)))

        except Exception:
            print("ERROR: failed to paste data from clipboard: {}".format(raw_data))
            traceback.print_exc()

        self.setup_new_world(self.build_current_bp())
        if needs_undo_stamp:
            self.stamp_current_state()
            self.mark_dirty()

    def delete_selection(self):
        orig, new = self._mutate_selected_specs(lambda s: [])
        print("INFO: deleted {} spec(s)".format(len(orig)))

    def move_selection(self, dx, dy):
        move_funct = lambda s: blueprints.SpecUtils.move(s, (dx * self.edit_resolution, dy * self.edit_resolution))
        self._mutate_selected_specs(move_funct)

    def resize_selection(self, dx, dy):
        resize_funct = lambda s: blueprints.SpecUtils.resize(s, (dx * self.edit_resolution, dy * self.edit_resolution))
        self._mutate_selected_specs(resize_funct)

    def add_point_to_selection(self, x, y):
        add_funct = lambda s: blueprints.SpecUtils.add_point(s, (x, y))
        self._mutate_selected_specs(add_funct)

    def remove_point_from_selection(self, x, y):
        rem_funct = lambda s: blueprints.SpecUtils.remove_points(s, (x, y), r=16)
        self._mutate_selected_specs(rem_funct)

    def clear_points_from_selection(self):
        clear_funct = lambda s: blueprints.SpecUtils.clear_points(s)
        self._mutate_selected_specs(clear_funct)

    def cycle_selection_type(self, steps):
        cycle_funct = lambda s: blueprints.SpecUtils.cycle_subtype(s, steps)
        self._mutate_selected_specs(cycle_funct)

    def cycle_selection_color(self, steps):
        cycle_func = lambda s: blueprints.SpecUtils.cycle_color(s, steps)
        self._mutate_selected_specs(cycle_func)

    def cycle_selection_art(self, steps):
        cycle_func = lambda s: blueprints.SpecUtils.cycle_art(s, steps)
        self._mutate_selected_specs(cycle_func)

    def toggle_selection_inverted(self):
        toggle_func = lambda s: blueprints.SpecUtils.toggle_inverted(s)
        self._mutate_selected_specs(toggle_func)

    def handle_advanced_edit_pressed(self):
        advanced_edit_func = lambda s: blueprints.SpecUtils.open_advanced_editor(s)
        self._mutate_selected_specs(advanced_edit_func)

    def _apply_state(self, state: 'EditorState'):
        self.all_spec_blobs = [s.copy() for s in state.all_specs]

        self.setup_new_world(self.build_current_bp())
        for spec in self.all_spec_blobs:
            if util.to_key(spec) in state.selected_specs:
                self.set_selected(spec, select=True)
            else:
                self.set_selected(spec, select=False)

    def build_current_bp(self):
        return blueprints.LevelBlueprint.build(self.orig_bp.name(),
                                               self._level_id,
                                               self.orig_bp.get_player_types(),
                                               self.orig_bp.time_limit(),
                                               self.orig_bp.description(),
                                               self.orig_bp.explicit_song_id(),
                                               self.all_spec_blobs,
                                               self.orig_bp.special_flags(),
                                               directory=self.orig_bp.directory)

    def get_specs_at(self, world_xy):
        res = []
        for spec in self.all_spec_blobs:
            r = blueprints.SpecUtils.get_rect(spec, default_size=gs.get_instance().cell_size)
            if r is None:
                continue
            elif util.rect_contains(r, world_xy):
                res.append(spec)
        return res

    def save_to_disk(self, force_new_id=False):
        bp_to_save = self.build_current_bp()

        if force_new_id or bp_to_save.level_id() in (None, "", "???"):
            default_text = self.build_current_bp().level_id()

            def _do_accept(manager, level_id):
                self._level_id = level_id
                self.save_to_disk()
                manager.set_next_scene(self)

            self.jump_to_scene(TextEditScene("enter new level id:", default_text=default_text,
                                             on_cancel=lambda mgr: mgr.set_next_scene(self),
                                             on_accept=_do_accept,
                                             allowed_chars=ui.TextEditElement.LEVEL_ID_CHARS))
        else:
            file_to_use = bp_to_save.get_filepath()
            is_overwriting = os.path.exists(file_to_use)

            save_result = blueprints.write_level_to_file(bp_to_save, file_to_use)

            if save_result:
                if is_overwriting:
                    print("INFO: successfully overwrote {}".format(file_to_use))
                else:
                    print("INFO: successfully created {}".format(file_to_use))
                self._dirty = False
            else:
                print("INFO: failed to save level to {}".format(file_to_use))

    def setup_new_world(self, bp, reset_camera=False):
        camera_pos = None
        camera_zoom = None

        if self.get_world_view() is not None and not reset_camera:
            camera_pos = self.get_world_view().get_camera_pos_in_world()
            camera_zoom = self.get_world_view().get_zoom()

        super().setup_new_world(bp)
        self.get_world().set_is_being_edited(True)
        self._refresh_entities()

        self.get_world_view().set_free_camera(True)

        if camera_pos is not None:
            self.get_world_view().set_camera_pos_in_world(camera_pos)
        if camera_zoom is not None:
            self.get_world_view().set_zoom(camera_zoom)

    def _refresh_entities(self):
        self.entities_for_specs.clear()

        for ent in self.get_world().all_entities():
            spec = ent.get_spec()
            if spec is not None:
                as_key = util.to_key(spec)
                if as_key not in self.entities_for_specs:
                    self.entities_for_specs[as_key] = []
                self.entities_for_specs[as_key].append(ent)

            if util.to_key(spec) in self.selected_specs:
                ent.set_color_override(self._get_selected_entity_color(ent))
                ent.set_selected_in_editor(True)
            else:
                ent.set_color_override(None)
                ent.set_selected_in_editor(False)

    def update(self):
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.RESET)):
            self.get_world_view().set_camera_pos_in_world((0, 0))

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.TOGGLE_EDIT_MODE)):
            self.get_manager().set_next_scene(DebugGameScene(self.build_current_bp(), self))

        if configs.is_dev and inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.TOGGLE_SPRITE_MODE_DEBUG)):
            debug.toggle_debug_sprite_mode()

        self.mouse_mode.handle_drag_events()
        self.mouse_mode.handle_key_events()

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.SAVE_AS)):
            self.save_to_disk(force_new_id=True)
        elif inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.SAVE)):
            self.save_to_disk()

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.INCREASE_EDIT_RESOLUTION)):
            self.adjust_edit_resolution(True)
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.DECREASE_EDIT_RESOLUTION)):
            self.adjust_edit_resolution(False)

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.UNDO)):
            self.undo()
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.REDO)):
            self.redo()

        camera_move_x = 0
        if inputs.get_instance().time_held(keybinds.get_instance().get_keys(const.MOVE_CAMERA_RIGHT)) % self.camera_speed == 1:
            camera_move_x += 1
        if inputs.get_instance().time_held(keybinds.get_instance().get_keys(const.MOVE_CAMERA_LEFT)) % self.camera_speed == 1:
            camera_move_x -= 1

        camera_move_y = 0
        if inputs.get_instance().time_held(keybinds.get_instance().get_keys(const.MOVE_CAMERA_DOWN)) % self.camera_speed == 1:
            camera_move_y += 1
        if inputs.get_instance().time_held(keybinds.get_instance().get_keys(const.MOVE_CAMERA_UP)) % self.camera_speed == 1:
            camera_move_y -= 1

        if camera_move_x != 0 or camera_move_y != 0:
            zoom = self.get_world_view().get_zoom()
            cells = 1 if inputs.get_instance().shift_is_held() else 2
            dx = cells * gs.get_instance().cell_size // zoom * camera_move_x
            dy = cells * gs.get_instance().cell_size // zoom * camera_move_y
            self.get_world_view().move_camera_in_world((dx, dy))

        sidepanel_size = self.sidepanel.get_size()
        screen_size = renderengine.get_instance().get_game_size()
        # TODO have it move incrementally while it's expanding / contracting
        self.sidepanel.set_xy((screen_size[0] - sidepanel_size[0], 0))
        self.sidepanel.update_self_and_kids()

        super().update()

    def handle_esc_pressed(self):
        if not isinstance(self.mouse_mode, NormalMouseMode):
            # if in a non-default mousemode, esc exits the mode
            self.set_mouse_mode(None)
            return

        if self.is_dirty():
            desc = "you have unsaved changes."
        else:
            desc = None

        # TODO would be really pro to jump back to the level select screen with this level highlighted
        manager = self.get_manager()
        current_bp = self.build_current_bp()

        def _handle_new_bp(new_bp):
            if new_bp != current_bp:
                manager.set_next_scene(LevelEditGameScene(new_bp))
            else:
                manager.set_next_scene(self)

        def _do_final_exit():
            prev_scene = None
            if self._prev_scene_provider is not None:
                prev_scene = self._prev_scene_provider()

            if prev_scene is None:
                prev_scene = LevelSelectForEditScene(configs.level_edit_dirs)

            self.get_manager().set_next_scene(prev_scene)

        def _new_editor_scene(new_bp: blueprints.LevelBlueprint):
            return LevelEditGameScene(new_bp, prev_scene_provider=self._prev_scene_provider)

        self.jump_to_scene(LevelEditorPauseMenu(current_bp,
                                                _handle_new_bp,
                                                _do_final_exit,
                                                _new_editor_scene,
                                                description=desc))
        sounds.play_sound(soundref.MENU_BACK)

    def adjust_edit_resolution(self, increase):
        if self.edit_resolution in self.resolution_options:
            cur_idx = self.resolution_options.index(self.edit_resolution)
            new_idx = util.bound(cur_idx + (1 if increase else -1), 0, len(self.resolution_options) - 1)
            self.edit_resolution = self.resolution_options[new_idx]
        else:
            self.edit_resolution = self.resolution_options[-1]
        print("INFO: new editor resolution: {}".format(self.edit_resolution))

    def handle_click_at(self, screen_xy, world_xy, button=1):
        if self.sidepanel.send_click_to_self_and_kids(screen_xy, absolute=True, button=button):
            pass
        else:
            super().handle_click_at(screen_xy, world_xy, button=button)
            self.mouse_mode.handle_click_at(world_xy, button=button)

    def is_selected(self, spec):
        return util.to_key(spec) in self.selected_specs

    def deselect_all(self):
        all_selects = [s for s in self.selected_specs]
        for s in all_selects:
            self.set_selected(s, select=False)

    def select_all(self):
        for s in self.all_spec_blobs:
            self.set_selected(s, select=True)

    def _get_selected_entity_color(self, ent):
        color_id = ent.get_color_id()
        if color_id is not None:
            return spriteref.get_color(color_id, dark=True)
        else:
            return colors.darken(ent.get_color(ignore_override=True), 0.30)

    def set_selected(self, spec, select=True):
        if spec is None:
            return
        else:
            key = util.to_key(spec)
            if select:
                self.selected_specs.add(key)
                if key in self.entities_for_specs:
                    for ent in self.entities_for_specs[key]:
                        ent.set_color_override(self._get_selected_entity_color(ent))
                        ent.set_selected_in_editor(True)
            else:
                if key in self.selected_specs:
                    self.selected_specs.remove(key)
                if key in self.entities_for_specs:
                    for ent in self.entities_for_specs[key]:
                        ent.set_color_override(None)
                        ent.set_selected_in_editor(False)

    def all_sprites(self):
        for spr in super().all_sprites():
            yield spr
        for spr in self.sidepanel.all_sprites_from_self_and_kids():
            yield spr

    def _create_new_world(self, world_type=0):
        if isinstance(world_type, blueprints.LevelBlueprint):
            self.setup_new_world(world_type)
        else:
            types = ("moving_plat", "full_level", "floating_blocks", "start_and_end")
            type_to_use = types[world_type % len(types)]
            print("INFO: activating test world: {}".format(type_to_use))

            if type_to_use == types[0]:
                self._world = blueprints.get_test_blueprint_0().create_world()
            elif type_to_use == types[1]:
                self._world = blueprints.get_test_blueprint_1().create_world()
            elif type_to_use == types[2]:
                self._world = blueprints.get_test_blueprint_2().create_world()
            elif type_to_use == types[3]:
                self._world = blueprints.get_test_blueprint_3().create_world()
            else:
                return

            self._world_view = worldview.WorldView(self._world)

    def get_pallette_object(self, idx):
        if 0 <= idx < len(self.object_pallette):
            return dict(self.object_pallette[idx])
        else:
            return None

    def get_pallette_object_type(self, idx):
        obj = self.get_pallette_object(idx)
        if obj is not None:
            return blueprints.SpecTypes.get(obj[blueprints.TYPE_ID])
        else:
            return None

    def get_mouse_position_in_world(self, snap_to_grid=True):
        if not inputs.get_instance().mouse_in_window():
            return None
        else:
            screen_pos = inputs.get_instance().mouse_pos()
            mouse_pos_in_world = self._world_view.screen_pos_to_world_pos(screen_pos)
            if not snap_to_grid:
                return mouse_pos_in_world
            else:
                return self.snap_world_coords_to_edit_grid(mouse_pos_in_world)

    def snap_world_coords_to_edit_grid(self, world_xy):
        snapped_x = world_xy[0] - (world_xy[0] % self.edit_resolution)
        snapped_y = world_xy[1] - (world_xy[1] % self.edit_resolution)
        return (snapped_x, snapped_y)

    def spawn_pallette_object_at(self, idx, xy):
        spec_to_spawn = self.get_pallette_object(idx)
        if spec_to_spawn is not None and xy is not None:
            spec_to_spawn = blueprints.SpecUtils.set_xy(spec_to_spawn, xy)

            self.all_spec_blobs.append(spec_to_spawn)
            self.stamp_current_state()
            self.setup_new_world(self.build_current_bp())

    def spawn_object_at(self, spec_type, xy):
        spec_blob = spec_type.get_default_blob()
        if spec_blob is not None and xy is not None:
            spec_to_spawn = blueprints.SpecUtils.set_xy(spec_blob, xy)

            self.all_spec_blobs.append(spec_to_spawn)
            self.stamp_current_state()
            self.setup_new_world(self.build_current_bp())


class EditEvent:
    def __init__(self, old_state, new_state):
        self.old_state = old_state
        self.new_state = new_state


class EditorState:
    def __init__(self, all_specs, selected_specs):
        self.all_specs = all_specs
        self.selected_specs = selected_specs


class MouseMode:

    def __init__(self, scene: LevelEditGameScene):
        self.scene = scene

    def activate(self):
        pass

    def deactivate(self):
        pass

    def handle_drag_events(self):
        pass

    def handle_click_at(self, world_xy, button=1):
        pass

    def handle_key_events(self):
        pass

    def _get_activated_spawn_idx(self):
        for i in range(0, len(const.OPTIONS)):
            if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.OPTIONS[i])):
                spawn_idx = i
                # 80 different choices!~
                if inputs.get_instance().shift_is_held():
                    spawn_idx += 10
                if inputs.get_instance().ctrl_is_held():
                    spawn_idx += 20
                if inputs.get_instance().alt_is_held():
                    spawn_idx += 40
                return spawn_idx
        return None


class NormalMouseMode(MouseMode):

    def __init__(self, scene: LevelEditGameScene):
        super().__init__(scene)

    def handle_drag_events(self):
        if inputs.get_instance().mouse_is_dragging(button=3):
            drag_this_frame = inputs.get_instance().mouse_drag_this_frame(button=3)
            if drag_this_frame is not None:
                dxy = util.sub(drag_this_frame[1], drag_this_frame[0])
                dxy = util.mult(dxy, -1 / self.scene.get_world_view().get_zoom())
                self.scene.get_world_view().move_camera_in_world(dxy)
                self.scene.get_world_view().set_free_camera(True)

    def handle_click_at(self, world_xy, button=1):
        if button == 1:
            specs_at_click = self.scene.get_specs_at(world_xy)
            holding_shift = inputs.get_instance().shift_is_held()
            holding_ctrl = inputs.get_instance().ctrl_is_held()
            if len(specs_at_click) > 0:
                top_prio = max(blueprints.SpecUtils.get_priority(spec) for spec in specs_at_click)
                specs_at_click = [spec for spec in specs_at_click if blueprints.SpecUtils.get_priority(spec) >= top_prio]
                if holding_shift or holding_ctrl:
                    for s in specs_at_click:
                        self.scene.set_selected(s, select=True)
                else:
                    self.scene.deselect_all()
                    idx = int(random.random() * len(specs_at_click))  # TODO pls
                    self.scene.set_selected(specs_at_click[idx], select=True)
            else:
                self.scene.deselect_all()
            self.scene.stamp_current_state()

    def handle_key_events(self):
        mouse_xy = self.scene.get_mouse_position_in_world(snap_to_grid=False)
        edit_xy = self.scene.get_mouse_position_in_world(snap_to_grid=True)

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.SAVE_AS)):
            # XXX this keybind tends to conflict with others (shift-S), so just bail if it's pressed
            # (saving is handled in the scene's update method directly)
            return

        resize_xy = inputs.get_instance().was_pressed_four_way(left=keybinds.get_instance().get_keys(const.SHRINK_SELECTION_HORZ),
                                                               right=keybinds.get_instance().get_keys(const.GROW_SELECTION_HORZ),
                                                               up=keybinds.get_instance().get_keys(const.SHRINK_SELECTION_VERT),
                                                               down=keybinds.get_instance().get_keys(const.GROW_SELECTION_VERT))
        move_xy = inputs.get_instance().was_pressed_four_way(left=keybinds.get_instance().get_keys(const.MOVE_SELECTION_LEFT),
                                                             right=keybinds.get_instance().get_keys(const.MOVE_SELECTION_RIGHT),
                                                             up=keybinds.get_instance().get_keys(const.MOVE_SELECTION_UP),
                                                             down=keybinds.get_instance().get_keys(const.MOVE_SELECTION_DOWN))

        if resize_xy != (0, 0):
            self.scene.resize_selection(resize_xy[0], resize_xy[1])
        elif move_xy != (0, 0):
            self.scene.move_selection(move_xy[0], move_xy[1])

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.COPY)):
            self.scene.copy_selection_to_clipboard()
        elif inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.CUT)):
            self.scene.cut_selection_to_clipboard()
        elif inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.PASTE)):
            self.scene.paste_clipboard_at_mouse()
        elif inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.DELETE)):
            self.scene.delete_selection()
        elif inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.ADVANCED_EDIT)):
            self.scene.handle_advanced_edit_pressed()
        elif inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.SELECT_ALL)):
            self.scene.select_all()

        cycle_type_steps = inputs.get_instance().was_pressed_four_way(
            right=keybinds.get_instance().get_keys(const.CYCLE_SELECTION_SUBTYPE_FORWARD),
            left=keybinds.get_instance().get_keys(const.CYCLE_SELECTION_SUBTYPE_BACKWARD))[0]
        if cycle_type_steps != 0:
            self.scene.cycle_selection_type(cycle_type_steps)

        cycle_color_steps = inputs.get_instance().was_pressed_four_way(
            right=keybinds.get_instance().get_keys(const.CYCLE_SELECTION_COLOR_FORWARD),
            left=keybinds.get_instance().get_keys(const.CYCLE_SELECTION_COLOR_BACKWARD))[0]
        if cycle_color_steps != 0:
            self.scene.cycle_selection_color(cycle_color_steps)

        cycle_art_steps = inputs.get_instance().was_pressed_four_way(
            right=keybinds.get_instance().get_keys(const.CYCLE_SELECTION_ART_FORWARD),
            left=keybinds.get_instance().get_keys(const.CYCLE_SELECTION_ART_BACKWARD))[0]
        if cycle_art_steps != 0:
            self.scene.cycle_selection_art(cycle_art_steps)

        toggle_inverted = inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.TOGGLE_SELECTION_INVERTED))
        if toggle_inverted:
            self.scene.toggle_selection_inverted()

        if mouse_xy is not None and edit_xy is not None:
            if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.CLEAR_POINTS)):
                self.scene.clear_points_from_selection()
            elif inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.REMOVE_POINT)):
                self.scene.remove_point_from_selection(mouse_xy[0], mouse_xy[1])
            elif inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.ADD_POINT)):
                self.scene.add_point_to_selection(edit_xy[0], edit_xy[1])

        spawn_idx = self._get_activated_spawn_idx()
        if spawn_idx is not None:
            obj_type = self.scene.get_pallette_object_type(spawn_idx)
            self.scene.set_spec_type_to_place(obj_type)


class ObjectPlacementMouseMode(MouseMode):

    def __init__(self, spec_type_to_place, scene: LevelEditGameScene):
        super().__init__(scene)
        self.spec_type = spec_type_to_place

    def activate(self):
        pass

    def deactivate(self):
        pass

    def handle_drag_events(self):
        pass

    def handle_click_at(self, world_xy, button=1):
        if button == 1:  # left click
            edit_xy = self.scene.snap_world_coords_to_edit_grid(world_xy)
            self.scene.spawn_object_at(self.spec_type, edit_xy)

            if not inputs.get_instance().shift_is_held():
                self.scene.set_mouse_mode(None)

    def handle_key_events(self):
        spawn_idx = self._get_activated_spawn_idx()
        if spawn_idx is not None:
            obj_type = self.scene.get_pallette_object_type(spawn_idx)
            if obj_type == self.spec_type:
                self.scene.set_spec_type_to_place(None)
            else:
                self.scene.set_spec_type_to_place(obj_type)


def build_object_pallette():
    return [
        blueprints.SpecTypes.BLOCK.get_default_blob(),                  # 1
        blueprints.SpecTypes.START_BLOCK.get_default_blob(),            # 2
        blueprints.SpecTypes.END_BLOCK.get_default_blob(),              # 3
        blueprints.SpecTypes.SLOPE_BLOCK_QUAD.get_default_blob(),       # 4
        blueprints.SpecTypes.MOVING_BLOCK.get_default_blob(),           # 5
        blueprints.SpecTypes.DOOR_BLOCK.get_default_blob(),             # 6
        blueprints.SpecTypes.KEY_BLOCK.get_default_blob(),              # 7
        blueprints.SpecTypes.SPIKES.get_default_blob(),                 # 8
        blueprints.SpecTypes.FALLING_BLOCK.get_default_blob(),          # 9
        blueprints.SpecTypes.TELEPORTER.get_default_blob(),             # 0

        blueprints.SpecTypes.INFO.get_default_blob(),                   # shift + 1
        blueprints.SpecTypes.FALSE_BLOCK.get_default_blob(),            # shift + 2
        blueprints.SpecTypes.CAMERA_BOUND_MARKER.get_default_blob(),    # shift + 3
        blueprints.SpecTypes.ZONE.get_default_blob(),                   # shift + 4
        blueprints.SpecTypes.DECORATION.get_default_blob()              # shift + 5
    ]


class Test3DScene(scenes.Scene):

    def __init__(self):
        super().__init__()
        self.ship_model = spriteref.ThreeDeeModels.SHIP
        self.ship_sprites = [None] * 30
        self.text_info_sprite = None
        self.sun_sprite = None

        self.cam_walk_speed = 0.75   # units per tick
        self.cam_turn_speed = 0.025  # radians per tick
        self.cam_turn_speed_slow = 0.005

        self.max_y_angle = 0.9 * math.pi / 2
        self.min_y_angle = -0.9 * math.pi / 2

        self.cam_pos = (0, 0, -65)
        self.cam_dir = (0, 0, 1)
        self.cam_fov = 24

        self.track_ship = False

    def handle_camera_move(self):
        import pygame
        cam_move = inputs.get_instance().is_held_four_way(left=pygame.K_a,
                                                          right=pygame.K_d,
                                                          up=pygame.K_w,
                                                          down=pygame.K_s)

        xz_dir = util.set_length((self.cam_dir[0], self.cam_dir[2]), 1)
        cam_x, cam_y, cam_z = self.cam_pos
        cam_x += cam_move[1] * xz_dir[0] * self.cam_walk_speed
        cam_z += cam_move[1] * xz_dir[1] * self.cam_walk_speed

        right_xz_dir = util.rotate(xz_dir, math.pi / 2)
        cam_x += cam_move[0] * right_xz_dir[0] * self.cam_walk_speed
        cam_z += cam_move[0] * right_xz_dir[1] * self.cam_walk_speed

        cam_move_y = inputs.get_instance().is_held_four_way(up=pygame.K_SPACE, down=pygame.K_c)[1]
        cam_y += cam_move_y * self.cam_walk_speed

        self.cam_pos = (cam_x, cam_y, cam_z)

    def handle_camera_rotate(self):
        import pygame
        cam_rotate = inputs.get_instance().is_held_four_way(left=pygame.K_LEFT,
                                                            right=pygame.K_RIGHT,
                                                            up=pygame.K_UP,
                                                            down=pygame.K_DOWN)
        new_cam_dir = self.cam_dir

        turn_speed = self.cam_turn_speed if not inputs.get_instance().shift_is_held() else self.cam_turn_speed_slow

        # rotate camera left or right
        if cam_rotate[0] != 0:
            mat = matutils.yrot_matrix(-turn_speed * cam_rotate[0])
            rotated_dir = mat.dot([new_cam_dir[0], new_cam_dir[1], new_cam_dir[2], 0])
            new_cam_dir = (float(rotated_dir[0]), float(rotated_dir[1]), float(rotated_dir[2]))

        # rotate camera up or down
        if cam_rotate[1] != 0:
            orig_xz = (new_cam_dir[0], new_cam_dir[2])
            xz_vs_y = (util.mag(orig_xz), new_cam_dir[1])
            xz_vs_y = util.rotate(xz_vs_y, cam_rotate[1] * turn_speed)

            # enforce max upward / downward angles
            if xz_vs_y[1] > 0 and util.angle_between((1, 0), xz_vs_y) > self.max_y_angle:
                xz_vs_y = (math.cos(self.max_y_angle), math.sin(self.max_y_angle))
            elif xz_vs_y[1] < 0 and -util.angle_between((1, 0), xz_vs_y) < self.min_y_angle:
                xz_vs_y = (math.cos(self.min_y_angle), math.sin(self.min_y_angle))

            new_xz_length = xz_vs_y[0]
            new_xz = util.set_length(orig_xz, new_xz_length)
            new_cam_dir = (new_xz[0], xz_vs_y[1], new_xz[1])

        if cam_rotate != (0, 0):
            self.track_ship = False
        elif inputs.get_instance().was_pressed(pygame.K_t):
            self.track_ship = not self.track_ship

        if self.track_ship:
            new_cam_dir = util.set_length(util.sub(self.ship_sprites[0].position(), self.cam_pos), 1)

        self.cam_dir = tuple(float(v) for v in new_cam_dir)  # new_cam_dir might be a numpy array at this point

        if inputs.get_instance().is_held(pygame.K_f):
            fov_change_speed = 1
            mult = -1 if inputs.get_instance().shift_is_held() else 1
            self.cam_fov = util.bound(self.cam_fov + mult * fov_change_speed, 10, 180)

    def update(self):
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_CANCEL)):
            self.jump_to_scene(MainMenuScene())
            return

        import src.engine.threedee as threedee
        for i in range(0, len(self.ship_sprites)):
            if self.ship_sprites[i] is None:
                self.ship_sprites[i] = threedee.BillboardSprite3D(self.ship_model, spriteref.THREEDEE_LAYER,
                                                                  position=(i * 30, 0, 0),
                                                                  vert_billboard=i % 2 == 0,
                                                                  horz_billboard=i % 3 == 0)
        if self.sun_sprite is None:
            self.sun_sprite = threedee.BillboardSprite3D(spriteref.ThreeDeeModels.SUN_FLAT, spriteref.THREEDEE_LAYER,
                                                         position=(0, 0, 10000), scale=(1000, 1000, 1000),
                                                         vert_billboard=True,
                                                         horz_billboard=True)

        import pygame

        mult = -1 if inputs.get_instance().shift_is_held() else 1

        for i in range(0, len(self.ship_sprites)):
            ship_sprite = self.ship_sprites[i]

            rot = list(ship_sprite.rotation())

            rot_speed = 0.03
            if inputs.get_instance().is_held(pygame.K_r):  # roll
                rot[2] += mult * rot_speed
            if inputs.get_instance().is_held(pygame.K_p):  # pitch
                rot[0] += mult * rot_speed
            if inputs.get_instance().is_held(pygame.K_o):  # 'o' stands for dOor which is the mnemonic for yaw
                rot[1] += mult * rot_speed

            scale = list(ship_sprite.scale())
            pos = list(ship_sprite.position())

            if inputs.get_instance().ctrl_is_held():
                scale_inc = mult * 0.05
                if inputs.get_instance().is_held(pygame.K_x):
                    scale[0] += scale_inc
                if inputs.get_instance().is_held(pygame.K_y):
                    scale[1] += scale_inc
                if inputs.get_instance().is_held(pygame.K_z):
                    scale[2] += scale_inc
            else:
                pos_inc = mult * 0.2
                if inputs.get_instance().is_held(pygame.K_x):
                    pos[0] += pos_inc
                if inputs.get_instance().is_held(pygame.K_y):
                    pos[1] += pos_inc
                if inputs.get_instance().is_held(pygame.K_z):
                    pos[2] += pos_inc

            self.ship_sprites[i] = ship_sprite.update(new_position=pos, new_rotation=rot, new_scale=scale)

        if self.text_info_sprite is None:
            self.text_info_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, "abc", scale=0.5, color=colors.LIGHT_GRAY,
                                                       font_lookup=spritesheets.get_default_font(mono=True, small=False))

        self.handle_camera_move()
        self.handle_camera_rotate()

        layer = renderengine.get_instance().get_layer(spriteref.THREEDEE_LAYER)
        layer.camera.set_position(self.cam_pos)
        layer.camera.set_direction(self.cam_dir)
        layer.camera.set_fov(self.cam_fov)

        pos = self.ship_sprites[0].position()
        rot = self.ship_sprites[0].get_effective_rotation(camera_pos=layer.camera.get_position())
        scale = self.ship_sprites[0].scale()
        cam_x, cam_y, cam_z = layer.camera.get_position()
        dir_x, dir_y, dir_z = layer.camera.get_direction()
        text = "camera.pos= ({:.2f}, {:.2f}, {:.2f})\n" \
               "camera.dir= ({:.2f}, {:.2f}, {:.2f})\n" \
               "camera.fov= {} \n\n" \
               "ship_pos=   ({:.2f}, {:.2f}, {:.2f})\n" \
               "ship_rot=   ({:.2f}, {:.2f}, {:.2f})\n" \
               "ship_scale= ({:.2f}, {:.2f}, {:.2f})\n" \
               "tracking=   {}".format(
            cam_x, cam_y, cam_z,
            dir_x, dir_y, dir_z,
            layer.camera.get_fov(),
            pos[0], pos[1], pos[2],
            rot[0], rot[1], rot[2],
            scale[0], scale[1], scale[2],
            self.track_ship
        )
        self.text_info_sprite.update(new_text=text)

        if inputs.get_instance().was_pressed(pygame.K_m):
            print("proj={}".format(layer.get_proj_matrix(renderengine.get_instance())))
            print("view={}".format(layer.get_view_matrix()))
            print("model={}".format(self.ship_sprites[0].get_xform()))

    def all_sprites(self):
        for spr in self.ship_sprites:
            yield spr
        yield self.sun_sprite
        yield self.text_info_sprite

