import src.engine.globaltimer as globaltimer


class SaveData:

    COMPLETED_LEVELS = "completed_levels"

    def __init__(self, filepath):
        self.filepath = filepath
        self.json_blob = {
            SaveData.COMPLETED_LEVELS: {}  # level_id -> completion time (in ticks)
        }

    def load_from_disk(self) -> 'SaveData':
        # TODO implement
        return self

    def save_to_disk(self, filepath=None):
        pass  # TODO

    def completed_levels(self) -> dict:
        return self.json_blob[SaveData.COMPLETED_LEVELS]


class GlobalState:

    def __init__(self):
        self.debug_render = False        # draw collision boxes
        self.player_type_override = None

        self.cell_size = 16             # affects collisions
        self.subpixel_resolution = 10   # affects movement

        self._tick_count = 0

        self._save_data = SaveData("save_data.txt").load_from_disk()

    def tick_count(self):
        return self._tick_count

    def anim_tick(self):
        return self.tick_count() // 4

    def update(self):
        self._tick_count += 1

    def save_data(self) -> SaveData:
        return self._save_data


_INSTANCE = GlobalState()


def set_instance(gstate):
    global _INSTANCE
    _INSTANCE = gstate


def get_instance() -> GlobalState:
    global _INSTANCE
    return _INSTANCE

