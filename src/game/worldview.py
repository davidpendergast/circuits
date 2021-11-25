
import pygame

import src.utils.util as util
import src.engine.renderengine as renderengine
import src.engine.inputs as inputs
import src.engine.sprites as sprites

import src.game.globalstate as gs
import src.game.spriteref as spriteref
import src.game.colors as colors


class WorldView:

    def __init__(self, world):
        self._world = world

        self._free_camera = False  # if false, camera follows player

        self._show_grid = True
        self._grid_line_sprites = []

        self._camera_xy = (0, 0)

        self._camera_zoom_idx = 1
        self._zoom_levels = (0.5, 1, 2, 3, 4)

    def update(self):
        zoom_change = 0
        if inputs.get_instance().was_pressed(pygame.K_MINUS):
            zoom_change -= 1
        if inputs.get_instance().was_pressed(pygame.K_EQUALS):
            zoom_change += 1
        if zoom_change != 0:
            self.adjust_zoom(zoom_change)

        if inputs.get_instance().was_pressed(pygame.K_f):
            self._free_camera = not self._free_camera
            print("INFO: toggled free camera to: {}".format(self._free_camera))

        if inputs.get_instance().was_pressed(pygame.K_g):
            self._show_grid = not self._show_grid
            print("INFO: toggled grid to: {}".format(self._show_grid))

        if inputs.get_instance().was_pressed(pygame.K_h):
            gs.get_instance().debug_render = not gs.get_instance().debug_render
            print("INFO: toggled debug sprites to: {}".format(gs.get_instance().debug_render))

        if not self._free_camera:
            player = self._world.get_player()
            if player is not None:
                rect = player.get_rect()
                new_cam_center = (rect[0] + rect[2] // 2, rect[1] + rect[3] // 2)
                self.set_camera_center_in_world(new_cam_center)
                self._world.constrain_camera(self)

        cam_x, cam_y = self.get_camera_pos_in_world()

        # update the sprites of entities near the camera
        for ent in self.get_entities_to_render_this_frame():
            ent.update_sprites()

        self._update_grid_line_sprites()

        for layer_id in spriteref.all_world_layers():
            renderengine.get_instance().set_layer_scale(layer_id, self.get_zoom())
            renderengine.get_instance().set_layer_offset(layer_id,
                                                         cam_x * self.get_zoom(),
                                                         cam_y * self.get_zoom())

    def set_free_camera(self, val):
        self._free_camera = val

    def adjust_zoom(self, dz):
        old_center = self.get_camera_center_in_world()

        new_zoom_idx = util.bound(int(self._camera_zoom_idx + dz), 0, len(self._zoom_levels) - 1)
        self._camera_zoom_idx = new_zoom_idx
        self.set_camera_center_in_world(old_center)

    def get_zoom(self):
        return self._zoom_levels[self._camera_zoom_idx]

    def set_zoom(self, zoom_level):
        if zoom_level in self._zoom_levels:
            self._camera_zoom_idx = self._zoom_levels.index(zoom_level)
        else:
            print("ERROR: invalid zoom level, ignoring request: {}".format(zoom_level))

    def get_camera_pos_in_world(self):
        return self._camera_xy

    def set_camera_pos_in_world(self, xy):
        new_x = xy[0] if xy[0] is not None else self._camera_xy[0]
        new_y = xy[1] if xy[1] is not None else self._camera_xy[1]
        self._camera_xy = (new_x, new_y)

    def set_camera_center_in_world(self, xy):
        size = self.get_camera_size_in_world()
        new_x = xy[0] - size[0] // 2 if xy[0] is not None else self._camera_xy[0]
        new_y = xy[1] - size[1] // 2 if xy[1] is not None else self._camera_xy[1]
        self._camera_xy = (new_x, new_y)

    def move_camera_in_world(self, dxy):
        cur_pos = self.get_camera_pos_in_world()
        new_x = cur_pos[0] + dxy[0] if dxy[0] is not None else None
        new_y = cur_pos[1] + dxy[1] if dxy[1] is not None else None
        self.set_camera_pos_in_world((new_x, new_y))

    def get_camera_size_in_world(self, integer=True):
        game_size = renderengine.get_instance().get_game_size()
        zoom = self.get_zoom()
        if integer:
            return (game_size[0] // zoom, game_size[1] // zoom)
        else:
            return (game_size[0] / zoom, game_size[1] / zoom)

    def get_camera_center_in_world(self):
        size = self.get_camera_size_in_world(integer=True)
        xy = self.get_camera_pos_in_world()
        return (xy[0] + size[0] // 2, xy[1] + size[1] // 2)

    def get_camera_rect_in_world(self, integer=True, expansion=0):
        xy = self.get_camera_pos_in_world()
        size = self.get_camera_size_in_world(integer=integer)
        return [xy[0] - expansion,
                xy[1] - expansion,
                size[0] + expansion * 2,
                size[1] + expansion * 2]

    def get_entities_to_render_this_frame(self):
        buffer_zone = gs.get_instance().cell_size * 4
        render_zone = self.get_camera_rect_in_world(integer=True, expansion=buffer_zone)
        for ent in self._world.all_entities_in_rect(render_zone):
            yield ent

    def screen_pos_to_world_pos(self, screen_xy):
        if screen_xy is None:
            return None
        game_size = renderengine.get_instance().get_game_size()
        x_pct = screen_xy[0] / game_size[0]
        y_pct = screen_xy[1] / game_size[1]

        cam_rect = self.get_camera_rect_in_world(integer=False)
        return (cam_rect[0] + int(x_pct * cam_rect[2]),
                cam_rect[1] + int(y_pct * cam_rect[3]))

    def world_pos_to_screen_pos(self, world_xy):
        if world_xy is None:
            return None
        cam_rect = self.get_camera_rect_in_world(integer=False)
        x_pct = (world_xy[0] - cam_rect[0]) / cam_rect[2]
        y_pct = (world_xy[1] - cam_rect[1]) / cam_rect[3]

        game_size = renderengine.get_instance().get_game_size()

        return int(x_pct * game_size[0]), int(y_pct * game_size[1])

    def _update_grid_line_sprites(self):
        if self._show_grid:
            cam_rect = self.get_camera_rect_in_world()
            cs = gs.get_instance().cell_size
            n_x_lines = int(cam_rect[2] // cs)
            n_y_lines = int(cam_rect[3] // cs)
            util.extend_or_empty_list_to_length(self._grid_line_sprites, n_x_lines + n_y_lines,
                                                creator=lambda: sprites.LineSprite(spriteref.POLYGON_LAYER))
            for i in range(0, n_x_lines):
                x_line_sprite = self._grid_line_sprites[i]
                p1 = (cam_rect[0] - (cam_rect[0] % cs) + cs * (i + 1), cam_rect[1])
                p2 = (cam_rect[0] - (cam_rect[0] % cs) + cs * (i + 1), cam_rect[1] + cam_rect[3])
                x_line_sprite.update(new_p1=p1, new_p2=p2, new_thickness=1,
                                     new_color=colors.PERFECT_VERY_DARK_GRAY, new_depth=500)

            for i in range(0, n_y_lines):
                y_line_sprite = self._grid_line_sprites[i + n_x_lines]
                p1 = (cam_rect[0], (cam_rect[1] - (cam_rect[1] % cs) + cs * (i + 1)))
                p2 = (cam_rect[0] + cam_rect[2], (cam_rect[1] - (cam_rect[1] % cs) + cs * (i + 1)))
                y_line_sprite.update(new_p1=p1, new_p2=p2, new_thickness=1,
                                     new_color=colors.PERFECT_VERY_DARK_GRAY, new_depth=500)
        else:
            self._grid_line_sprites.clear()

    def all_sprites(self):
        for ent in self.get_entities_to_render_this_frame():
            if gs.get_instance().debug_render:
                for spr in ent.all_debug_sprites():
                    yield spr
            else:
                for spr in ent.all_sprites():
                    yield spr

        for spr in self._grid_line_sprites:
            yield spr

