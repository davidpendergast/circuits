import src.engine.scenes as scenes
import src.engine.threedeecine as threedeecine
import src.engine.threedee as threedee
import src.game.spriteref as spriteref
import src.utils.util as util
import src.engine.renderengine as renderengine


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


class CinematicFactory:

    @staticmethod
    def make_cinematic(cine_type):
        if cine_type == CinematicScenes.INTRO:
            return CinematicFactory.make_intro()
        else:
            raise ValueError("unrecognized cine: {}".format(cine_type))

    @staticmethod
    def make_intro() -> threedeecine.CinematicSequence3D:
        ship_sprite = threedee.Sprite3D(spriteref.ThreeDeeModels.SHIP, spriteref.THREEDEE_LAYER)
        ship_sprite.update(new_x=0, new_y=0, new_z=0)

        shot1_dur = 180
        cam_pos_1 = threedee.Camera3D(position=(0, 0, 65))
        cam_pos_2 = threedee.Camera3D(position=util.add(cam_pos_1.get_position(), (10, 0, 0)))
        shot_1_cam = threedeecine.InterpolatingAnimatedCamera(cam_pos_1, cam_pos_2, shot1_dur)
        shot1 = threedeecine.SimpleCinematicShot3D("shot1", shot1_dur, shot_1_cam)
        shot1.add_sprite(ship_sprite)

        shot2_dur = 180
        cam_pos_1 = threedee.Camera3D(position=(35, 0, 0), direction=(-1, 0, 0))
        cam_pos_2 = threedee.Camera3D(position=(75, 0, 0), direction=(-1, 0, 0))
        shot_2_cam = threedeecine.InterpolatingAnimatedCamera(cam_pos_1, cam_pos_2, shot1_dur)
        shot2 = threedeecine.SimpleCinematicShot3D("shot1", shot2_dur, shot_2_cam)
        shot2.add_sprite(ship_sprite)

        return threedeecine.CinematicSequence3D("intro", [shot1, shot2])

