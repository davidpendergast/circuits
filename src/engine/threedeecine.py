import src.engine.threedee as threedee
import src.utils.util as util
import math
import traceback


class AnimatedCamera3D(threedee.Camera3D):

    def __init__(self, duration=-1):
        super().__init__()
        self.duration = duration
        self.ticks_active = 0

    def get_duration(self):
        return self.duration

    def get_ticks(self):
        return self.ticks_active

    def is_finished(self):
        return 0 <= self.get_duration() <= self.get_ticks()

    def get_prog(self):
        if self.duration < 0:
            return 0
        else:
            return util.bound(self.ticks_active / self.duration, 0, 1)

    def update(self):
        self.ticks_active += 1

    def get_position(self):
        raise NotImplementedError()

    def get_direction(self):
        raise NotImplementedError()

    def get_fov(self):
        raise NotImplementedError()


class InterpolatingAnimatedCamera(AnimatedCamera3D):

    LINEAR = "LINEAR"
    SINE = "SINE"

    def __init__(self, start_camera, end_camera, duration, interp_mode=None):
        super().__init__(duration=duration)
        self._start = start_camera
        self._end = end_camera
        self._interp_mode = interp_mode if interp_mode is not None else InterpolatingAnimatedCamera.LINEAR

    def is_finished(self):
        return 0 <= self.get_duration() <= self.get_ticks()

    def get_prog(self):
        if self.duration < 0:
            return 0
        else:
            return util.bound(self.ticks_active / self.duration, 0, 1)

    def _get_interped_prog(self):
        prog = self.get_prog()
        if self._interp_mode == InterpolatingAnimatedCamera.SINE:
            prog = math.sin(prog * math.pi / 4)
        return prog

    def get_position(self):
        prog = self._get_interped_prog()
        return util.linear_interp(self._start.get_position(), self._end.get_position(), prog)

    def get_direction(self):
        prog = self._get_interped_prog()
        return util.interpolate_spherical(self._start.get_direction(), self._end.get_direction(), prog)

    def get_fov(self):
        prog = self._get_interped_prog()
        return util.linear_interp(self._start.get_fov(), self._end.get_fov(), prog)


class ExternallyControlledCamera(AnimatedCamera3D):

    def __init__(self, position, direction, fov=lambda t: 45, duration=-1):
        """
        :param position:   t -> (x, y, z)
        :param direction:  t -> (x, y, z)
        :param fov:        t -> degrees
        :param duration:   t -> int
        """
        super().__init__(duration=duration)
        self.position_provider = position
        self.direction_provider = direction
        self.fov_provider = fov

    def get_position(self):
        return self.position_provider(self.ticks_active)

    def get_direction(self):
        return self.direction_provider(self.ticks_active)

    def get_fov(self):
        return self.fov_provider(self.ticks_active)


class CompositeAnimatedCamera(AnimatedCamera3D):

    def __init__(self, cameras):
        total_dur = 0
        for c in cameras:
            if c.get_duration() < 0:
                total_dur = -1
                break
            else:
                total_dur += c.get_duration()
        super().__init__(duration=total_dur)
        self.cameras = cameras
        self.active_idx = 0

    def update(self):
        if self.active_idx < len(self.cameras):
            active_camera = self.cameras[self.active_idx]
            if active_camera.is_finished():
                self.active_idx += 1
            else:
                active_camera.update()
        super().update()

    def get_active_camera(self):
        if self.active_idx < len(self.cameras):
            return self.cameras[self.active_idx]
        else:
            return self.cameras[-1]  # I guess?

    def get_position(self):
        return self.get_active_camera().get_position()

    def get_direction(self):
        return self.get_active_camera().get_direction()

    def get_fov(self):
        return self.get_active_camera().get_direction()


class CinematicSequence3D:

    def __init__(self, name, shots):
        self.name = name
        if isinstance(shots, CinematicShot3D):
            shots = util.listify(shots)
        if isinstance(shots, list) or isinstance(shots, tuple):
            shots = list(shots)
            shots.reverse()
            self.shot_provider = lambda: None if len(shots) == 0 else shots.pop()
        else:
            self.shot_provider = shots
        self.current_shot = self.shot_provider()

    def get_current_shot(self):
        return self.current_shot

    def update(self):
        cur_shot = self.get_current_shot()
        if cur_shot is None:
            return
        elif cur_shot.is_finished():
            cur_shot.destroy()
            cur_shot = self.shot_provider()
            if cur_shot is not None:
                cur_shot.initialize()
            self.current_shot = cur_shot
        else:
            cur_shot.update()

    def is_finished(self):
        return self.get_current_shot() is None

    def all_sprites(self):
        cur_shot = self.get_current_shot()
        if cur_shot is None:
            return []
        else:
            for spr in cur_shot.all_sprites():
                yield spr

    def get_camera(self) -> threedee.Camera3D:
        cur_shot = self.get_current_shot()
        if cur_shot is None:
            return threedee.Camera3D()
        else:
            return cur_shot.get_camera()


class CinematicShot3D:

    def __init__(self, name):
        self.name = name

    def get_name(self):
        return self.name

    def initialize(self):
        raise NotImplementedError()

    def destroy(self):
        pass

    def all_sprites(self):
        raise NotImplementedError()

    def update(self):
        raise NotImplementedError()

    def is_finished(self):
        raise NotImplementedError()

    def get_camera(self) -> threedee.Camera3D:
        raise NotImplementedError()


class SimpleCinematicShot3D(CinematicShot3D):

    def __init__(self, name, duration, camera):
        super().__init__(name)
        self.duration = duration
        self.tick_count = 0
        self.camera = camera
        self.sprite_lookup = []  # list of (sprite_instance, updater)

    def add_sprite(self, spr, updater=lambda x, t: x):
        """
        :param spr: the sprite
        :param updater: lambda (Sprite3D, tick) -> Sprite3D, None (to hide), or False (to delete)
        """
        self.sprite_lookup.append((spr, updater))

    def add_sprites(self, sprites):
        """
        :param sprites: list of (Sprite3D, updater)s or Sprite3Ds
        """
        for spr in sprites:
            if isinstance(spr, tuple):
                self.add_sprite(spr[0], updater=spr[1])
            else:
                self.add_sprite(spr)

    def initialize(self):
        pass

    def update(self):
        self.camera.update()
        all_sprites = [x for x in self.sprite_lookup]
        self.sprite_lookup.clear()
        for spr_and_updater in all_sprites:
            old_spr, updater = spr_and_updater
            try:
                new_spr = updater(old_spr, self.tick_count)

                if new_spr is False:
                    continue  # delete the sprite
                else:
                    self.sprite_lookup.append((new_spr, updater))
            except Exception:
                print("ERROR: failed to update sprite, removing it: {}".format(old_spr))
                traceback.print_exc()
        self.tick_count += 1

    def is_finished(self):
        return self.tick_count >= self.duration

    def get_camera(self):
        return self.camera

    def all_sprites(self):
        for spr_and_updater in self.sprite_lookup:
            spr = spr_and_updater[0]
            if spr is not None:
                yield spr
