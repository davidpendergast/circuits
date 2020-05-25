
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
import src.game.worldview as worldview
import src.game.globalstate as gs
import src.game.const as const
import src.game.blueprints as blueprints

import src.game.spriteref as spriteref


class CircuitsGame(game.Game):

    def __init__(self):
        game.Game.__init__(self)
        self._world = None
        self._world_view = None

    def initialize(self):
        if configs.is_dev:
            _update_readme()

        keybinds.get_instance().set_binding(const.MOVE_LEFT, [pygame.K_LEFT, pygame.K_a])
        keybinds.get_instance().set_binding(const.MOVE_RIGHT, [pygame.K_RIGHT, pygame.K_d])
        keybinds.get_instance().set_binding(const.JUMP, [pygame.K_UP, pygame.K_w, pygame.K_SPACE])

        keybinds.get_instance().set_binding(const.RESET, [pygame.K_r])

        self._create_new_world()

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
            camera_pos = self._world_view.get_camera_pos_in_world()
            cell_size = gs.get_instance().cell_size
            print("INFO: mouse pressed at ({}, {})".format((pos[0] + camera_pos[0]) // cell_size,
                                                           (pos[1] + camera_pos[1]) // cell_size))

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.RESET)):
            self._create_new_world()

        if inputs.get_instance().mouse_is_dragging(button=1):
            drag_this_frame = inputs.get_instance().mouse_drag_this_frame(button=1)
            if drag_this_frame is not None:
                dxy = util.sub(drag_this_frame[1], drag_this_frame[0])
                dxy = util.mult(dxy, -1 / self._world_view.get_zoom())
                self._world_view.move_camera_in_world(dxy)
                self._world_view.set_free_camera(True)

        self._world.update()
        self._world_view.update()

    def _create_new_world(self):
        bp = blueprints.get_test_blueprint()
        self._world = bp.create_world()

        self._world_view = worldview.WorldView(self._world)
        self._world_view.set_camera_attached_to(self._world.get_player())

    def all_sprites(self):
        if gs.get_instance().debug_render:
            for spr in self._world_view.all_debug_sprites():
                yield spr
        else:
            for spr in self._world_view.all_sprites():
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
