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


class MainMenuScene(scenes.Scene):

    def __init__(self):
        scenes.Scene.__init__(self)
        self._title_element = ui.SpriteElement()

        self._options_list = ui.OptionsList()
        self._options_list.add_option("start", lambda: self.jump_to_scene(overworld.OverworldScene("overworlds/test_overworld")))
        self._options_list.add_option("intro", lambda: self.jump_to_scene(IntroCutsceneScene()))
        # self._options_list.add_option("load", lambda: self.jump_to_scene(overworld.OverworldScene("overworlds/test_overworld")))
        self._options_list.add_option("create", lambda: self.jump_to_scene(LevelSelectForEditScene(configs.level_edit_dir)))
        self._options_list.add_option("options", lambda: self.jump_to_scene(Test3DScene()))
        self._options_list.add_option("exit", lambda: self.jump_to_scene(LevelEditGameScene(blueprints.get_test_blueprint_4())), esc_option=True)
        self._options_list.update_sprites()

    def update(self):
        self.update_sprites()

        self._title_element.update_self_and_kids()
        self._options_list.update_self_and_kids()

    def update_sprites(self):
        total_size = renderengine.get_instance().get_game_size()

        if self._title_element.get_sprite() is None:
            text_sprite = sprites.ImageSprite(spriteref.ui_sheet().title_img, 0, 0, spriteref.UI_FG_LAYER, scale=2)
            self._title_element.set_sprite(text_sprite)

        title_x = total_size[0] // 2 - self._title_element.get_size()[0] // 2
        title_y = total_size[1] // 3 - self._title_element.get_size()[1] // 2
        self._title_element.set_xy((title_x, title_y))

        options_xy = (total_size[0] // 3 - self._options_list.get_size()[0] // 2,
                      title_y + self._title_element.get_size()[1] - 40)
        self._options_list.set_xy(options_xy)

    def all_sprites(self):
        for spr in self._title_element.all_sprites_from_self_and_kids():
            yield spr
        for spr in self._options_list.all_sprites_from_self_and_kids():
            yield spr


class OptionSelectScene(scenes.Scene):

    OPTS_PER_PAGE = 6

    def __init__(self, title=None, description=None):
        scenes.Scene.__init__(self)
        self.title_text = title
        self.title_sprite = None
        self.title_scale = 2

        self.desc_text = description
        self.desc_sprite = None
        self.desc_scale = 1
        self.desc_horz_inset = 32

        self.vert_spacing = 32

        self.option_pages = ui.MultiPageOptionsList(opts_per_page=OptionSelectScene.OPTS_PER_PAGE)

        self._esc_option = None

    def add_option(self, text, do_action, is_enabled=lambda: True, esc_option=False):
        self.option_pages.add_option(text, do_action, is_enabled=is_enabled, esc_option=esc_option)

    def update(self):
        if self.title_sprite is None:
            self.title_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, self.title_text, scale=self.title_scale)
        screen_size = renderengine.get_instance().get_game_size()
        title_x = screen_size[0] // 2 - self.title_sprite.size()[0] // 2
        title_y = max(16, screen_size[1] // 5 - self.title_sprite.size()[1] // 2)
        self.title_sprite.update(new_x=title_x, new_y=title_y)
        y_pos = title_y + self.title_sprite.size()[1] + self.vert_spacing

        if self.desc_text is None:
            self.desc_sprite = None
        else:
            if self.desc_sprite is None:
                self.desc_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, "abc", scale=self.desc_scale)
            wrapped_desc = sprites.TextSprite.wrap_text_to_fit(self.desc_text, screen_size[0] - self.desc_horz_inset * 2,
                                                               scale=self.desc_scale)
            self.desc_sprite.update(new_text="\n".join(wrapped_desc))
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


class LevelSelectForEditScene(OptionSelectScene):

    def __init__(self, dirpath):
        OptionSelectScene.__init__(self, "create level")
        self.all_levels = blueprints.load_all_levels_from_dir(dirpath)  # level_id -> LevelBlueprint

        sorted_ids = [k for k in self.all_levels]
        sorted_ids.sort()

        self.add_option("create new", lambda: self.jump_to_scene(LevelEditGameScene(blueprints.get_template_blueprint())))

        for level_id in sorted_ids:
            level_bp = self.all_levels[level_id]

            def _action(bp=level_bp):  # lambdas in loops, yikes
                self.jump_to_scene(LevelEditGameScene(bp, output_file=bp.loaded_from_file))

            self.add_option(level_id, _action)

    def update(self):
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_CANCEL)):
            self.jump_to_scene(MainMenuScene())
        else:
            super().update()


