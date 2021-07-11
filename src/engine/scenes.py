import configs


_INSTANCE = None


def create_instance(cur_scene) -> 'SceneManager':
    global _INSTANCE
    _INSTANCE = SceneManager(cur_scene)
    return _INSTANCE


def get_instance() -> 'SceneManager':
    return _INSTANCE


class Scene:

    def __init__(self):
        pass

    def get_manager(self) -> 'SceneManager':
        return get_instance()

    def is_active(self):
        return self.get_manager().get_active_scene() == self

    def jump_to_scene(self, next_scene):
        self.get_manager().set_next_scene(next_scene)

    def all_sprites(self):
        raise NotImplementedError()

    def update_sprites(self):
        """Creates and/or updates the sprites in the scene.
            This method is optional and intended for scenes that want to implement a pause mode (where
            logical updates stop but sprite updates (e.g. animations) continue). Scenes that don't require a pause
            function may instead update their sprites in update(). Under *no* circumstances should update() call this
            method (if update() calls this method, it will be called twice per frame).
        """
        pass

    def update(self):
        """Performs the "logic update" for the scene."""
        raise NotImplementedError()

    def became_active(self):
        pass

    def about_to_become_inactive(self):
        pass

    def get_clear_color(self):
        return configs.clear_color


class SceneManager:

    def __init__(self, cur_scene):
        if cur_scene is None:
            raise ValueError("current scene can't be None")
        cur_scene._manager = self
        self._active_scene = cur_scene

        self._next_scene = None
        self._next_scene_delay = 0

    def set_next_scene(self, scene, delay=0):
        self._next_scene = scene
        self._next_scene_delay = delay

    def get_active_scene(self) -> Scene:
        return self._active_scene

    def get_clear_color(self):
        return self.get_active_scene().get_clear_color()

    def all_sprites(self):
        for spr in self.get_active_scene().all_sprites():
            yield spr

    def update(self):
        if self._next_scene is not None:
            if self._next_scene_delay <= 0:
                self._active_scene.about_to_become_inactive()
                self._active_scene = self._next_scene
                self._next_scene.became_active()
                self._next_scene = None
                self._next_scene_delay = 0
            else:
                self._next_scene_delay -= 1

        self._active_scene.update()
        self._active_scene.update_sprites()

