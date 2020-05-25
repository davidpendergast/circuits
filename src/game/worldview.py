
import src.engine.renderengine as renderengine

import src.game.spriteref as spriteref


class WorldView:

    def __init__(self, world):
        self._world = world

        self._camera_xy = (0, 0)
        self._camera_zoom = 2

    def update(self):
        cam_x, cam_y = self.get_camera_pos_in_world()
        for layer_id in spriteref.all_world_layers():
            renderengine.get_instance().set_layer_offset(layer_id, cam_x, cam_y )

    def get_camera_pos_in_world(self):
        return self._camera_xy

    def set_camera_pos_in_world(self, xy):
        self._camera_xy = xy

    def move_camera_in_world(self, dxy):
        cur_pos = self.get_camera_pos_in_world()
        self.set_camera_pos_in_world((cur_pos[0] + dxy[0], cur_pos[1] + dxy[1]))

    def get_camera_size_in_world(self, integer=True):
        game_size = renderengine.get_instance().get_game_size()
        if integer:
            return (game_size[0] // self._camera_zoom, game_size[1] // self._camera_zoom)
        else:
            return (game_size[0] / self._camera_zoom, game_size[1] / self._camera_zoom)

    def get_camera_center_in_world(self):
        size = self.get_camera_size_in_world(integer=True)
        xy = self.get_camera_pos_in_world()
        return (xy[0] + size[0] // 2, xy[1] + size[1] // 2)

    def get_camera_rect_in_world(self, integer=True):
        xy = self.get_camera_pos_in_world()
        size = self.get_camera_size_in_world(integer=integer)
        return [xy[0], xy[1], size[0], size[1]]

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

    def all_sprites(self):
        for ent in self._world.entities:
            for spr in ent.all_sprites():
                yield spr

    def all_debug_sprites(self):
        for ent in self._world.entities:
            for spr in ent.all_debug_sprites():
                yield spr


