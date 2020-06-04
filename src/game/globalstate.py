import src.engine.globaltimer as globaltimer


class GlobalState:

    def __init__(self):
        self.debug_render = True        # draw collision boxes

        self.cell_size = 16             # affects collisions
        self.subpixel_resolution = 10   # affects movement

        self._tick_count = 0

    def tick_count(self):
        return self._tick_count

    def anim_tick(self):
        return self.tick_count() // 4

    def update(self):
        self._tick_count += 1


_INSTANCE = GlobalState()


def set_instance(gstate):
    global _INSTANCE
    _INSTANCE = gstate


def get_instance() -> GlobalState:
    global _INSTANCE
    return _INSTANCE

