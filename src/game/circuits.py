
import pygame
import os

import configs as configs

import src.engine.game as game
import src.engine.layers as layers
import src.engine.keybinds as keybinds
import src.engine.inputs as inputs
import src.engine.readme_writer as readme_writer
import src.utils.util as util

import src.game.worlds as worlds
import src.game.globalstate as gs
import src.game.const as const

import src.game.spriteref as spriteref


class CircuitsGame(game.Game):

    def __init__(self):
        game.Game.__init__(self)
        self._world = None

    def initialize(self):
        if configs.is_dev:
            _update_readme()

        keybinds.get_instance().set_binding(const.MOVE_LEFT, [pygame.K_LEFT, pygame.K_a])
        keybinds.get_instance().set_binding(const.MOVE_RIGHT, [pygame.K_RIGHT, pygame.K_d])
        keybinds.get_instance().set_binding(const.JUMP, [pygame.K_UP, pygame.K_w, pygame.K_SPACE])

        keybinds.get_instance().set_binding(const.RESET, [pygame.K_r])

        self._world = worlds.World.new_test_world()

    def get_sheets(self):
        return []

    def get_layers(self):
        yield layers.ImageLayer(spriteref.BLOCK_LAYER, 0, sort_sprites=True, use_color=True)
        yield layers.ImageLayer(spriteref.ENTITY_LAYER, 5, sort_sprites=True, use_color=True)
        yield layers.PolygonLayer(spriteref.POLYGON_LAYER, 12, sort_sprites=True)

        yield layers.ImageLayer(spriteref.UI_FG_LAYER, 20, sort_sprites=True, use_color=True)
        yield layers.ImageLayer(spriteref.UI_BG_LAYER, 19, sort_sprites=True, use_color=True)

    def update(self):
        if inputs.get_instance().mouse_was_pressed():  # debug
            pos = inputs.get_instance().mouse_pos()
            camera_pos = (0, 0)
            cell_size = gs.get_instance().cell_size
            print("INFO: mouse pressed at ({}, {})".format((pos[0] + camera_pos[0]) // cell_size,
                                                           (pos[1] + camera_pos[1]) // cell_size))

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.RESET)):
            self._world = worlds.World.new_test_world()

        self._world.update()

    def all_sprites(self):
        if gs.get_instance().debug_render:
            for spr in self._world.all_debug_sprites():
                yield spr
        else:
            for spr in self._world.all_sprites():
                yield spr


def _update_readme():
    gif_directory = "gifs"
    gif_filenames = [f for f in os.listdir(gif_directory) if os.path.isfile(os.path.join(gif_directory, f))]
    gif_filenames = [f for f in gif_filenames if f.endswith(".gif") and f[0].isdigit()]
    gif_filenames.sort(key=lambda text: util.Utils.parse_leading_int(text, or_else=-1), reverse=True)

    def _key_lookup(key: str):
        n = util.Utils.parse_ending_int(key, or_else=-1)
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
