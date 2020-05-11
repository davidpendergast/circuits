import pygame
import math

import src.engine.game as game
import src.engine.globaltimer as globaltimer
import src.engine.renderengine as renderengine
import src.engine.inputs as inputs
import src.engine.sprites as sprites
import src.engine.spritesheets as spritesheets
import src.engine.layers as layers
from src.utils.util import Utils


class DemoSheet(spritesheets.SpriteSheet):

    def __init__(self):
        spritesheets.SpriteSheet.__init__(self, "demo_sheet", "assets/assets.png")

        self.player_models = []
        self.tv_models = []
        self.floor_model = None
        self.wall_model = None
        self.shadow_model = None

        self.border_models = []

        self.all_models = []

    def draw_to_atlas(self, atlas, sheet, start_pos=(0, 0)):
        super().draw_to_atlas(atlas, sheet, start_pos=start_pos)

        self.player_models = [sprites.ImageModel(0 + 16 * i, 0, 16, 32, offset=start_pos) for i in range(0, 2)]
        self.tv_models = [sprites.ImageModel(32 + 16 * i, 0, 16, 32, offset=start_pos) for i in range(0, 2)]
        self.floor_model = sprites.ImageModel(64, 16, 16, 16, offset=start_pos)
        self.wall_model = sprites.ImageModel(80, 16, 16, 16, offset=start_pos)
        self.shadow_model = sprites.ImageModel(64, 0, 16, 16, offset=start_pos)

        self.border_models = []
        for y in range(0, 3):
            for x in range(0, 3):
                self.border_models.append(sprites.ImageModel(96 + x * 8, 8 + y * 8, 8, 8, offset=start_pos))

        self.all_models = [self.floor_model, self.wall_model, self.shadow_model]
        self.all_models.extend(self.player_models)
        self.all_models.extend(self.tv_models)
        self.all_models.extend(self.border_models)


