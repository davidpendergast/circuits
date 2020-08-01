

class Scene:

    def __init__(self):
        self._manager = None  # SceneManager, gets set by SceneManager when the scene is active

    def get_manager(self):
        return self._manager

    def all_sprites(self):
        raise NotImplementedError()

    def update(self):
        raise NotImplementedError()

    def became_active(self):
        pass

    def about_to_become_inactive(self):
        pass


class SceneManager:

    def __init__(self, cur_scene):
        if cur_scene is None:
            raise ValueError("current scene can't be None")
        self._active_scene = cur_scene

        self._next_scene = None
        self._next_scene_delay = 0

    def set_next_scene(self, scene, delay=0):
        self._next_scene = scene
        self._next_scene_delay = delay

    def get_active_scene(self):
        return self._active_scene

    def all_sprites(self):
        for spr in self.get_active_scene().all_sprites():
            yield spr

    def update(self):
        if self._next_scene is not None:
            if self._next_scene_delay <= 0:
                self._active_scene.about_to_become_inactive()
                self._active_scene._manager = None

                self._next_scene._manager = self
                self._active_scene = self._next_scene
                self._next_scene.became_active()
                self._next_scene = None
                self._next_scene_delay = 0
            else:
                self._next_scene_delay -= 1

        self._active_scene.update()
