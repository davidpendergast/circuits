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


class MainMenuScene(scenes.Scene):

    def __init__(self):
        scenes.Scene.__init__(self)
        self._title_element = SpriteElement()

        self._options_list = OptionsList()
        self._options_list.add_option("start", lambda: self.get_manager().set_next_scene(DebugGameScene()))
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
            text_sprite = sprites.ImageSprite(spriteref.object_sheet().title_img, 0, 0, spriteref.UI_FG_LAYER, scale=4)
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


class OptionsList(ui.ElementGroup):

    def __init__(self):
        ui.ElementGroup.__init__(self)
        self.selected_idx = 0
        self.options = []  # list of (UiElement: element, str: text, lambda: do_action, lambda: is_enabled)
        self.y_spacing = 4

    def add_option(self, text, do_action, is_enabled=lambda: True):
        element = SpriteElement()
        self.options.append((element, text, do_action, is_enabled))
        self.add_child(element)

    def update(self):

        # TODO - is this the place we should be doing this?
        # TODO - it's fine for now I think
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_UP)):
            self.selected_idx = (self.selected_idx - 1) % len(self.options)
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_DOWN)):
            self.selected_idx = (self.selected_idx + 1) % len(self.options)

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_ACCEPT)):
            if 0 <= self.selected_idx < len(self.options):
                action = self.options[self.selected_idx][2]
                try:
                    action()
                except Exception as e:
                    print("ERROR: failed to activate option: {}".format(self.options[1]))
                    traceback.print_exc()

        y = 0
        for i in range(0, len(self.options)):
            element, text, do_action, is_enabled = self.options[i]

            if not is_enabled():
                element.set_color(colors.DARK_GRAY)
            elif i == self.selected_idx:
                element.set_color(colors.PERFECT_RED)
            else:
                element.set_color(colors.PERFECT_WHITE)

            text_spr = element.get_sprite()
            if text_spr is None:
                text_spr = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, text)
                element.set_sprite(text_spr)

            element.set_xy((0, y))
            y += element.get_size()[1] + self.y_spacing


class SpriteElement(ui.UiElement):

    def __init__(self, sprite=None):
        ui.UiElement.__init__(self)
        self.sprite = None
        self.color = colors.PERFECT_WHITE
        self.set_sprite(sprite)

    def set_sprite(self, sprite):
        if sprite is None:
            self.sprite = None
        else:
            # XXX only supports sprites that can handle `update(new_x=int, new_y=int)`
            if not isinstance(sprite, sprites.ImageSprite) and not isinstance(sprite, sprites.TextSprite):
                raise ValueError("unsupported sprite type: {}".format(type(sprite).__name__))
            self.sprite = sprite

    def get_sprite(self):
        return self.sprite

    def set_color(self, color):
        self.color = color if color is not None else colors.PERFECT_WHITE

    def update(self):
        abs_xy = self.get_xy(absolute=True)
        if self.sprite is not None:
            self.sprite = self.sprite.update(new_x=abs_xy[0], new_y=abs_xy[1], new_color=self.color)

    def all_sprites(self):
        if self.sprite is not None:
            for spr in self.sprite.all_sprites():
                yield spr

    def get_size(self):
        if self.sprite is not None:
            return self.sprite.size()
        else:
            return (0, 0)


class DebugGameScene(scenes.Scene):

    def __init__(self, world_type=0):
        scenes.Scene.__init__(self)
        self._world = None
        self._world_view = None

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
            self._cur_test_world += 1
            self._create_new_world(world_type=self._cur_test_world)

        if configs.is_dev and inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.SAVE_LEVEL_DEBUG)):
            if self._world is not None:
                bp = self._world.get_blueprint()
                if bp is not None:
                    filepath = "testing/saved_level.json"
                    print("INFO: saving level to {}".format(filepath))
                    blueprints.write_level_to_file(bp, filepath)

        if configs.is_dev and inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.TOGGLE_SPRITE_MODE_DEBUG)):
            debug.toggle_debug_sprite_mode()

        if inputs.get_instance().mouse_is_dragging(button=1):
            drag_this_frame = inputs.get_instance().mouse_drag_this_frame(button=1)
            if drag_this_frame is not None:
                dxy = util.sub(drag_this_frame[1], drag_this_frame[0])
                dxy = util.mult(dxy, -1 / self._world_view.get_zoom())
                self._world_view.move_camera_in_world(dxy)
                self._world_view.set_free_camera(True)
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

    def _create_new_world(self, world_type=0):
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


