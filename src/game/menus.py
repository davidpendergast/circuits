import traceback
import random
import json
import os

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
        self._options_list.add_option("start", lambda: self.jump_to_scene(RealGameScene(blueprints.get_test_blueprint_4())))
        self._options_list.add_option("intro", lambda: self.jump_to_scene(IntroCutsceneScene()))
        self._options_list.add_option("load", lambda: self.jump_to_scene(overworld.OverworldScene("overworlds/test_overworld")))
        self._options_list.add_option("create", lambda: self.jump_to_scene(LevelSelectForEditScene("testing")))
        self._options_list.add_option("options", lambda: self.jump_to_scene(LevelEditGameScene(blueprints.get_test_blueprint_4())))
        self._options_list.add_option("exit", lambda: self.jump_to_scene(LevelEditGameScene(blueprints.get_test_blueprint_4())))

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

    OPTS_PER_PAGE = 8

    def __init__(self, title=None):
        scenes.Scene.__init__(self)
        self.title_text = title
        self.title_sprite = None
        self.title_scale = 2

        self.option_pages = ui.MultiPageOptionsList(opts_per_page=OptionSelectScene.OPTS_PER_PAGE)

    def add_option(self, text, do_action, is_enabled=lambda: True):
        self.option_pages.add_option(text, do_action, is_enabled=is_enabled)

    def update(self):
        if self.title_sprite is None:
            self.title_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, self.title_text, scale=self.title_scale)
        screen_size = renderengine.get_instance().get_game_size()
        title_x = screen_size[0] // 2 - self.title_sprite.size()[0] // 2
        title_y = max(16, screen_size[1] // 5 - self.title_sprite.size()[1] // 2)
        self.title_sprite.update(new_x=title_x, new_y=title_y)

        options_y = title_y + 32 + self.title_sprite.size()[1]
        options_x = screen_size[0] // 2 - self.option_pages.get_size()[0] // 2
        self.option_pages.set_xy((options_x, options_y))
        self.option_pages.update_self_and_kids()

    def all_sprites(self):
        if self.title_sprite is not None:
            for spr in self.title_sprite.all_sprites():
                yield spr
        for spr in self.option_pages.all_sprites_from_self_and_kids():
            yield spr


class LevelSelectForEditScene(OptionSelectScene):

    def __init__(self, dirpath):
        OptionSelectScene.__init__(self, "create level")
        self.all_levels = blueprints.load_all_levels_from_dir(dirpath)  # level_id -> LevelBlueprint

        sorted_ids = [k for k in self.all_levels]
        sorted_ids.sort()

        self.add_option("create new", lambda: self.jump_to_scene(LevelEditGameScene(blueprints.get_test_blueprint_4())))

        for level_id in sorted_ids:
            level_bp = self.all_levels[level_id]
            self.add_option(level_id, lambda: self.jump_to_scene(LevelEditGameScene(level_bp,
                                                                                    output_file=level_bp.loaded_from_file)))


class TextEditScene(scenes.Scene):

    def __init__(self, prompt_text, default_text="", on_cancel=None, on_accept=None):
        """
        :param on_exit: lambda () -> None
        :param on_accept: lambda (final_text) -> None
        """
        scenes.Scene.__init__(self)
        self.prompt_text = prompt_text
        self.prompt_element = ui.SpriteElement()

        self.text_box = ui.TextEditElement(default_text, scale=1, char_limit=32, outline_color=colors.LIGHT_GRAY)

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
                self.on_cancel()
                return

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_ACCEPT)):
            if self.on_accept is not None:
                self.on_accept(self.text_box.get_text())
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

    def get_world(self) -> worlds.World:
        return self._world

    def get_world_view(self) -> worldview.WorldView:
        return self._world_view

    def update(self):
        if self._world is not None:
            self._world.update()
        if self._world_view is not None:
            self._world_view.update()

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


