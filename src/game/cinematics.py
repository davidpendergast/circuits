import math
import random
import src.engine.scenes as scenes
import src.engine.threedeecine as threedeecine
import src.engine.threedee as threedee
import src.game.spriteref as spriteref
import src.utils.util as util
import src.engine.renderengine as renderengine
import configs
import src.game.colors as colors


class CinematicScene3D(scenes.Scene):

    def __init__(self, cinematic_sequence: threedeecine.CinematicSequence3D, next_scene_provider):
        super().__init__()
        self.next_scene_provider = next_scene_provider
        self.cine_seq = cinematic_sequence

    def all_sprites(self):
        for spr in self.cine_seq.all_sprites():
            yield spr

    def update(self):
        self.cine_seq.update()

        cam = self.cine_seq.get_camera().get_snapshot()
        renderengine.get_instance().get_layer(spriteref.THREEDEE_LAYER).set_camera(cam)

        if self.cine_seq.is_finished():
            next_scene = self.next_scene_provider()
            self.get_manager().set_next_scene(next_scene)


class CinematicScenes:
    INTRO = "intro"
    MAIN_MENU = "main_menu"


class CinematicFactory:

    @staticmethod
    def make_cinematic(cine_type):
        if cine_type == CinematicScenes.INTRO:
            return CinematicFactory.make_intro(infinite=False)
        elif cine_type == CinematicScenes.MAIN_MENU:
            return CinematicFactory.make_main_menu_scene()
        else:
            raise ValueError("unrecognized cine: {}".format(cine_type))

    @staticmethod
    def make_intro(infinite=True) -> threedeecine.CinematicSequence3D:
        ship_sprite = threedee.Sprite3D(spriteref.ThreeDeeModels.SHIP, spriteref.THREEDEE_LAYER)
        ship_sprite.update(new_x=0, new_y=0, new_z=0)

        i = [0]

        def next_shot():
            if not infinite and i[0] >= 2:
                return None

            i[0] += 1

            if (i[0]-1) % 2 == 0:
                shot1_dur = 180
                cam_pos_1 = threedee.Camera3D(position=(0, 0, 65))
                cam_pos_2 = threedee.Camera3D(position=util.add(cam_pos_1.get_position(), (10, 0, 0)))
                shot_1_cam = threedeecine.InterpolatingAnimatedCamera(cam_pos_1, cam_pos_2, shot1_dur)
                shot1 = threedeecine.SimpleCinematicShot3D("shot1", shot1_dur, shot_1_cam)
                shot1.add_sprite(ship_sprite)
                return shot1
            else:
                shot2_dur = 180
                cam_pos_1 = threedee.Camera3D(position=(35, 0, 0), direction=(-1, 0, 0))
                cam_pos_2 = threedee.Camera3D(position=(75, 0, 0), direction=(-1, 0, 0))
                shot_2_cam = threedeecine.InterpolatingAnimatedCamera(cam_pos_1, cam_pos_2, shot2_dur)
                shot2 = threedeecine.SimpleCinematicShot3D("shot2", shot2_dur, shot_2_cam)
                shot2.add_sprites(ship_sprite)
                return shot2

        return threedeecine.CinematicSequence3D(CinematicScenes.INTRO, next_shot)

    @staticmethod
    def gen_hella_stars(n, dist_range=(12000, 18000), scale_range=(20, 100), opacity_range=(0.2, 0.5)):
        res = []
        color_opts = [colors.PERFECT_WHITE, colors.BLUE, colors.GREEN, colors.TAN, colors.PURPLE]

        for i in range(0, n):
            opacity = opacity_range[0] + (opacity_range[1] - opacity_range[0]) * random.random()
            ident = "small" if random.random() < 0.8 else "large"
            idx = random.randint(0, 999)
            model_2d = spriteref.star_sheet().get_star(idx, ident, opacity)

            dist = random.randint(dist_range[0], dist_range[1])
            scale = random.randint(scale_range[0], scale_range[1])

            base_vec = (0, 0, dist)
            r, theta, phi = util.cartesian_to_spherical(base_vec)
            theta += 3.1415 / 2 * (random.random() - 0.5)
            phi += 3.1415 / 2 * (random.random() - 0.5)
            pos = util.spherical_to_cartesian(r, theta, phi)
            color = random.choice(color_opts)

            new_star = threedee.BillboardSprite3D(spriteref.ThreeDeeModels.from_2d_model(model_2d), spriteref.THREEDEE_LAYER,
                                                  position=pos, scale=(scale, scale, scale),
                                                  vert_billboard=True, horz_billboard=True, color=color)
            res.append(new_star)
        res.sort(key=lambda s: -util.mag(s.position()))
        return res

    @staticmethod
    def make_main_menu_scene() -> threedeecine.CinematicSequence3D:
        ship_sprite = threedee.Sprite3D(spriteref.ThreeDeeModels.SHIP, spriteref.THREEDEE_LAYER)
        ship_sprite.update(new_x=0, new_y=0, new_z=0)

        sun_sprite = threedee.BillboardSprite3D(spriteref.ThreeDeeModels.SUN_FLAT, spriteref.THREEDEE_LAYER,
                                                position=(0, 0, 10000), scale=(1000, 1000, 1000),
                                                vert_billboard=True, horz_billboard=True)

        all_stars = CinematicFactory.gen_hella_stars(50)

        all_sprites = all_stars + [ship_sprite, sun_sprite]

        y = lambda t: 2 + 1 * math.cos(t * 0.0025 * configs.target_fps / 60)
        cam_center = lambda t: (5, y(t), -25)
        cam_radius = 2
        cam_speed = 0.005 * configs.target_fps / 60  # whatever

        def cam_position(t):
            return util.add(cam_center(t), (cam_radius * math.cos(t * cam_speed), 0, cam_radius * math.sin(t * cam_speed)))
        def cam_direction(t):
            target = (0, y(t), 10)  # a little ahead of the ship's position, with some vertical offset
            return util.set_length(util.sub(target, cam_position(t)), 1)  # point at ship

        camera = threedeecine.ExternallyControlledCamera(cam_position, cam_direction, fov=lambda t: 20)

        shot = threedeecine.SimpleCinematicShot3D("shot2", float('inf'), camera)
        shot.add_sprites(all_sprites)

        return threedeecine.CinematicSequence3D(CinematicScenes.MAIN_MENU, shot)
