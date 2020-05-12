
import src.engine.game as game
import src.engine.layers as layers
import src.game.worlds as worlds

import src.game.spriteref as spriteref


class CircuitsGame(game.Game):

    def __init__(self):
        game.Game.__init__(self)
        self._world = None

    def create_sheets(self):
        return []

    def create_layers(self):
        yield layers.ImageLayer(spriteref.BLOCK_LAYER, 0, sort_sprites=True, use_color=True)
        yield layers.ImageLayer(spriteref.ENTITY_LAYER, 5, sort_sprites=True, use_color=True)
        yield layers.PolygonLayer(spriteref.POLYGON_LAYER, 12, sort_sprites=True)

        yield layers.ImageLayer(spriteref.UI_FG_LAYER, 20, sort_sprites=True, use_color=True)
        yield layers.ImageLayer(spriteref.UI_BG_LAYER, 19, sort_sprites=True, use_color=True)

    def update(self):
        if self._world is None:
            self._world = worlds.World.new_test_world()

        self._world.update()

    def all_sprites(self):
        for spr in self._world.all_sprites():
            yield spr
