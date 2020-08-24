
import pygame
import os

import configs as configs

import src.engine.game as game
import src.engine.layers as layers
import src.engine.keybinds as keybinds
import src.engine.inputs as inputs
import src.engine.readme_writer as readme_writer
import src.engine.scenes as scenes
import src.utils.util as util

import src.game.globalstate as gs
import src.game.const as const
import src.game.menus as menus

import src.game.spriteref as spriteref

import pygame


class CircuitsGame(game.Game):

    def __init__(self):
        game.Game.__init__(self)
        self.scene_manager = None

    def initialize(self):
        if configs.is_dev:
            _update_readme()

        keybinds.get_instance().set_binding(const.MOVE_LEFT, [pygame.K_LEFT, pygame.K_a])
        keybinds.get_instance().set_binding(const.MOVE_RIGHT, [pygame.K_RIGHT, pygame.K_d])
        keybinds.get_instance().set_binding(const.JUMP, [pygame.K_UP, pygame.K_w, pygame.K_SPACE])
        keybinds.get_instance().set_binding(const.CROUCH, [pygame.K_DOWN, pygame.K_s])

        keybinds.get_instance().set_binding(const.MENU_UP, [pygame.K_UP, pygame.K_w])
        keybinds.get_instance().set_binding(const.MENU_DOWN, [pygame.K_DOWN, pygame.K_s])
        keybinds.get_instance().set_binding(const.MENU_LEFT, [pygame.K_LEFT, pygame.K_a])
        keybinds.get_instance().set_binding(const.MENU_RIGHT, [pygame.K_RIGHT, pygame.K_d])
        keybinds.get_instance().set_binding(const.MENU_ACCEPT, [pygame.K_RETURN])
        keybinds.get_instance().set_binding(const.MENU_CANCEL, [pygame.K_ESCAPE])

        keybinds.get_instance().set_binding(const.RESET, [pygame.K_r])

        # debug commands
        keybinds.get_instance().set_binding(const.NEXT_LEVEL_DEBUG, [pygame.K_n])
        keybinds.get_instance().set_binding(const.TOGGLE_SPRITE_MODE_DEBUG, [pygame.K_h])
        keybinds.get_instance().set_binding(const.TOGGLE_PLAYER_TYPE, [pygame.K_p])
        keybinds.get_instance().set_binding(const.SAVE_LEVEL_DEBUG, [pygame.K_F2])

        self.scene_manager = scenes.SceneManager(menus.MainMenuScene())

    def get_sheets(self):
        return spriteref.initialize_sheets()

    def get_layers(self):
        # TODO layer depth goes opposite to sprite depths???
        yield layers.PolygonLayer(spriteref.POLYGON_LAYER, 0, sort_sprites=True)
        yield layers.ImageLayer(spriteref.BLOCK_LAYER, 5, sort_sprites=True, use_color=True)
        yield layers.ImageLayer(spriteref.ENTITY_LAYER, 10, sort_sprites=True, use_color=True)

        yield layers.ImageLayer(spriteref.UI_BG_LAYER, 19, sort_sprites=True, use_color=True)
        yield layers.ImageLayer(spriteref.UI_FG_LAYER, 20, sort_sprites=True, use_color=True)

    def update(self):
        self.scene_manager.update()
        gs.get_instance().update()

    def get_clear_color(self):
        return self.scene_manager.get_clear_color()

    def all_sprites(self):
        for spr in self.scene_manager.all_sprites():
            yield spr


def _update_readme():
    gif_directory = "gifs"
    gif_filenames = [f for f in os.listdir(gif_directory) if os.path.isfile(os.path.join(gif_directory, f))]
    gif_filenames = [f for f in gif_filenames if f.endswith(".gif") and f[0].isdigit()]
    gif_filenames.sort(key=lambda text: util.parse_leading_int(text, or_else=-1), reverse=True)

    def _key_lookup(key: str):
        n = util.parse_ending_int(key, or_else=-1)
        if n < 0 or n >= len(gif_filenames):
            return None
        if key.startswith("file_"):
            return gif_filenames[n]
        elif key.startswith("name_"):
            return gif_filenames[n][:-4]  # rm the ".gif" part
        else:
            return None

    readme_writer.write_readme("README_template.txt", "README.md",
                               key_lookup=_key_lookup,
                               skip_line_if_value_missing=True)
