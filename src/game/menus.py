import traceback

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
import src.game.spriteref as spriteref
import src.game.colors as colors
import src.game.overworld as overworld
import src.game.ui as ui
import src.engine.spritesheets as spritesheets


class MainMenuScene(scenes.Scene):

    def __init__(self):
        scenes.Scene.__init__(self)
        self._title_element = ui.SpriteElement()

        self._options_list = ui.OptionsList()
        self._options_list.add_option("start", lambda: self.get_manager().set_next_scene(RealGameScene(blueprints.get_test_blueprint_3())))
        self._options_list.add_option("intro", lambda: self.get_manager().set_next_scene(IntroCutsceneScene()))
        self._options_list.add_option("load", lambda: self.get_manager().set_next_scene(overworld.OverworldScene("overworlds/test_overworld")))
        self._options_list.add_option("options", lambda: self.get_manager().set_next_scene(DebugGameScene()))
        self._options_list.add_option("exit", lambda: self.get_manager().set_next_scene(DebugGameScene()))

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
            self.get_manager().set_next_scene(self.get_next_scene())

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

        self.setup_new_world(bp)

    def setup_new_world(self, bp):
        if bp is None:
            self._world = None
            self._world_view = None
        else:
            print("INFO: activating blueprint: {}".format(bp.name()))
            self._world = bp.create_world()
            self._world_view = worldview.WorldView(self._world)

    def get_world(self):
        return self._world

    def update(self):
        if self._world is not None:
            self._world.update()
        if self._world_view is not None:
            self._world_view.update()

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
        self._currently_satisfied = [False] * len(self._players_in_level)

        self._total_ticks = bp.time_limit()
        self._time_elapsed = 0

        self._active_player_idx = 0

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

    def set_satisfied(self, player_idx, val):
        self._currently_satisfied[player_idx] = val

    def do_level_completed(self):
        pass

    def update(self, world):
        self._time_elapsed += 1

        end_blocks = [eb for eb in world.all_entities(cond=lambda ent: ent.is_end_block())]

        became_satisfied = []

        for idx in range(0, self.num_players()):
            player_type = self.get_player_type(idx)
            for eb in end_blocks:
                if eb.get_player_type() == player_type and eb.is_satisfied():
                    if not self.is_satisfied(idx):
                        self.set_satisfied(idx, True)
                        became_satisfied.append(player_type)

        if len(became_satisfied) > 0:
            if self.all_satisfied():
                self.do_level_completed()
            else:
                active_type = self.get_active_player_type()
                if active_type in became_satisfied:
                    player = world.get_player()

                    start_xy = world.get_player_start_position(player)
                    world.teleport_entity_to(player, start_xy, 30, new_entity=None)


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
        util.extend_or_empty_list_to_length(self.character_panel_sprites, len(player_types),
                                            creator=lambda: sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER))
        util.extend_or_empty_list_to_length(self.character_panel_animation_sprites, len(player_types),
                                            creator=lambda: None)
        for i in range(0, len(player_types)):
            model = spriteref.ui_sheet().get_character_card_sprite(player_types[i], i == 0)
            is_active = i == self._state.get_active_player_idx()
            color = const.get_player_color(player_types[i], dark=not is_active)
            card_x = rect[0] - 7 + 40 * i
            card_y = rect[1]
            self.character_panel_sprites[i] = self.character_panel_sprites[i].update(new_x=card_x,
                                                                                     new_y=card_y,
                                                                                     new_model=model,
                                                                                     new_color=color)
            if self._state.is_satisfied(i):
                if self.character_panel_animation_sprites[i] is None:
                    self.character_panel_animation_sprites[i] = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER)
                is_first = i == 0
                is_last = i == len(player_types) - 1  # TODO not correct
                model = spriteref.ui_sheet().get_character_card_anim(is_first, is_last,
                                                                     gs.get_instance().anim_tick())
                self.character_panel_animation_sprites[i] = self.character_panel_animation_sprites[i].update(new_x=card_x,
                                                                                                             new_y=card_y,
                                                                                                             new_model=model,
                                                                                                             new_color=colors.WHITE,
                                                                                                             new_depth=10)
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
        _BaseGameScene.__init__(self, bp=bp)
        self._state = _GameState(bp)

        self._top_panel_ui = None
        self._progress_bar_ui = None

    def update(self):
        super().update()
        self._state.update(self.get_world())

        self._update_ui()

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


class DebugGameScene(_BaseGameScene):
    # TODO this will become the level editor I think

    def __init__(self, world_type=0):
        """
        world_type: an int or level blueprint
        """
        _BaseGameScene.__init__(self)

        self._cur_test_world = world_type
        self._create_new_world(world_type=world_type)

    def update(self):
        if inputs.get_instance().mouse_was_pressed() and inputs.get_instance().mouse_in_window():  # debug
            screen_pos = inputs.get_instance().mouse_pos()
            pos_in_world = self._world_view.screen_pos_to_world_pos(screen_pos)

            cell_size = gs.get_instance().cell_size
            print("INFO: mouse pressed at ({}, {})".format(int(pos_in_world[0]) // cell_size,
                                                           int(pos_in_world[1]) // cell_size))

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.RESET)):
            self._create_new_world(world_type=self._cur_test_world)

        if configs.is_dev and inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.NEXT_LEVEL_DEBUG)):
            # TODO clean this up please...
            if isinstance(self._cur_test_world, int):
                self._cur_test_world += 1
                self._create_new_world(world_type=self._cur_test_world)

        if configs.is_dev and inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.SAVE_LEVEL_DEBUG)):
            if self._world is not None:
                bp = self._world.get_blueprint()
                if bp is not None:
                    filepath = "testing/saved_level.json"
                    print("INFO: saving level to {}".format(filepath))
                    blueprints.write_level_to_file(bp, filepath)

        if configs.is_dev and inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_CANCEL)):
            # TODO probably want to disable this once we start editing levels
            self.get_manager().set_next_scene(MainMenuScene())

        if configs.is_dev and inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.TOGGLE_SPRITE_MODE_DEBUG)):
            debug.toggle_debug_sprite_mode()

        if inputs.get_instance().mouse_is_dragging(button=1):
            drag_this_frame = inputs.get_instance().mouse_drag_this_frame(button=1)
            if drag_this_frame is not None:
                dxy = util.sub(drag_this_frame[1], drag_this_frame[0])
                dxy = util.mult(dxy, -1 / self._world_view.get_zoom())
                self._world_view.move_camera_in_world(dxy)
                self._world_view.set_free_camera(True)

        super().update()

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


