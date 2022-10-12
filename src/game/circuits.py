
import pygame

import os

import configs as configs

import src.engine.game as game
import src.engine.layers as layers
import src.engine.threedee as threedee
import src.engine.keybinds as keybinds
import src.engine.inputs as inputs
import src.engine.readme_writer as readme_writer
import src.engine.cursors as cursors
import src.engine.scenes as scenes
import src.engine.globaltimer as globaltimer
import src.engine.window as window
import src.engine.renderengine as renderengine
import src.utils.util as util

import src.game.globalstate as gs
import src.game.const as const
import src.game.menus as menus
import src.game.songsystem as songsystem

import src.game.spriteref as spriteref

import pygame


class CircuitsGame(game.Game):

    def __init__(self):
        game.Game.__init__(self)

    def initialize(self):
        if configs.is_dev:
            _update_readme()

        util.set_info_for_user_data_path(configs.userdata_subdir, "Ghast")

        keybinds.get_instance().set_binding(const.MOVE_LEFT, [pygame.K_LEFT, pygame.K_a])
        keybinds.get_instance().set_binding(const.MOVE_RIGHT, [pygame.K_RIGHT, pygame.K_d])
        keybinds.get_instance().set_binding(const.JUMP, [pygame.K_UP, pygame.K_w, pygame.K_SPACE])
        keybinds.get_instance().set_binding(const.CROUCH, [pygame.K_DOWN, pygame.K_s])
        keybinds.get_instance().set_binding(const.ACTION, [pygame.K_f, pygame.K_j, pygame.K_RETURN])

        keybinds.get_instance().set_binding(const.MENU_UP, [pygame.K_UP, pygame.K_w])
        keybinds.get_instance().set_binding(const.MENU_DOWN, [pygame.K_DOWN, pygame.K_s])
        keybinds.get_instance().set_binding(const.MENU_LEFT, [pygame.K_LEFT, pygame.K_a])
        keybinds.get_instance().set_binding(const.MENU_RIGHT, [pygame.K_RIGHT, pygame.K_d])
        keybinds.get_instance().set_binding(const.MENU_ACCEPT, [pygame.K_RETURN])
        keybinds.get_instance().set_binding(const.MENU_CANCEL, [pygame.K_ESCAPE])

        keybinds.get_instance().set_binding(const.RESET, keybinds.Binding(pygame.K_r, mods=pygame.KMOD_SHIFT))
        keybinds.get_instance().set_binding(const.SOFT_RESET, [pygame.K_r])

        keybinds.get_instance().set_binding(const.TOGGLE_MUTE, [pygame.K_m])

        # debug commands
        keybinds.get_instance().set_binding(const.TOGGLE_SPRITE_MODE_DEBUG, [pygame.K_h])
        keybinds.get_instance().set_binding(const.TOGGLE_PLAYER_TYPE, [pygame.K_p])
        keybinds.get_instance().set_binding(const.TEST_KEY_1, keybinds.Binding(pygame.K_1, mods=pygame.KMOD_SHIFT))
        keybinds.get_instance().set_binding(const.TEST_KEY_2, keybinds.Binding(pygame.K_2, mods=pygame.KMOD_SHIFT))
        keybinds.get_instance().set_binding(const.TEST_KEY_3, keybinds.Binding(pygame.K_3, mods=pygame.KMOD_SHIFT))
        keybinds.get_instance().set_binding(const.TOGGLE_SHOW_LIGHTING, keybinds.Binding(pygame.K_l))
        keybinds.get_instance().set_binding(const.UNLOCK_ALL_DEBUG, keybinds.Binding(pygame.K_u, mods=pygame.KMOD_CTRL))

        keybinds.get_instance().set_binding(const.SAVE, keybinds.Binding(pygame.K_s, mods=[pygame.KMOD_CTRL, pygame.KMOD_NONE]))
        keybinds.get_instance().set_binding(const.SAVE_AS, keybinds.Binding(pygame.K_s, mods=[pygame.KMOD_CTRL, pygame.KMOD_SHIFT, pygame.KMOD_NONE]))

        # level editor commands
        keybinds.get_instance().set_binding(const.TOGGLE_SHOW_CAPTION_INFO, [pygame.K_F3])
        keybinds.get_instance().set_binding(const.TOGGLE_EDIT_MODE, [pygame.K_F5])
        keybinds.get_instance().set_binding(const.TOGGLE_COMPAT_MODE, [pygame.K_F6])

        keybinds.get_instance().set_binding(const.MOVE_SELECTION_UP, keybinds.Binding(pygame.K_w, mods=pygame.KMOD_NONE))
        keybinds.get_instance().set_binding(const.MOVE_SELECTION_LEFT, keybinds.Binding(pygame.K_a, mods=pygame.KMOD_NONE))
        keybinds.get_instance().set_binding(const.MOVE_SELECTION_DOWN, keybinds.Binding(pygame.K_s, mods=pygame.KMOD_NONE))
        keybinds.get_instance().set_binding(const.MOVE_SELECTION_RIGHT, keybinds.Binding(pygame.K_d, mods=pygame.KMOD_NONE))

        keybinds.get_instance().set_binding(const.MOVE_CAMERA_UP, [pygame.K_UP])
        keybinds.get_instance().set_binding(const.MOVE_CAMERA_LEFT, [pygame.K_LEFT])
        keybinds.get_instance().set_binding(const.MOVE_CAMERA_DOWN, [pygame.K_DOWN])
        keybinds.get_instance().set_binding(const.MOVE_CAMERA_RIGHT, [pygame.K_RIGHT])

        keybinds.get_instance().set_binding(const.SHRINK_SELECTION_VERT, keybinds.Binding(pygame.K_w, mods=[pygame.KMOD_SHIFT, pygame.KMOD_NONE]))
        keybinds.get_instance().set_binding(const.SHRINK_SELECTION_HORZ, keybinds.Binding(pygame.K_a, mods=[pygame.KMOD_SHIFT, pygame.KMOD_NONE]))
        keybinds.get_instance().set_binding(const.GROW_SELECTION_VERT, keybinds.Binding(pygame.K_s, mods=[pygame.KMOD_SHIFT, pygame.KMOD_NONE]))
        keybinds.get_instance().set_binding(const.GROW_SELECTION_HORZ, keybinds.Binding(pygame.K_d, mods=[pygame.KMOD_SHIFT, pygame.KMOD_NONE]))

        keybinds.get_instance().set_binding(const.CYCLE_SELECTION_SUBTYPE_FORWARD, keybinds.Binding(pygame.K_t, mods=pygame.KMOD_NONE))
        keybinds.get_instance().set_binding(const.CYCLE_SELECTION_SUBTYPE_BACKWARD, keybinds.Binding(pygame.K_t, mods=[pygame.KMOD_SHIFT, pygame.KMOD_NONE]))

        keybinds.get_instance().set_binding(const.CYCLE_SELECTION_COLOR_FORWARD, keybinds.Binding(pygame.K_c, mods=pygame.KMOD_NONE))
        keybinds.get_instance().set_binding(const.CYCLE_SELECTION_COLOR_BACKWARD, keybinds.Binding(pygame.K_c, mods=[pygame.KMOD_SHIFT, pygame.KMOD_NONE]))

        keybinds.get_instance().set_binding(const.CYCLE_SELECTION_ART_FORWARD, keybinds.Binding(pygame.K_e, mods=pygame.KMOD_NONE))
        keybinds.get_instance().set_binding(const.CYCLE_SELECTION_ART_BACKWARD, keybinds.Binding(pygame.K_e, mods=[pygame.KMOD_SHIFT, pygame.KMOD_NONE]))

        keybinds.get_instance().set_binding(const.TOGGLE_SELECTION_INVERTED, keybinds.Binding(pygame.K_i, mods=pygame.KMOD_NONE))
        keybinds.get_instance().set_binding(const.ADVANCED_EDIT, keybinds.Binding(pygame.K_o, mods=pygame.KMOD_NONE))

        keybinds.get_instance().set_binding(const.ADD_POINT, keybinds.Binding(pygame.K_p, mods=pygame.KMOD_NONE))
        keybinds.get_instance().set_binding(const.REMOVE_POINT, keybinds.Binding(pygame.K_p, mods=[pygame.KMOD_SHIFT, pygame.KMOD_NONE]))
        keybinds.get_instance().set_binding(const.CLEAR_POINTS, keybinds.Binding(pygame.K_p, mods=[pygame.KMOD_SHIFT, pygame.KMOD_CTRL, pygame.KMOD_NONE]))
        keybinds.get_instance().set_binding(const.ROTATE_POINTS_FORWARD, keybinds.Binding(pygame.K_p, mods=[pygame.KMOD_ALT, pygame.KMOD_NONE]))
        keybinds.get_instance().set_binding(const.ROTATE_POINTS_BACKWARD, keybinds.Binding(pygame.K_p, mods=[pygame.KMOD_ALT, pygame.KMOD_SHIFT, pygame.KMOD_NONE]))

        keybinds.get_instance().set_binding(const.DECREASE_EDIT_RESOLUTION, [pygame.K_LEFTBRACKET])
        keybinds.get_instance().set_binding(const.INCREASE_EDIT_RESOLUTION, [pygame.K_RIGHTBRACKET])

        keybinds.get_instance().set_binding(const.OPTION_0, [pygame.K_1])
        keybinds.get_instance().set_binding(const.OPTION_1, [pygame.K_2])
        keybinds.get_instance().set_binding(const.OPTION_2, [pygame.K_3])
        keybinds.get_instance().set_binding(const.OPTION_3, [pygame.K_4])
        keybinds.get_instance().set_binding(const.OPTION_4, [pygame.K_5])
        keybinds.get_instance().set_binding(const.OPTION_5, [pygame.K_6])
        keybinds.get_instance().set_binding(const.OPTION_6, [pygame.K_7])
        keybinds.get_instance().set_binding(const.OPTION_7, [pygame.K_8])
        keybinds.get_instance().set_binding(const.OPTION_8, [pygame.K_9])
        keybinds.get_instance().set_binding(const.OPTION_9, [pygame.K_0])

        keybinds.get_instance().set_binding(const.UNDO, keybinds.Binding(pygame.K_z, mods=pygame.KMOD_CTRL))
        keybinds.get_instance().set_binding(const.REDO, keybinds.Binding(pygame.K_y, mods=pygame.KMOD_CTRL))

        keybinds.get_instance().set_binding(const.DELETE, [pygame.K_DELETE, pygame.K_BACKSPACE])

        keybinds.get_instance().set_binding(const.COPY, keybinds.Binding(pygame.K_c, mods=pygame.KMOD_CTRL))
        keybinds.get_instance().set_binding(const.PASTE, keybinds.Binding(pygame.K_v, mods=pygame.KMOD_CTRL))
        keybinds.get_instance().set_binding(const.CUT, keybinds.Binding(pygame.K_x, mods=pygame.KMOD_CTRL))
        keybinds.get_instance().set_binding(const.SELECT_ALL, keybinds.Binding(pygame.K_a, mods=[pygame.KMOD_CTRL, pygame.KMOD_NONE]))
        keybinds.get_instance().set_binding(const.SELECT_ALL_ONSCREEN, keybinds.Binding(pygame.K_a, mods=[pygame.KMOD_SHIFT, pygame.KMOD_CTRL, pygame.KMOD_NONE]))

        path_to_cursors = util.resource_path("assets/cursors.png")

        cursors.init_cursors(path_to_cursors, [
            (const.CURSOR_DEFAULT, [0, 0, 16, 16], (0, 0)),
            (const.CURSOR_HAND, [16, 0, 16, 16], (5, 3)),
            (const.CURSOR_INVIS, [32, 0, 16, 16], (0, 0))
        ])
        cursors.set_cursor(const.CURSOR_DEFAULT)

        globaltimer.set_show_fps(True)

        gs.get_instance().load_data_from_disk()

        scenes.set_instance(menus.CircuitsSceneManager(menus.MainMenuScene()))

    def get_sheets(self):
        return spriteref.initialize_sheets()

    def get_layers(self):
        yield threedee.ThreeDeeLayer(spriteref.THREEDEE_LAYER, 1)
        yield layers.PolygonLayer(spriteref.POLYGON_LAYER, 3)

        yield layers.ImageLayer(spriteref.BLOCK_LAYER, 5)
        yield layers.ImageLayer(spriteref.ENTITY_LAYER, 10)
        yield layers.ImageLayer(spriteref.WORLD_UI_LAYER, 12)

        yield layers.PolygonLayer(spriteref.POLYGON_UI_BG_LAYER, 15)
        yield layers.ImageLayer(spriteref.UI_BG_LAYER, 19)
        yield layers.ImageLayer(spriteref.UI_FG_LAYER, 20)
        yield layers.PolygonLayer(spriteref.POLYGON_ULTRA_OMEGA_TOP_LAYER, 10000)
        yield layers.ImageLayer(spriteref.ULTRA_OMEGA_GAMMA_TOP_IMAGE_LAYER, 10005)

    def update(self):
        self._handle_global_keybinds()

        scenes.get_instance().update()
        gs.get_instance().update()

        songsystem.get_instance().update()

        if globaltimer.tick_count() % 15 == 0:
            window.get_instance().set_caption_info("SPRITES", renderengine.get_instance().count_sprites())
            window.get_instance().set_caption_info("NO_GL_MODE", None if window.get_instance().is_opengl_mode() else "True")
        return not gs.get_instance().should_exit()

    def cleanup(self):
        gs.get_instance().save_data_to_disk()

    def get_clear_color(self):
        return scenes.get_instance().get_clear_color()

    def all_sprites(self):
        for spr in gs.get_instance().all_sprites():
            yield spr
        for spr in scenes.get_instance().all_sprites():
            yield spr

    def _handle_global_keybinds(self):
        if inputs.get_instance().was_pressed(const.TOGGLE_MUTE):
            is_muted = (gs.get_instance().get_settings().get(gs.Settings.MUTE_MUSIC) and
                        gs.get_instance().get_settings().get(gs.Settings.EFFECTS_VOLUME))
            print(f"INFO: {'unmuting' if is_muted else 'muting'} audio")
            gs.get_instance().get_settings().set(gs.Settings.MUTE_MUSIC, not is_muted)
            gs.get_instance().get_settings().set(gs.Settings.MUTE_EFFECTS, not is_muted)

        if inputs.get_instance().was_pressed(const.TOGGLE_SHOW_CAPTION_INFO):
            win = window.get_instance()
            print(f"INFO: toggling caption info to {not win.is_showing_caption_info()}")
            win.set_show_caption_info(not win.is_showing_caption_info())

        if inputs.get_instance().was_pressed(const.TOGGLE_COMPAT_MODE):
            win = window.get_instance()

            if win.is_fullscreen():
                win.set_fullscreen(False)

            print(f"INFO: setting compat mode to {win.is_opengl_mode()}")
            win.set_opengl_mode(not win.is_opengl_mode())


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
