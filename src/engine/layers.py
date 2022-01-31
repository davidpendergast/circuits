from OpenGL.GL import *

import numpy

import src.engine.sprites as sprites
import src.utils.util as util


def assert_int(val):
    if not isinstance(val, int):
        raise ValueError("value is not an int: {}".format(val))


class _Layer:

    def __init__(self, layer_id, layer_height, sort_sprites=True, use_color=True):
        """
            layer_id: The string identifier for this layer.
            layer_z: The z-depth of this layer, in relation to other layers in the engine. Higher z = on top.
            sort_sprites: Whether the sprites in this layer should be sorted by their depth.
            use_color: Whether this layer should use the color information in its sprites.
        """
        self._layer_id = layer_id
        self._layer_z = layer_height

        self._sort_sprites = sort_sprites
        self._use_color = use_color

        self._offset = (0, 0)
        self._scale = 1

    def get_layer_id(self):
        return self._layer_id

    def set_scale(self, scale):
        self._scale = scale

    def get_scale(self):
        return self._scale

    def set_offset(self, x, y):
        self._offset = (x, y)

    def get_offset(self):
        return self._offset

    def is_sorted(self):
        return self._sort_sprites

    def is_color(self):
        return self._use_color

    def accepts_sprite_type(self, sprite_type):
        raise NotImplementedError()

    def vertex_stride(self):
        raise NotImplementedError()

    def texture_stride(self):
        raise NotImplementedError()

    def index_stride(self):
        raise NotImplementedError()

    def color_stride(self):
        raise NotImplementedError()

    def get_layer_z(self):
        return self._layer_z

    def is_dirty(self):
        raise NotImplementedError()

    def get_num_sprites(self):
        raise NotImplementedError()

    def update(self, sprite_id, last_mod_time):
        raise NotImplementedError()

    def remove(self, sprite_id):
        raise NotImplementedError()

    def rebuild(self, sprite_info_lookup):
        raise NotImplementedError()

    def render(self, engine):
        raise NotImplementedError()

    def __contains__(self, sprite_id):
        raise NotImplementedError()

    def __len__(self):
        return self.get_num_sprites()