class LevelEditorPauseMenu(OptionSelectScene):

    def __init__(self, level_bp, on_cancel, on_quit, description=None, output_file=None):
        """
        :param level_bp: current LevelBlueprint
        :param on_cancel: manager, LevelBlueprint -> None
        :param on_quit: () -> None
        """
        super().__init__(title="editing {}".format(level_bp.name()), description=description)
        self.add_option("resume", lambda: on_cancel(level_bp), esc_option=True)
        self.add_option("edit metadata", lambda: self.jump_to_scene(
            LevelMetaDataEditScene(level_bp, lambda new_bp: self.jump_to_scene(LevelEditGameScene(new_bp,
                                   output_file=output_file if new_bp.level_id() == level_bp.level_id() else None)))))
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
                return

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_ACCEPT)):
            if self.on_accept is not None:
                self.on_accept(self.get_manager(), self.text_box.get_text())
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

    def handle_inputs(self):
        if self.tick_count > 5 and inputs.get_instance().was_anything_pressed():
            self.jump_to_scene(self.get_next_scene())

    def update_sprites(self):
        bg_img = self.get_bg_image()
        if bg_img is None:
            self._bg_sprite = None
        else:
            if self._bg_sprite is None:
                self._bg_sprite = sprites.ImageSprite(bg_img, 0, 0, spriteref.UI_BG_LAYER)

            game_size = renderengine.get_instance().get_game_size()
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
                self._text_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, cur_text)
            if self._text_bg_sprite is None:
                self._text_bg_sprite = sprites.ImageSprite(spriteref.UI_BG_LAYER, 0, 0, spriteref.UI_BG_LAYER)

            # TODO text

    def all_sprites(self):
        yield self._bg_sprite
        yield self._text_bg_sprite
        if self._text_sprite is not None:
            for spr in self._text_sprite:
                yield spr


class IntroCutsceneScene(CutsceneScene):

    _PAGES = [
        (spriteref.CutsceneTypes.SUN, "The sun."),
        (spriteref.CutsceneTypes.SUN_CLOSEUP, "Close up."),
        (spriteref.CutsceneTypes.SHIP, "Ship."),
        (spriteref.CutsceneTypes.DIG, "Resources."),
        (spriteref.CutsceneTypes.BARREN, "Exhausted"),
        (spriteref.CutsceneTypes.TRANSPORT, "Transport"),
        (spriteref.CutsceneTypes.SPLIT, "Done")
    ]

    def __init__(self, page=0, next_scene_provider=None):
        CutsceneScene.__init__(self)
        if page < 0 or page >= len(IntroCutsceneScene._PAGES):
            raise ValueError("page out of bounds: {}".format(page))
        self.page = page
        self.next_scene_provider = next_scene_provider

    def get_text(self) -> sprites.TextBuilder:
        text = IntroCutsceneScene._PAGES[self.page][1]
        if text is None:
            return None
        else:
            res = sprites.TextBuilder()
            res.add(text, color=colors.WHITE)

    def get_bg_image(self) -> sprites.ImageModel:
        img_type = IntroCutsceneScene._PAGES[self.page][0]
        if img_type is not None:
            return spriteref.cutscene_image(img_type)
        else:
            return None

    def get_next_scene(self) -> scenes.Scene:
        if self.page < len(IntroCutsceneScene._PAGES) - 1:
            return IntroCutsceneScene(self.page + 1, next_scene_provider=self.next_scene_provider)
        elif self.next_scene_provider is not None:
            return self.next_scene_provider()
        else:
            return MainMenuScene()


class _BaseGameScene(scenes.Scene):

    def __init__(self, bp=None):
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
        if self._world is not None:
            self._world.update()
        if self._world_view is not None:
            self._world_view.update()

    def update(self):
        self.update_world_and_view()

        if inputs.get_instance().mouse_in_window():
            screen_pos = inputs.get_instance().mouse_pos()
            pos_in_world = self._world_view.screen_pos_to_world_pos(screen_pos)
            if inputs.get_instance().mouse_was_pressed(button=1):
                self.handle_click_at(pos_in_world, button=1)
            if inputs.get_instance().mouse_was_pressed(button=2):
                self.handle_click_at(pos_in_world, button=2)
            if inputs.get_instance().mouse_was_pressed(button=3):
                self.handle_click_at(pos_in_world, button=3)

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_CANCEL)):
            self.handle_esc_pressed()

    def handle_esc_pressed(self):
        pass

    def handle_click_at(self, world_xy, button=1):
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


