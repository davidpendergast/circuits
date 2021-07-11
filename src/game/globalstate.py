import src.engine.globaltimer as globaltimer


class SaveAndLoadJsonBlob:

    def __init__(self, filepath):
        self.filepath = filepath
        self.json_blob = {}
        self.set_defaults()

    def load_from_disk(self) -> 'SaveAndLoadJsonBlob':
        # TODO implement
        return self

    def save_to_disk(self, filepath=None):
        pass  # TODO

    def set_defaults(self):
        pass


class SaveData(SaveAndLoadJsonBlob):

    COMPLETED_LEVELS = "completed_levels"

    def __init__(self, filepath):
        super().__init__(filepath)

    def set_defaults(self):
        self.json_blob[SaveData.COMPLETED_LEVELS] = {}  # level_id -> completion time (in ticks)

    def completed_levels(self) -> dict:
        return self.json_blob[SaveData.COMPLETED_LEVELS]


class Settings(SaveAndLoadJsonBlob):

    SHOW_LIGHTING = "show_lighting"

    def __init__(self, filepath):
        super().__init__(filepath)

    def set_defaults(self):
        self.json_blob[Settings.SHOW_LIGHTING] = True

    def get(self, attrib):
        if attrib in self.json_blob:
            return self.json_blob[attrib]
        else:
            return None

    def set(self, attrib, val):
        self.json_blob[attrib] = val


class GlobalState:

    def __init__(self):
        self.debug_render = False        # draw collision boxes
        self.player_type_override = None

        self.cell_size = 16             # affects collisions
        self.subpixel_resolution = 10   # affects movement

        self._tick_count = 0

        self._save_data = SaveData("save_data.txt").load_from_disk()
        self._settings = Settings("settings.txt").load_from_disk()

        self._should_quit_for_real = False

    def tick_count(self):
        return self._tick_count

    def anim_tick(self):
        return self.tick_count() // 4

    def update(self):
        self._tick_count += 1

    def save_data(self) -> SaveData:
        return self._save_data

    def settings(self) -> Settings:
        return self._settings

    def quit_game_for_real(self):
        self._should_quit_for_real = True

    def should_exit(self):
        return self._should_quit_for_real


_INSTANCE = GlobalState()


def set_instance(gstate):
    global _INSTANCE
    _INSTANCE = gstate


def get_instance() -> GlobalState:
    global _INSTANCE
    return _INSTANCE