class ImageLayer(_Layer):
    """
        Layer for ImageSprites.
    """

    def __init__(self, layer_id, layer_z, sort_sprites=True, use_color=True):
        _Layer.__init__(self, layer_id, layer_z, sort_sprites=sort_sprites, use_color=use_color)

        self.images = []  # ordered list of image ids
        self._image_set = set()  # set of image ids

        self._last_known_last_modified_ticks = {}  # image id -> int

        # these are the pointers the layer passes to gl
        self.vertices = numpy.array([], dtype=float)
        self.tex_coords = numpy.array([], dtype=float)
        self.indices = numpy.array([], dtype=float)
        self.colors = numpy.array([], dtype=float) if use_color else None

        self._dirty_sprites = []
        self._to_remove = []
        self._to_add = []

    def update(self, sprite_id, last_mod_time):
        assert_int(sprite_id)
        if sprite_id in self._image_set:
            if last_mod_time > self._last_known_last_modified_ticks[sprite_id]:
                self._dirty_sprites.append(sprite_id)
        else:
            self._image_set.add(sprite_id)
            self._to_add.append(sprite_id)

        self._last_known_last_modified_ticks[sprite_id] = last_mod_time

    def remove(self, sprite_id):
        assert_int(sprite_id)
        if sprite_id in self._image_set:
            self._image_set.remove(sprite_id)
            self._to_remove.append(sprite_id)
            del self._last_known_last_modified_ticks[sprite_id]

    def is_dirty(self):
        return len(self._dirty_sprites) + len(self._to_add) + len(self._to_remove) > 0

    def accepts_sprite_type(self, sprite_type):
        return sprite_type == sprites.SpriteTypes.IMAGE

    def vertex_stride(self):
        return 4 * 3

    def texture_stride(self):
        return 8

    def index_stride(self):
        return 6

    def color_stride(self):
        return 4 * 3

    def populate_data_arrays(self, sprite_info_lookup):
        n_sprites = len(self.images)

        # need refcheck to be false or else Pycharm's debugger can cause this to fail (due to holding a ref)
        self.vertices.resize(self.vertex_stride() * n_sprites, refcheck=False)
        self.tex_coords.resize(self.texture_stride() * n_sprites, refcheck=False)
        self.indices.resize(self.index_stride() * n_sprites, refcheck=False)
        if self.is_color():
            self.colors.resize(self.color_stride() * n_sprites, refcheck=False)

        # TODO - we only need to iterate over dirty indices here
        # TODO - even better, can we numpyify this whole thing?
        for i in range(0, n_sprites):
            sprite = sprite_info_lookup[self.images[i]].sprite
            sprite.add_urself(
                i,
                self.vertices,
                self.tex_coords,
                self.colors,
                self.indices)

    def rebuild(self, sprite_info_lookup):
        if len(self._to_remove) > 0:
            # this is all here to handle the case where you add and remove a sprite on the same frame
            for sprite_id in self._to_remove:
                if sprite_id in self._image_set:
                    self._image_set.remove(sprite_id)
                if sprite_id in self._last_known_last_modified_ticks:
                    del self._last_known_last_modified_ticks[sprite_id]

            util.remove_all_from_list_in_place(self.images, self._to_remove)
            util.remove_all_from_list_in_place(self._to_add, self._to_remove)
            self._to_remove.clear()

        if len(self._to_add) > 0:
            self.images.extend(self._to_add)
            self._to_add.clear()

        self._dirty_sprites.clear()

        if self.is_sorted():
            self.images.sort(key=lambda x: -sprite_info_lookup[x].sprite.depth())

        self.populate_data_arrays(sprite_info_lookup)

    def render(self, engine):
        if engine.is_opengl():
            # split up like this to make it easier to find performance bottlenecks
            self.set_client_states(True, engine)
            self._set_uniforms(engine)
            self._pass_attributes(engine)
            self._draw_elements(engine)
            self.set_client_states(False, engine)
        else:
            # compatibility mode
            engine.set_camera_2d(self.get_offset(), scale=[self.get_scale()] * 2)
            for i in range(0, len(self.images)):
                sprite = engine.sprite_info_lookup[self.images[i]].sprite
                engine.blit_sprite(sprite)

    def _set_uniforms(self, engine):
        engine.set_camera_2d(self.get_offset(), scale=[self.get_scale()] * 2)

    def set_client_states(self, enable, engine):
        engine.set_vertices_enabled(enable)
        engine.set_texture_coords_enabled(enable)
        if self.is_color():
            engine.set_colors_enabled(enable)

    def _pass_attributes(self, engine):
        engine.set_vertices(self.vertices)
        engine.set_texture_coords(self.tex_coords)
        if self.is_color():
            engine.set_colors(self.colors)

    def _draw_elements(self, engine):
        engine.draw_elements(self.indices)

    def __contains__(self, uid):
        return uid in self._image_set

    def get_num_sprites(self):
        return len(self.images)

    def __repr__(self):
        return "{}({}, {}, {}, {})".format(type(self).__name__, self.get_layer_id(), self.get_layer_z(),
                                           self.is_sorted(), self.is_color())


class PolygonLayer(ImageLayer):

    def __init__(self, layer_id, layer_z, sort_sprites=True):
        ImageLayer.__init__(self, layer_id, layer_z, sort_sprites=sort_sprites, use_color=True)

    def accepts_sprite_type(self, sprite_type):
        return sprite_type == sprites.SpriteTypes.TRIANGLE

    def vertex_stride(self):
        return 3 * 3

    def texture_stride(self):
        return 6

    def index_stride(self):
        return 3

    def color_stride(self):
        return 3 * 3