class _GameState:

    def __init__(self, bp, status=Statuses.WAITING):
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

    def status_changed_this_frame(self):
        return self._status_elapsed_time <= 1

    def reset(self, all_players=False):
        self._time_elapsed = 0
        for i in range(0, len(self._currently_satisfied)):
            self._currently_satisfied[i] = False
        for i in range(0, len(self._currently_playing)):
            self._currently_playing[i] = False
        if all_players:
            self._active_player_idx = 0
            self._recorded_runs = [None] * self.num_players()
        self.set_status(Statuses.WAITING)

    def active_player_succeeded(self, recording):
        self._recorded_runs[self._active_player_idx] = recording

        self.reset()
        self._active_player_idx += 1

    def has_recording(self, player_idx):
        return self._recorded_runs[player_idx] is not None

    def get_recording(self, player_idx):
        return self._recorded_runs[player_idx]

    def get_player_type(self, player_idx):
        return self._players_in_level[player_idx]

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
        return self._currently_satisfied[player_idx]

    def all_satisfied(self):
        for idx in range(0, self.num_players()):
            if not self.is_satisfied(idx):
                return False
        return True

    def is_playing_back(self, player_idx):
        return self._currently_playing[player_idx]

    def set_playing_back(self, player_idx, val):
        self._currently_playing[player_idx] = val

    def is_alive(self, player_idx):
        return self._currently_alive[player_idx]

    def is_dead(self, player_idx):
        return player_idx <= self._active_player_idx and not self.is_alive(player_idx)

    def set_alive(self, player_idx, val):
        self._currently_alive[player_idx] = val

    def was_playing_back(self, player_idx):
        return player_idx < self.get_active_player_idx()

    def set_satisfied(self, player_idx, val):
        self._currently_satisfied[player_idx] = val

    def is_active_character_satisfied(self):
        return self._currently_satisfied[self._active_player_idx]

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

        end_blocks = [eb for eb in world.all_entities(cond=lambda ent: ent.is_end_block())]
        for idx in range(0, self.num_players()):
            player_type = self.get_player_type(idx)
            for eb in end_blocks:
                if eb.get_player_type() == player_type:
                    self.set_satisfied(idx, eb.is_satisfied())

            player = world.get_player(must_be_active=False, with_type=player_type)
            if player is not None and not player.is_active() and not player.get_controller().is_finished(world.get_tick()):
                self.set_playing_back(idx, True)
            else:
                self.set_playing_back(idx, False)

            self.set_alive(idx, player is not None)


class TopPanelUi(ui.UiElement):

    def __init__(self, state: _GameState):
        ui.UiElement.__init__(self)
        self._state = state
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
            self.bg_sprite = sprites.ImageSprite.new_sprite(spriteref.UI_BG_LAYER)
        self.bg_sprite = self.bg_sprite.update(new_model=spriteref.ui_sheet().top_panel_bg,
                                               new_x=rect[0], new_y=rect[1], new_color=colors.DARK_GRAY)

        player_types = [self._state.get_player_type(i) for i in range(0, self._state.num_players())]
        active_idx = self._state.get_active_player_idx()

        util.extend_or_empty_list_to_length(self.character_panel_sprites, len(player_types),
                                            creator=lambda: sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER))
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
                    self.character_panel_animation_sprites[i] = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER)

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
                                                                            new_depth=10)
                self.character_panel_animation_sprites[i] = anim_spr
            else:
                self.character_panel_animation_sprites[i] = None

        clock_text = self.get_clock_text()
        if self.clock_text_sprite is None:
            self.clock_text_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, clock_text,
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

    def __init__(self, state):
        ui.UiElement.__init__(self)
        self._state = state
        self.bg_sprite = None
        self.bar_sprite = None

    def update(self):
        rect = self.get_rect(absolute=True)
        if self.bg_sprite is None:
            self.bg_sprite = sprites.ImageSprite.new_sprite(spriteref.UI_BG_LAYER)
        self.bg_sprite = self.bg_sprite.update(new_model=spriteref.ui_sheet().top_panel_progress_bar_bg,
                                               new_x=rect[0], new_y=rect[1], new_color=colors.DARK_GRAY)
        if self.bar_sprite is None:
            self.bar_sprite = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER)
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


