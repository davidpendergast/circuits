
import pygame

import src.utils.util as util
import src.engine.renderengine as renderengine
import src.engine.inputs as inputs
import src.engine.sprites as sprites

import configs
import src.game.globalstate as gs
import src.game.spriteref as spriteref
import src.engine.spritesheets as spritesheets
import src.game.colors as colors


_ZOOM_LEVELS = (0.5, 1, 2, 3, 4)


class WorldView:

    def __init__(self, world):
        self._world = world

        self._free_camera = False  # if false, camera follows player

        self._show_grid = True
        self._grid_line_sprites = []

        self._entities_to_render = []

        self._hide_regions_outside_camera_bounds = True
        self._out_of_bounds_blockers = [None] * 4  # top, right, bottom, left

        # the "true" zoom
        self._base_zoom_idx = 1
        self._base_camera_xy = (0, 0)

        # the "temp" zoom, during dialog and such
        self._temp_zoom_idx = None
        self._temp_zoom_center_provider = lambda: self.get_camera_center_in_world(ignore_temp_zoom=True)
        self._temp_zoom_tick_count = 0
        self._temp_zoom_delay = 20
        self._use_temp_zoom = False

        self._bg_colors = [colors.PERFECT_BLACK]
        self._bg_colors_period = 120
        self._bg_colors_tick = 0
        self._loop_bg_colors = True

    def update(self):
        if configs.is_dev:
            self._handle_debug_inputs()

        if self._temp_zoom_idx is not None:
            self._temp_zoom_tick_count = min(self._temp_zoom_delay, self._temp_zoom_tick_count + 1)
            if not self._use_temp_zoom and self._temp_zoom_tick_count >= self._temp_zoom_delay:
                # remove temp zoom
                self._temp_zoom_idx = None

        self._bg_colors_tick += 1

        if not self._free_camera:
            player = self._world.get_player()
            if player is not None:
                center = player.get_center()
                for cb in self._world.all_camera_bounds_containing(center):
                    self._world.set_active_camera_idx(cb[0])
                    break

                rect = player.get_rect()
                new_cam_center = (rect[0] + rect[2] // 2, rect[1] + rect[3] // 2)
                self.set_camera_center_in_world(new_cam_center)
                cam_rect = self._world.constrain_camera(self.get_camera_rect_in_world(ignore_temp_zoom=True))
                self.set_camera_pos_in_world((cam_rect[0], cam_rect[1]))

        camera_bound_rect = self._world.get_camera_bound()
        cam_x, cam_y = self.get_camera_pos_in_world()

        self._entities_to_render = [ent for ent in self._calc_entities_to_render_this_frame(inside_rect=camera_bound_rect)]

        # update the sprites of entities near the camera
        for ent in self._entities_to_render:
            ent.update_sprites()

        self._update_grid_line_sprites()
        self._update_out_of_bounds_blockers(camera_bound_rect, bg_color=self.get_current_bg_color())

        for layer_id in spriteref.all_world_layers():
            renderengine.get_instance().set_layer_scale(layer_id, self.get_zoom())
            renderengine.get_instance().set_layer_offset(layer_id,
                                                         cam_x * self.get_zoom(),
                                                         cam_y * self.get_zoom())

    def set_free_camera(self, val):
        self._free_camera = val

    def _handle_debug_inputs(self):
        zoom_change = 0
        if inputs.get_instance().was_pressed(pygame.K_MINUS):
            zoom_change -= 1
        if inputs.get_instance().was_pressed(pygame.K_EQUALS):
            zoom_change += 1
        if zoom_change != 0:
            self.adjust_base_zoom(zoom_change)

        if inputs.get_instance().was_pressed(pygame.K_f):
            self._free_camera = not self._free_camera
            print("INFO: toggled free camera to: {}".format(self._free_camera))

        if inputs.get_instance().was_pressed(pygame.K_g):
            self._show_grid = not self._show_grid
            print("INFO: toggled grid to: {}".format(self._show_grid))

        if inputs.get_instance().was_pressed(pygame.K_h):
            gs.get_instance().debug_render = not gs.get_instance().debug_render
            print("INFO: toggled debug sprites to: {}".format(gs.get_instance().debug_render))

    def set_bg_colors(self, colors, period=120, loop=True):
        if colors is None:
            colors = [colors.PERFECT_BLACK]
        elif isinstance(colors, tuple):
            colors = [colors]

        self._bg_colors = colors
        self._bg_colors_tick = 0
        self._bg_colors_period = period
        self._loop_bg_colors = loop

    def fade_to_bg_color(self, color, delay):
        self.set_bg_colors([self.get_current_bg_color(), color], period=delay, loop=False)

    def get_current_bg_color(self):
        n_colors = len(self._bg_colors)
        if n_colors == 0:
            return colors.PERFECT_BLACK
        elif n_colors == 1:
            return self._bg_colors[0]
        elif not self._loop_bg_colors and self._bg_colors_tick >= self._bg_colors_period * n_colors:
            return self._bg_colors[-1]
        else:
            idx1 = (self._bg_colors_tick // self._bg_colors_period) % n_colors
            idx2 = (idx1 + 1) % n_colors if self._loop_bg_colors else min(idx1 + 1, n_colors - 1)
            prog = (self._bg_colors_tick % self._bg_colors_period) / self._bg_colors_period
            return util.linear_interp(self._bg_colors[idx1], self._bg_colors[idx2], prog)

    def adjust_base_zoom(self, dz: int):
        old_center = self.get_camera_center_in_world(ignore_temp_zoom=True)

        new_zoom_idx = util.bound(int(self._base_zoom_idx + dz), 0, len(_ZOOM_LEVELS) - 1)
        self._base_zoom_idx = new_zoom_idx
        self.set_camera_center_in_world(old_center)

    def set_temp_zoom(self, zoom_idx, center=None, delay=30):
        if zoom_idx is None:
            if self._use_temp_zoom:
                # return to regular zoom
                self._use_temp_zoom = False
                self._temp_zoom_tick_count = 0
                self._temp_zoom_delay = delay
        else:
            if center is None:
                temp_center_provider = lambda: None
            elif isinstance(center, (list, tuple)):
                temp_center_provider = lambda: center
            else:
                temp_center_provider = center

            self._use_temp_zoom = True
            self._temp_zoom_center_provider = temp_center_provider
            self._temp_zoom_tick_count = 0
            self._temp_zoom_delay = delay
            self._temp_zoom_idx = zoom_idx

    def get_zoom(self, ignore_temp_zoom=False):
        base_zoom = _ZOOM_LEVELS[self._base_zoom_idx]
        temp_zoom_prog = self._get_temp_zoom_prog()
        if ignore_temp_zoom or temp_zoom_prog == 0:
            return base_zoom
        else:
            temp_zoom = _ZOOM_LEVELS[self._temp_zoom_idx]
            return util.linear_interp(base_zoom, temp_zoom, temp_zoom_prog)

    def _get_temp_zoom_prog(self):
        if self._temp_zoom_idx is None:
            return 0
        elif self._use_temp_zoom:
            return util.bound(self._temp_zoom_tick_count / self._temp_zoom_delay, 0, 1)
        else:
            return util.bound(1 - self._temp_zoom_tick_count / self._temp_zoom_delay, 0, 1)

    def _get_temp_zoom(self):
        return _ZOOM_LEVELS[self._temp_zoom_idx]

    def _get_temp_zoom_xy(self):
        center = self._temp_zoom_center_provider()
        size = self._get_camera_size_in_world_for_zoom(self._get_temp_zoom())
        return (center[0] - size[0] // 2, center[1] - size[1] // 2)

    def _get_temp_zoom_center(self):
        backup = self.get_camera_center_in_world(ignore_temp_zoom=True)
        if self._temp_zoom_center_provider is None:
            return backup
        else:
            temp_center = self._temp_zoom_center_provider()
            return backup if temp_center is None else temp_center

    def set_zoom(self, zoom_level):
        if zoom_level in _ZOOM_LEVELS:
            self._base_zoom_idx = _ZOOM_LEVELS.index(zoom_level)
        else:
            print("ERROR: invalid zoom level, ignoring request: {}".format(zoom_level))

    def get_camera_pos_in_world(self, ignore_temp_zoom=False):
        base_xy = self._base_camera_xy
        temp_zoom_prog = self._get_temp_zoom_prog()
        if ignore_temp_zoom or temp_zoom_prog == 0:
            return base_xy
        else:
            base_center = self.get_camera_center_in_world(ignore_temp_zoom=True)
            temp_center = self._temp_zoom_center_provider()
            cur_center = util.linear_interp(base_center, temp_center, temp_zoom_prog)
            cur_zoom = self.get_zoom()
            size = self._get_camera_size_in_world_for_zoom(cur_zoom, integer=False)

            return util.round_vec((cur_center[0] - size[0] / 2, cur_center[1] - size[1] / 2))

    def set_camera_pos_in_world(self, xy):
        new_x = xy[0] if xy[0] is not None else self._base_camera_xy[0]
        new_y = xy[1] if xy[1] is not None else self._base_camera_xy[1]
        self._base_camera_xy = (new_x, new_y)

    def set_camera_center_in_world(self, xy):
        size = self.get_camera_size_in_world(ignore_temp_zoom=True)
        new_x = xy[0] - size[0] // 2 if xy[0] is not None else self._base_camera_xy[0]
        new_y = xy[1] - size[1] // 2 if xy[1] is not None else self._base_camera_xy[1]
        self._base_camera_xy = (new_x, new_y)

    def move_camera_in_world(self, dxy):
        cur_pos = self.get_camera_pos_in_world(ignore_temp_zoom=True)
        new_x = cur_pos[0] + dxy[0] if dxy[0] is not None else None
        new_y = cur_pos[1] + dxy[1] if dxy[1] is not None else None
        self.set_camera_pos_in_world((new_x, new_y))

    def get_camera_size_in_world(self, ignore_temp_zoom=False, integer=True):
        zoom = self.get_zoom(ignore_temp_zoom=ignore_temp_zoom)
        return self._get_camera_size_in_world_for_zoom(zoom, integer=integer)

    def _get_camera_size_in_world_for_zoom(self, zoom, integer=True):
        game_size = renderengine.get_instance().get_game_size()
        if integer:
            return (game_size[0] // zoom, game_size[1] // zoom)
        else:
            return (game_size[0] / zoom, game_size[1] / zoom)

    def get_camera_center_in_world(self, ignore_temp_zoom=False):
        base_size = self.get_camera_size_in_world(ignore_temp_zoom=True, integer=True)
        base_xy = self.get_camera_pos_in_world(ignore_temp_zoom=True)
        base_center = (base_xy[0] + base_size[0] // 2, base_xy[1] + base_size[1] // 2)

        temp_zoom_prog = self._get_temp_zoom_prog()
        if ignore_temp_zoom or temp_zoom_prog == 0:
            return base_center
        else:
            return util.round_vec(
                util.linear_interp(base_center, self._temp_zoom_center_provider(), temp_zoom_prog)
            )

    def get_camera_rect_in_world(self, integer=True, expansion=0, ignore_temp_zoom=False):
        xy = self.get_camera_pos_in_world(ignore_temp_zoom=ignore_temp_zoom)
        size = self.get_camera_size_in_world(ignore_temp_zoom=ignore_temp_zoom, integer=integer)
        return [xy[0] - expansion,
                xy[1] - expansion,
                size[0] + expansion * 2,
                size[1] + expansion * 2]

    def _calc_entities_to_render_this_frame(self, inside_rect=None):
        buffer_zone = gs.get_instance().cell_size * 4
        render_zone = self.get_camera_rect_in_world(integer=True, expansion=buffer_zone)
        if inside_rect is not None:
            render_zone = util.get_rect_intersect(render_zone, inside_rect)
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

    def _update_out_of_bounds_blockers(self, camera_bounds, bg_color=colors.PERFECT_BLACK, insets=1):
        fov_rect = self.get_camera_rect_in_world()
        if self._hide_regions_outside_camera_bounds and (fov_rect is not None and camera_bounds is not None):
            """fov_rect
                x1y1---------*---*
                | 0          | 1 |
                *---x2y2-----*   |
                |   | bounds |   |
                |   *-----x3y3---*
                | 3 |          2 |
                *---*---------x4y4
            """
            x1, y1 = fov_rect[0:2]
            x2, y2 = camera_bounds[0:2]
            x3, y3 = x2 + camera_bounds[2], y2 + camera_bounds[3]
            x4, y4 = x1 + fov_rect[2], y1 + fov_rect[3]

            rects = [
                [x1, y1, x3 - x1, y2 - y1],
                [x3, y1, x4 - x3, y3 - y1],
                [x2, y3, x4 - x2, y4 - y3],
                [x1, y2, x2 - x1, y4 - y2]
            ]

            rects = [(r if (r[2] > 0 and r[3] > 0) else None) for r in rects]
        else:
            rects = [None] * 4

        for i in range(0, 4):
            rect = rects[i]
            if rect is not None:
                if insets > 0:
                    rect = util.rect_expand(rect, all_expand=insets)
                if self._out_of_bounds_blockers[i] is None:
                    self._out_of_bounds_blockers[i] = sprites.ImageSprite.new_sprite(spriteref.WORLD_UI_LAYER, depth=100)

                self._out_of_bounds_blockers[i] = self._out_of_bounds_blockers[i].update(
                    new_model=spritesheets.get_white_square_img(),
                    new_x=rect[0],
                    new_y=rect[1],
                    new_color=bg_color,
                    new_raw_size=(rect[2], rect[3]))
            else:
                self._out_of_bounds_blockers[i] = None

    def all_sprites(self):
        for ent in self._entities_to_render:
            if gs.get_instance().debug_render:
                for spr in ent.all_debug_sprites():
                    yield spr
            else:
                for spr in ent.all_sprites():
                    yield spr
        for spr in self._out_of_bounds_blockers:
            yield spr
        for spr in self._grid_line_sprites:
            yield spr

