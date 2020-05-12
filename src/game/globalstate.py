

class GlobalState:

    def __init__(self):
        self.debug_render = True        # draw collision boxes

        self.cell_size = 16             # affects collisions
        self.subpixel_resolution = 10   # affects movement


_INSTANCE = GlobalState()


def set_instance(gstate):
    global _INSTANCE
    _INSTANCE = gstate


def get_instance() -> GlobalState:
    global _INSTANCE
    return _INSTANCE