class RealGameScene(_BaseGameScene):

    def __init__(self, bp, on_level_completion, on_level_exit):
        """
        :param bp: LevelBlueprint
        :param on_level_completion: (time) -> None
        :param on_level_exit: () -> None
        """
        self._state = _GameState(bp)

        _BaseGameScene.__init__(self, bp=bp)

        self._on_level_completion = on_level_completion
        self._on_level_exit = on_level_exit

        self._top_panel_ui = None
        self._progress_bar_ui = None

        self._fadeout_duration = 90

        self.setup_new_world(bp)

        self._queued_next_world = None
        self._next_world_countdown = 0

    def update_world_and_view(self):
        if self._world is not None:
            self._world.update()
        if self._world_view is not None:
            self._world_view.update()

    def on_level_complete(self, time):
        if self._on_level_completion is not None:
            self._on_level_completion(time)

    def on_level_exit(self):
        if self._on_level_exit is not None:
            self._on_level_exit()

    def update(self):
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

        super().update()

        self._state.update(self.get_world())

        hard_reset_keys = keybinds.get_instance().get_keys(const.RESET)
        soft_reset_keys = keybinds.get_instance().get_keys(const.SOFT_RESET)

        if inputs.get_instance().was_pressed(hard_reset_keys) and self._state.get_status().can_hard_reset:
            self._state.reset(all_players=True)
            self.setup_new_world(self._state.bp)
        elif inputs.get_instance().was_pressed(soft_reset_keys) and self._state.get_status().can_soft_reset:
            self._state.reset(all_players=False)
            self.setup_new_world(self._state.bp)

        elif self._state.all_satisfied():
            self._state.set_status(Statuses.TOTAL_SUCCESS)
            self.replace_players_with_fadeout(delay=self._fadeout_duration)
            self._state.set_status(Statuses.EXIT_NOW_SUCCESSFULLY, delay=self._fadeout_duration)
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

        self._update_ui()

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
            anim = entities.PlayerFadeAnimation(0, 0, True, player_type, delay, False)

            # it thinks its a player because it has a get_player_type function~
            xy = self.get_world().get_player_start_position(anim)
            anim.set_xy(xy)
            self.get_world().add_entity(anim)

    def handle_esc_pressed(self):
        self.on_level_exit()

    def setup_new_world_with_delay(self, bp, delay, new_state, runnable=lambda: None):
        self._queued_next_world = (bp, new_state, runnable)
        self._next_world_countdown = delay

    def setup_new_world(self, bp):
        old_show_grid = False if self.get_world_view() is None else self.get_world_view()._show_grid
        super().setup_new_world(bp)

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
                player_ent = entities.PlayerEntity(0, 0, player_type, controller)
                start_xy = world.get_player_start_position(player_ent)
                player_ent.set_xy(start_xy)
                world.add_entity(player_ent, next_update=False)

                if is_active:
                    world.add_entity(entities.PlayerIndicatorEntity(player_ent), next_update=False)
                    world.add_entity(entities.EndBlockIndicatorEntity(player_ent), next_update=False)

        world.update()
        self.get_world_view().update()

    def _update_ui(self):
        y = 4
        if self._top_panel_ui is None:
            self._top_panel_ui = TopPanelUi(self._state)
        top_panel_size = self._top_panel_ui.get_size()
        display_size = renderengine.get_instance().get_game_size()
        self._top_panel_ui.set_xy((display_size[0] // 2 - top_panel_size[0] // 2, y))
        self._top_panel_ui.update()
        y += top_panel_size[1]

        if self._progress_bar_ui is None:
            self._progress_bar_ui = ProgressBarUi(self._state)
        prog_bar_size = self._progress_bar_ui.get_size()
        self._progress_bar_ui.set_xy((display_size[0] // 2 - prog_bar_size[0] // 2, y))
        self._progress_bar_ui.update()

    def all_sprites(self):
        for spr in super().all_sprites():
            yield spr
        if self._top_panel_ui is not None:
            for spr in self._top_panel_ui.all_sprites():
                yield spr
        if self._progress_bar_ui is not None:
            for spr in self._progress_bar_ui.all_sprites():
                yield spr


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


class LevelMetaDataEditScene(OptionSelectScene):

    def __init__(self, bp: blueprints.LevelBlueprint, on_exit):
        """
        :param bp:
        :param on_exit: LevelBlueprint -> None
        """
        OptionSelectScene.__init__(self, title="Edit Metadata")
        self._base_bp = bp
        self._on_exit = on_exit

        self._add_text_edit_option("level name: ", blueprints.NAME, bp)
        self._add_text_edit_option("description: ", blueprints.DESCRIPTION, bp)
        self._add_text_edit_option("level ID: ", blueprints.LEVEL_ID, bp)
        self._add_players_edit_option("Players: ", bp)

        self.add_option("back", lambda: self._on_exit(self._base_bp), esc_option=True)

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
        self.add_option(name + current_val, _action)

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


class LevelEditGameScene(_BaseGameScene):

    def __init__(self, bp: blueprints.LevelBlueprint, output_file=None):
        """
        world_type: an int or level blueprint
        """
        _BaseGameScene.__init__(self)

        self.orig_bp = bp
        self.output_file = output_file

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

        self._dirty = False  # whether the current state is different from the last-saved state

        self.stamp_current_state()
        self.setup_new_world(bp)

        self.object_pallette = self._load_object_pallette()

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
        if mode is None:
            self.mouse_mode = NormalMouseMode(self)
        else:
            self.mouse_mode = mode

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
                                               self.orig_bp.level_id(),
                                               self.orig_bp.get_player_types(),
                                               self.orig_bp.time_limit(),
                                               self.orig_bp.description(),
                                               self.all_spec_blobs)

    def get_specs_at(self, world_xy):
        res = []
        for spec in self.all_spec_blobs:
            r = blueprints.SpecUtils.get_rect(spec, default_size=gs.get_instance().cell_size)
            if r is None:
                continue
            elif util.rect_contains(r, world_xy):
                res.append(spec)
        return res

    def save_to_disk(self, prompt_for_location=False):
        bp_to_save = self.build_current_bp()
        file_to_use = self.output_file

        if prompt_for_location or self.output_file is None:
            file_to_use = util.prompt_for_file("enter file name for save", root="testing/", ext=".json")
            if file_to_use is None:
                return
            if os.path.isfile(file_to_use):
                ans = util.prompt_question("overwrite {}?".format(file_to_use), accepted_answers=("y", "n"))
                if ans == "y":
                    self.output_file = file_to_use
                else:
                    print("INFO: save canceled")
                    return
            else:
                self.output_file = file_to_use

        # TODO add a real way to set this from the editor...
        # TODO and make sure it avoids name collisions because otherwise levels won't load properly
        # (they're hashed by level_id all over the place)
        if bp_to_save.level_id() == "???":
            bp_to_save = bp_to_save.copy_with(level_id=str(file_to_use))

        save_result = blueprints.write_level_to_file(bp_to_save, file_to_use)
        if save_result:
            print("INFO: saved level to {}".format(file_to_use))
            self.output_file = file_to_use
            self._dirty = False
        else:
            print("INFO: failed to save level to {}".format(file_to_use))
            self.output_file = None

    def setup_new_world(self, bp, reset_camera=False):
        camera_pos = None
        camera_zoom = None

        if self.get_world_view() is not None and not reset_camera:
            camera_pos = self.get_world_view().get_camera_pos_in_world()
            camera_zoom = self.get_world_view().get_zoom()

        super().setup_new_world(bp)
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
            default_text = "" if self.output_file is None else self.output_file

            def _do_accept(manager, filename):
                # TODO validate the filename?
                self.output_file = filename
                self.save_to_disk(prompt_for_location=False)
                manager.set_next_scene(self)

            self.jump_to_scene(TextEditScene("enter filename:", default_text=default_text,
                                             on_cancel=lambda mgr: mgr.set_next_scene(self),
                                             on_accept=_do_accept,
                                             allowed_chars=ui.TextEditElement.FILEPATH_CHARS))
            return
            # self.save_to_disk(prompt_for_location=True)
        elif inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.SAVE)):
            self.save_to_disk(prompt_for_location=False)

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
            dx = 2 * gs.get_instance().cell_size // zoom * camera_move_x
            dy = 2 * gs.get_instance().cell_size // zoom * camera_move_y
            self.get_world_view().move_camera_in_world((dx, dy))

        super().update()

    def handle_esc_pressed(self):
        if self.is_dirty():
            desc = "you have unsaved changes."
        else:
            desc = None

        # TODO would be really pro to jump back to the level select screen with this level highlighted
        manager = self.get_manager()
        current_bp = self.build_current_bp()
        current_output_file = self.output_file
        def _handle_new_bp(new_bp):
            if new_bp != current_bp:
                manager.set_next_scene(LevelEditGameScene(new_bp,
                                                          current_output_file if new_bp.level_id() == current_bp.level_id() else None))
            else:
                manager.set_next_scene(self)
        self.jump_to_scene(LevelEditorPauseMenu(current_bp,
                                                _handle_new_bp,
                                                lambda: manager.set_next_scene(LevelSelectForEditScene("testing")),
                                                description=desc,
                                                output_file=self.output_file))

    def adjust_edit_resolution(self, increase):
        if self.edit_resolution in self.resolution_options:
            cur_idx = self.resolution_options.index(self.edit_resolution)
            new_idx = util.bound(cur_idx + (1 if increase else -1), 0, len(self.resolution_options) - 1)
            self.edit_resolution = self.resolution_options[new_idx]
        else:
            self.edit_resolution = self.resolution_options[-1]
        print("INFO: new editor resolution: {}".format(self.edit_resolution))

    def handle_click_at(self, world_xy, button=1):
        super().handle_click_at(world_xy, button=button)
        self.mouse_mode.handle_click_at(world_xy, button=button)

    def is_selected(self, spec):
        return util.to_key(spec) in self.selected_specs

    def deselect_all(self):
        all_selects = [s for s in self.selected_specs]
        for s in all_selects:
            self.set_selected(s, select=False)

    def _get_selected_entity_color(self, ent):
        color_id = ent.get_color_id()
        if color_id is not None:
            return spriteref.get_color(color_id, dark=True)
        else:
            return artutils.darker(ent.get_color(ignore_override=True), pcnt=0.30)

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

    def _load_object_pallette(self):
        res = []
        res.append(blueprints.SpecTypes.BLOCK.get_default_blob())               # 1
        res.append(blueprints.SpecTypes.START_BLOCK.get_default_blob())         # 2
        res.append(blueprints.SpecTypes.END_BLOCK.get_default_blob())           # 3
        res.append(blueprints.SpecTypes.SLOPE_BLOCK_QUAD.get_default_blob())    # 4
        res.append(blueprints.SpecTypes.MOVING_BLOCK.get_default_blob())        # 5
        res.append(blueprints.SpecTypes.DOOR_BLOCK.get_default_blob())          # 6
        res.append(blueprints.SpecTypes.KEY_BLOCK.get_default_blob())           # 7
        res.append(blueprints.SpecTypes.SPIKES.get_default_blob())              # 8

        return res

    def get_pallette_object(self, idx):
        if 0 <= idx < len(self.object_pallette):
            return dict(self.object_pallette[idx])
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
                snapped_x = mouse_pos_in_world[0] - (mouse_pos_in_world[0] % self.edit_resolution)
                snapped_y = mouse_pos_in_world[1] - (mouse_pos_in_world[1] % self.edit_resolution)
                return (snapped_x, snapped_y)

    def spawn_pallette_object_at(self, idx, xy):
        spec_to_spawn = self.get_pallette_object(idx)
        if spec_to_spawn is not None and xy is not None:
            spec_to_spawn = blueprints.SpecUtils.set_xy(spec_to_spawn, xy)

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
                print("INFO: spawning object [{}] at mouse: {}".format(spawn_idx,
                                                                       self.scene.get_pallette_object(spawn_idx)))
                self.scene.spawn_pallette_object_at(spawn_idx, edit_xy)


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
        layer.camera_position = self.cam_pos
        layer.camera_direction = self.cam_dir
        layer.camera_fov = self.cam_fov

        pos = self.ship_sprites[0].position()
        rot = self.ship_sprites[0].get_effective_rotation(camera_pos=layer.camera_position)
        scale = self.ship_sprites[0].scale()
        cam_x, cam_y, cam_z = layer.camera_position
        dir_x, dir_y, dir_z = layer.camera_direction
        text = "camera_pos= ({:.2f}, {:.2f}, {:.2f})\n" \
               "camera_dir= ({:.2f}, {:.2f}, {:.2f})\n" \
               "camera_fov= {} \n\n" \
               "ship_pos=   ({:.2f}, {:.2f}, {:.2f})\n" \
               "ship_rot=   ({:.2f}, {:.2f}, {:.2f})\n" \
               "ship_scale= ({:.2f}, {:.2f}, {:.2f})\n" \
               "tracking=   {}".format(
            cam_x, cam_y, cam_z,
            dir_x, dir_y, dir_z,
            layer.camera_fov,
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

