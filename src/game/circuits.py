
import pygame

import src.engine.game as game
import src.engine.layers as layers
import src.engine.keybinds as keybinds

import src.game.worlds as worlds
import src.game.globalstate as gs
import src.game.const as const

import src.game.spriteref as spriteref


class CircuitsGame(game.Game):

    def __init__(self):
        game.Game.__init__(self)
        self._world = None

    def initialize(self):
        keybinds.get_instance().set_binding(const.MOVE_LEFT, [pygame.K_LEFT, pygame.K_a])
        keybinds.get_instance().set_binding(const.MOVE_RIGHT, [pygame.K_RIGHT, pygame.K_d])
        keybinds.get_instance().set_binding(const.JUMP, [pygame.K_UP, pygame.K_w, pygame.K_SPACE])

        self._world = worlds.World.new_test_world()

    def get_sheets(self):
        return []

    def get_layers(self):
        yield layers.ImageLayer(spriteref.BLOCK_LAYER, 0, sort_sprites=True, use_color=True)
        yield layers.ImageLayer(spriteref.ENTITY_LAYER, 5, sort_sprites=True, use_color=True)
        yield layers.PolygonLayer(spriteref.POLYGON_LAYER, 12, sort_sprites=True)

        yield layers.ImageLayer(spriteref.UI_FG_LAYER, 20, sort_sprites=True, use_color=True)
        yield layers.ImageLayer(spriteref.UI_BG_LAYER, 19, sort_sprites=True, use_color=True)

    def update(self):
        self._world.update()

    def all_sprites(self):
        if gs.get_instance().debug_render:
            for spr in self._world.all_debug_sprites():
                yield spr
        else:
            for spr in self._world.all_sprites():
                yield spr
