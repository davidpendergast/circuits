import configs


class Game:
    """The parent class for all games.
    """

    def __init__(self):
        pass

    def initialize(self):
        pass

    def get_sheets(self):
        raise NotImplementedError()

    def get_layers(self):
        raise NotImplementedError()

    def update(self):
        raise NotImplementedError()

    def all_sprites(self):
        raise NotImplementedError()

    def get_clear_color(self):
        return configs.clear_color