class _GameState:

    def __init__(self, bp):
        self.bp = bp

        self._players_in_level = bp.get_player_types()
        n_players = len(self._players_in_level)

        self.currently_playing = [False] * n_players
        self._currently_satisfied = [False] * n_players
        self._recorded_runs = [None] * n_players  # list of PlaybackPlayerController

        self._total_ticks = bp.time_limit()
        self._time_elapsed = 0

        self._active_player_idx = 0

    def reset(self, all_players=False):
        self._time_elapsed = 0
        for i in range(0, len(self._currently_satisfied)):
            self._currently_satisfied[i] = False
        for i in range(0, len(self.currently_playing)):
            self.currently_playing[i] = False
        if all_players:
            self._active_player_idx = 0
            self._recorded_runs = [None] * self.num_players()

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
        return self.currently_playing[player_idx]

    def set_playing_back(self, player_idx, val):
        self.currently_playing[player_idx] = val

    def was_playing_back(self, player_idx):
        return player_idx < self.get_active_player_idx()

    def set_satisfied(self, player_idx, val):
        self._currently_satisfied[player_idx] = val

    def is_active_character_satisfied(self):
        return self._currently_satisfied[self._active_player_idx]

    def update(self, world):
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
                is_done = i != active_idx and not self._state.is_playing_back(i)
                frm = gs.get_instance().anim_tick()
                model = spriteref.ui_sheet().get_character_card_anim(is_first, is_last, frm, done=is_done)

                if self._state.is_satisfied(i):
                    color = colors.PERFECT_GREEN
                elif i == active_idx:
                    color = colors.WHITE
                elif self._state.is_playing_back(i):
                    color = colors.LIGHT_GRAY
                else:
                    color = colors.PERFECT_RED  # failed

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

    def __init__(self, bp):
        self._state = _GameState(bp)

        _BaseGameScene.__init__(self, bp=bp)

        self._top_panel_ui = None
        self._progress_bar_ui = None

        self.setup_new_world(bp)

    def update(self):
        super().update()
        self._state.update(self.get_world())

        hard_reset_keys = keybinds.get_instance().get_keys(const.RESET)
        soft_reset_keys = keybinds.get_instance().get_keys(const.SOFT_RESET)
        if inputs.get_instance().was_pressed(hard_reset_keys):
            self._state.reset(all_players=True)
            self.setup_new_world(self._state.bp)
        elif inputs.get_instance().was_pressed(soft_reset_keys):
            self._state.reset(all_players=False)
            self.setup_new_world(self._state.bp)

        elif self._state.all_satisfied():
            pass  # TODO complete level / show replay or something
        else:
            active_satisfied = True
            for i in range(0, self._state.get_active_player_idx() + 1):
                if not self._state.is_satisfied(i):
                    active_satisfied = False
                    break

            if active_satisfied:
                player_ent = self.get_world().get_player()
                recording = player_ent.get_controller().get_recording()
                self._state.active_player_succeeded(recording)
                self.setup_new_world(self._state.bp)

        self._update_ui()

    def handle_esc_pressed(self):
        self.get_manager().set_next_scene(MainMenuScene())

    def setup_new_world(self, bp):
        old_show_grid = False if self.get_world_view() is None else self.get_world_view()._show_grid
        super().setup_new_world(bp)

        # gotta place the players down
        world = self.get_world()
        self.get_world_view()._show_grid = old_show_grid

        import src.game.entities as entities

        for i in range(0, self._state.num_players()):
            player_type = self._state.get_player_type(i)

            if i == self._state.get_active_player_idx():
                controller = entities.RecordingPlayerController()
            else:
                controller = self._state.get_recording(i)

            if controller is not None:
                player_ent = entities.PlayerEntity(0, 0, player_type, controller)
                start_xy = world.get_player_start_position(player_ent)
                player_ent.set_xy(start_xy)
                world.add_entity(player_ent, next_update=False)

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
        RealGameScene.__init__(self, bp)

        self.edit_scene = edit_scene

    def update(self):
        super().update()

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.TOGGLE_EDIT_MODE)):
            self.handle_esc_pressed()

    def handle_esc_pressed(self):
        self.get_manager().set_next_scene(self.edit_scene)