class DemoGame(game.Game):

    FLOOR_LAYER = "FLOORS"
    SHADOW_LAYER = "SHADOWS"
    WALL_LAYER = "WALLS"
    ENTITY_LAYER = "ENTITIES"
    POLYGON_LAYER = "POLYGONS"
    UI_FG_LAYER = "UI_FG"
    UI_BG_LAYER = "UI_BG"

    world_layer_ids = [ENTITY_LAYER, SHADOW_LAYER, WALL_LAYER, FLOOR_LAYER, POLYGON_LAYER]
    ui_layer_ids = [UI_BG_LAYER, UI_FG_LAYER]

    cell_size = 32

    demo_sheet = DemoSheet()

    def __init__(self):
        game.Game.__init__(self)

        self.camera_xy = (0, 0)

        self.floor_positions = [(0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (2, 2)]
        self.floor_sprites = []

        self.wall_positions = [(0, 0), (1, 0), (2, 0)]
        self.wall_sprites = []

        self.entity_positions = [(0.5 * DemoGame.cell_size, 2.5 * DemoGame.cell_size),
                                 (2.5 * DemoGame.cell_size, 1.5 * DemoGame.cell_size)]
        self.entity_sprites = []

        self.shadow_sprites = []

        self.triangle_center = (-32, 12)
        self.triangle_length = 20
        self.triangle_angle = 0
        self.triangle_color = (0, 0, 0)

        self.triangle_sprite = None

        self.cube_center = (-72, 80)
        self.cube_length = 40
        self.cube_angle = 0
        self.cube_color = (0, 0, 0)
        self.cube_line_thickness = 1

        self.cube_line_sprites = []

        self.fps_text_sprite = None
        self.title_text_sprite = None

        self.text_box_rect = [0, 0, 0, 0]
        self.text_box_sprite = None
        self.text_box_text_sprite = None

    def all_sprites(self):
        for spr in self.floor_sprites:
            yield spr
        for spr in self.wall_sprites:
            yield spr
        for spr in self.entity_sprites:
            yield spr
        for spr in self.shadow_sprites:
            yield spr

        yield self.triangle_sprite

        for spr in self.cube_line_sprites:
            yield spr

        yield self.fps_text_sprite
        yield self.title_text_sprite

        yield self.text_box_sprite
        yield self.text_box_text_sprite

    def create_sheets(self):
        yield DemoGame.demo_sheet

    def create_layers(self):
        COLOR = True
        SORTS = True
        yield layers.ImageLayer(DemoGame.FLOOR_LAYER, 0, False, COLOR)
        yield layers.ImageLayer(DemoGame.SHADOW_LAYER, 5, False, COLOR)
        yield layers.ImageLayer(DemoGame.WALL_LAYER, 10, False, COLOR)
        yield layers.PolygonLayer(DemoGame.POLYGON_LAYER, 12, SORTS)
        yield layers.ImageLayer(DemoGame.ENTITY_LAYER, 15, SORTS, COLOR)

        yield layers.ImageLayer(DemoGame.UI_FG_LAYER, 20, SORTS, COLOR)
        yield layers.ImageLayer(DemoGame.UI_BG_LAYER, 19, SORTS, COLOR)
        
    def update(self):
        if len(self.entity_sprites) == 0:
            self.entity_sprites.append(sprites.ImageSprite.new_sprite(DemoGame.ENTITY_LAYER, scale=1))  # player
            self.entity_sprites.append(sprites.ImageSprite.new_sprite(DemoGame.ENTITY_LAYER, scale=1))  # tv

        if len(self.wall_sprites) == 0:
            for pos in self.wall_positions:
                new_sprite = sprites.ImageSprite(DemoGame.demo_sheet.wall_model,
                                                 pos[0] * DemoGame.cell_size,
                                                 pos[1] * DemoGame.cell_size,
                                                 DemoGame.WALL_LAYER, scale=2)
                self.wall_sprites.append(new_sprite)

        if len(self.floor_sprites) == 0:
            for pos in self.floor_positions:
                new_sprite = sprites.ImageSprite(DemoGame.demo_sheet.floor_model,
                                                 pos[0] * DemoGame.cell_size,
                                                 pos[1] * DemoGame.cell_size,
                                                 DemoGame.FLOOR_LAYER, scale=2)
                self.floor_sprites.append(new_sprite)

        if len(self.shadow_sprites) == 0:
            for _ in self.entity_sprites:
                self.shadow_sprites.append(sprites.ImageSprite(DemoGame.demo_sheet.shadow_model, 0, 0,
                                                               DemoGame.SHADOW_LAYER, scale=1))

        if self.triangle_sprite is None:
            self.triangle_sprite = sprites.TriangleSprite(DemoGame.POLYGON_LAYER, color=(0, 0, 0))

        while len(self.cube_line_sprites) < 12:
            self.cube_line_sprites.append(sprites.LineSprite(DemoGame.POLYGON_LAYER, thickness=self.cube_line_thickness))

        anim_tick = globaltimer.tick_count() // 16

        speed = 2
        dx = 0
        new_xflip = None
        if inputs.get_instance().is_held([pygame.K_a, pygame.K_LEFT]):
            dx -= speed
            new_xflip = False
        elif inputs.get_instance().is_held([pygame.K_d, pygame.K_RIGHT]):
            dx += speed
            new_xflip = True

        dy = 0
        if inputs.get_instance().is_held([pygame.K_w, pygame.K_UP]):
            dy -= speed
        elif inputs.get_instance().is_held([pygame.K_s, pygame.K_DOWN]):
            dy += speed

        player_x = self.entity_positions[0][0] + dx
        new_y = self.entity_positions[0][1] + dy
        player_y = max(new_y, int(1.1 * DemoGame.cell_size))  # collision with walls~

        self.entity_positions[0] = (player_x, player_y)
        new_model = DemoGame.demo_sheet.player_models[anim_tick % len(DemoGame.demo_sheet.player_models)]
        player_sprite = self.entity_sprites[0]
        player_scale = player_sprite.scale()
        self.entity_sprites[0] = player_sprite.update(new_model=new_model,
                                                      new_x=player_x - new_model.width() * player_scale // 2,
                                                      new_y=player_y - new_model.height() * player_scale,
                                                      new_xflip=new_xflip, new_depth=-player_y)

        tv_model = DemoGame.demo_sheet.tv_models[(anim_tick // 2) % len(DemoGame.demo_sheet.tv_models)]
        tv_x = self.entity_positions[1][0]
        tv_y = self.entity_positions[1][1]
        tv_xflip = player_x > tv_x  # turn to face player
        tv_sprite = self.entity_sprites[1]
        tv_scale = tv_sprite.scale()

        self.entity_sprites[1] = tv_sprite.update(new_model=tv_model,
                                                  new_x=tv_x - tv_model.width() * tv_scale // 2,
                                                  new_y=tv_y - tv_model.height() * tv_scale,
                                                  new_xflip=tv_xflip, new_depth=-tv_y)

        for i in range(0, len(self.entity_positions)):
            xy = self.entity_positions[i]
            shadow_sprite = self.shadow_sprites[i]
            shadow_model = self.demo_sheet.shadow_model
            shadow_x = xy[0] - shadow_sprite.scale() * shadow_model.width() // 2
            shadow_y = xy[1] - shadow_sprite.scale() * shadow_model.height() // 2
            self.shadow_sprites[i] = shadow_sprite.update(new_model=shadow_model,
                                                          new_x=shadow_x, new_y=shadow_y)

        min_rot_speed = 0.3
        max_rot_speed = 4

        if self.triangle_sprite is not None:
            tri_center = self.triangle_center
            tri_angle = self.triangle_angle * 2 * 3.141529 / 360
            tri_length = self.triangle_length

            p1 = Utils.add(tri_center, Utils.rotate((tri_length, 0), tri_angle))
            p2 = Utils.add(tri_center, Utils.rotate((tri_length, 0), tri_angle + 3.141529 * 2 / 3))
            p3 = Utils.add(tri_center, Utils.rotate((tri_length, 0), tri_angle + 3.141529 * 4 / 3))

            self.triangle_sprite = self.triangle_sprite.update(new_points=(p1, p2, p3))

            player_dist = Utils.dist(self.entity_positions[0], tri_center)
            if player_dist > 100:
                rot_speed = min_rot_speed
            else:
                rot_speed = Utils.linear_interp(min_rot_speed, max_rot_speed, (100 - player_dist) / 100)

            self.triangle_angle += rot_speed

        text_inset = 4

        title_text = "Demo Scene"
        if self.title_text_sprite is None:
            self.title_text_sprite = sprites.TextSprite(DemoGame.UI_FG_LAYER, 0, text_inset, title_text)

        title_text_width = self.title_text_sprite.get_size()[0]
        title_text_x = renderengine.get_instance().get_game_size()[0] - title_text_width - text_inset
        self.title_text_sprite = self.title_text_sprite.update(new_x=title_text_x)

        if self.fps_text_sprite is None:
            self.fps_text_sprite = sprites.TextSprite(DemoGame.UI_FG_LAYER, text_inset, text_inset, "FPS: 0")
        fps_text = "FPS: {}".format(int(globaltimer.get_fps()))
        self.fps_text_sprite = self.fps_text_sprite.update(new_x=text_inset, new_y=text_inset,
                                                           new_text=fps_text)

        player_to_tv_dist = Utils.dist(self.entity_positions[0], self.entity_positions[1])
        info_text = "There's something wrong with the TV. Maybe it's better this way." if player_to_tv_dist < 32 else None
        info_text_w = 400 - 32
        info_text_h = 48
        info_text_rect = [renderengine.get_instance().get_game_size()[0] // 2 - info_text_w // 2,
                          renderengine.get_instance().get_game_size()[1] - info_text_h - 16,
                          info_text_w, info_text_h]
        if info_text is None:
            self.text_box_text_sprite = None
            self.text_box_sprite = None
        else:
            wrapped_text = "\n".join(sprites.TextSprite.wrap_text_to_fit(info_text, info_text_rect[2]))
            if self.text_box_text_sprite is None:
                self.text_box_text_sprite = sprites.TextSprite(DemoGame.UI_FG_LAYER, 0, 0, wrapped_text)
            self.text_box_text_sprite = self.text_box_text_sprite.update(new_x=info_text_rect[0],
                                                                         new_y=info_text_rect[1],
                                                                         new_text=wrapped_text)
            if self.text_box_sprite is None:
                self.text_box_sprite = sprites.BorderBoxSprite(DemoGame.UI_BG_LAYER, info_text_rect,
                                                               all_borders=DemoGame.demo_sheet.border_models)
            self.text_box_sprite = self.text_box_sprite.update(new_rect=info_text_rect, new_scale=2)

        if len(self.cube_line_sprites) == 12:
            cube_center = self.cube_center
            cube_angle = self.cube_angle * 2 * 3.141529 / 360
            cube_length = self.cube_length
            cube_color = self.cube_color

            cube_top_pts = []
            cube_btm_pts = []

            for i in range(0, 4):
                dx = cube_length / 2 * math.cos(cube_angle + i * 3.141529 / 2)
                dy = cube_length / 2 * math.sin(cube_angle + i * 3.141529 / 2) / 2  # foreshortened in the y-axis
                cube_btm_pts.append(Utils.add(cube_center, (dx, dy)))
                cube_top_pts.append(Utils.add(cube_center, (dx, dy - cube_length)))

            for i in range(0, 12):
                if i < 4:  # bottom lines
                    p1 = cube_btm_pts[i % 4]
                    p2 = cube_btm_pts[(i + 1) % 4]
                elif i < 8:  # top lines
                    p1 = cube_top_pts[i % 4]
                    p2 = cube_top_pts[(i + 1) % 4]
                else:  # bottom to top lines
                    p1 = cube_btm_pts[i % 4]
                    p2 = cube_top_pts[i % 4]

                self.cube_line_sprites[i].update(new_p1=p1, new_p2=p2, new_color=cube_color)

            player_dist = Utils.dist(self.entity_positions[0], cube_center)
            if player_dist > 100:
                rotation_speed = min_rot_speed
            else:
                rotation_speed = Utils.linear_interp(min_rot_speed, max_rot_speed, (100 - player_dist) / 100)

            self.cube_angle += rotation_speed

        # setting layer positions
        camera_x = player_x - renderengine.get_instance().get_game_size()[0] // 2
        camera_y = player_y - renderengine.get_instance().get_game_size()[1] // 2
        for layer_id in DemoGame.world_layer_ids:
            renderengine.get_instance().set_layer_offset(layer_id, camera_x, camera_y)
