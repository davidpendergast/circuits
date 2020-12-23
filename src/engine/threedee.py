import pywavefront

import src.engine.layers as layers
import src.engine.sprites as sprites


class Texture3DLayer(layers._Layer):

    def __init__(self, layer_id, layer_depth):
        super().__init__(layer_id, layer_depth)
        self._sprite_set = set()  # set of image ids

    def accepts_sprite_type(self, sprite_type):
        return sprite_type == sprites.SpriteTypes.THREE_DEE

    def vertex_stride(self):
        pass

    def texture_stride(self):
        pass

    def index_stride(self):
        pass

    def color_stride(self):
        pass

    def is_dirty(self):
        pass

    def get_num_sprites(self):
        return len(self._sprite_set)

    def update(self, sprite_id, last_mod_time):
        pass

    def remove(self, sprite_id):
        pass

    def rebuild(self, sprite_info_lookup):
        pass

    def render(self, engine):
        pass

    def __contains__(self, sprite_id):
        return sprite_id in self._sprite_set


class Sprite3D(sprites._Sprite):
    def __init__(self, obj, layer_id):
        sprites._Sprite.__init__(self, sprites.SpriteTypes.THREE_DEE, layer_id)
        self.obj = obj


def load_obj(filepath, layer_id) -> Sprite3D:
    obj = pywavefront.Wavefront(filepath)
    return Sprite3D(obj, layer_id)