class LevelEditGameScene(_BaseGameScene):

    def __init__(self, bp: blueprints.LevelBlueprint, output_file=None):
        """
        world_type: an int or level blueprint
        """
        _BaseGameScene.__init__(self)

        self.orig_bp = bp
        self.output_file = output_file if output_file is not None else "testing/saved_level.json"

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

    def undo(self):
        self.edit_queue_idx = util.bound(self.edit_queue_idx, 0, len(self.edit_queue))
        if self.edit_queue_idx > 0:
            self.edit_queue_idx -= 1
        else:
            return
        state_to_apply = self.edit_queue[self.edit_queue_idx]
        self._apply_state(state_to_apply)

    def redo(self):
        self.edit_queue_idx = util.bound(self.edit_queue_idx, 0, len(self.edit_queue))
        if self.edit_queue_idx < len(self.edit_queue) - 1:
            self.edit_queue_idx += 1
        else:
            return
        state_to_apply = self.edit_queue[self.edit_queue_idx]
        self._apply_state(state_to_apply)

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

    def delete_selection(self):
        orig, new = self._mutate_selected_specs(lambda s: [])
        print("INFO: deleted {} spec(s)".format(len(orig)))

    def move_selection(self, dx, dy):
        move_funct = lambda s: blueprints.SpecUtils.move(s, (dx * self.edit_resolution, dy * self.edit_resolution))
        self._mutate_selected_specs(move_funct)

    def resize_selection(self, dx, dy):
        resize_funct = lambda s: blueprints.SpecUtils.resize(s, (dx * self.edit_resolution, dy * self.edit_resolution))
        self._mutate_selected_specs(resize_funct)

    def cycle_selection_type(self, steps):
        cycle_funct = lambda s: blueprints.SpecUtils.cycle_subtype(s, steps)
        self._mutate_selected_specs(cycle_funct)

    def cycle_selection_color(self, steps):
        cycle_func = lambda s: blueprints.SpecUtils.cycle_color(s, steps)
        self._mutate_selected_specs(cycle_func)

    def cycle_selection_art(self, steps):
        cycle_func = lambda s: blueprints.SpecUtils.cycle_art(s, steps)
        self._mutate_selected_specs(cycle_func)

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

        save_result = blueprints.write_level_to_file(bp_to_save, file_to_use)
        if save_result:
            print("INFO: saved level to {}".format(file_to_use))
            self.output_file = file_to_use
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
            else:
                ent.set_color_override(None)

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
            manager = self.get_manager()

            def _do_accept(filename):
                # TODO validate the filename?
                self.output_file = filename
                self.save_to_disk(prompt_for_location=False)
                manager.set_next_scene(self)

            self.jump_to_scene(TextEditScene("enter filename:", default_text=default_text,
                                             on_cancel=lambda: manager.set_next_scene(self),
                                             on_accept=_do_accept))
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
        # TODO probably want to pop an "are you sure you want to exit" dialog
        pass

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
            else:
                if key in self.selected_specs:
                    self.selected_specs.remove(key)
                if key in self.entities_for_specs:
                    for ent in self.entities_for_specs[key]:
                        ent.set_color_override(None)

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
        res.append(blueprints.SpecTypes.BLOCK.get_default_blob())
        res.append(blueprints.SpecTypes.START_BLOCK.get_default_blob())
        res.append(blueprints.SpecTypes.END_BLOCK.get_default_blob())
        res.append(blueprints.SpecTypes.SLOPE_BLOCK_QUAD.get_default_blob())
        res.append(blueprints.SpecTypes.MOVING_BLOCK.get_default_blob())
        res.append(blueprints.SpecTypes.DOOR_BLOCK.get_default_blob())
        res.append(blueprints.SpecTypes.KEY_BLOCK.get_default_blob())

        return res

    def get_pallette_object(self, idx):
        if 0 <= idx < len(self.object_pallette):
            return dict(self.object_pallette[idx])
        else:
            return None

    def spawn_pallette_object_at_mouse(self, idx):
        spec_to_spawn = self.get_pallette_object(idx)
        if spec_to_spawn is not None and inputs.get_instance().mouse_in_window():
            screen_pos = inputs.get_instance().mouse_pos()
            mouse_pos_in_world = self._world_view.screen_pos_to_world_pos(screen_pos)
            spawn_x = mouse_pos_in_world[0] - (mouse_pos_in_world[0] % self.edit_resolution)
            spawn_y = mouse_pos_in_world[1] - (mouse_pos_in_world[1] % self.edit_resolution)

            spec_to_spawn = blueprints.SpecUtils.set_xy(spec_to_spawn, (spawn_x, spawn_y))

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
        resize_xy = inputs.get_instance().was_pressed_four_way(left=keybinds.get_instance().get_keys(const.SHRINK_SELECTION_HORZ),
                                                               right=keybinds.get_instance().get_keys(const.GROW_SELECTION_HORZ),
                                                               up=keybinds.get_instance().get_keys(const.SHRINK_SELECTION_VERT),
                                                               down=keybinds.get_instance().get_keys(const.GROW_SELECTION_VERT))
        move_xy = inputs.get_instance().was_pressed_four_way(left=keybinds.get_instance().get_keys(const.MOVE_SELECTION_LEFT),
                                                             right=keybinds.get_instance().get_keys(const.MOVE_SELECTION_RIGHT),
                                                             up=keybinds.get_instance().get_keys(const.MOVE_SELECTION_UP),
                                                             down=keybinds.get_instance().get_keys(const.MOVE_SELECTION_DOWN))

        # TODO this assumes that resize is the one with modifier keys
        # TODO (how should we manage keybinds that are subsets of other keybinds?)
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

        for i in range(0, len(const.OPTIONS)):
            if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.OPTIONS[i])):
                spawn_idx = i
                # 79 different choices!~
                if inputs.get_instance().shift_is_held():
                    spawn_idx += 10
                if inputs.get_instance().ctrl_is_held():
                    spawn_idx += 20
                if inputs.get_instance().alt_is_held():
                    spawn_idx += 40
                print("INFO: spawning object [{}] at mouse: {}".format(spawn_idx,
                                                                       self.scene.get_pallette_object(spawn_idx)))
                self.scene.spawn_pallette_object_at_mouse(spawn_idx)
