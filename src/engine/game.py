

class Game:
    """The parent class for all games.
    """

    def __init__(self):
        pass

    def create_sheets(self):
        raise NotImplementedError()

    def create_layers(self):
        raise NotImplementedError()

    def update(self):
        raise NotImplementedError()

    def all_sprites(self):
        raise NotImplementedError()
