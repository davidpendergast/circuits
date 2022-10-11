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


class ImageDataArray:

    def __init__(self, parent: 'ImageLayer', min_capacity=256):
        self._parent_layer = parent
        self._array_capacity = 0
        self._min_capacity = min_capacity
        self._size = 0

        self.vertices = numpy.array([], dtype=float)
        self.tex_coords = numpy.array([], dtype=float)
        self.indices = numpy.array([], dtype=float)
        self.colors = numpy.array([], dtype=float) if parent.is_color() else None

    def __len__(self):
        return self._size

    def _ensure_capacity(self, n):
        self._size = n

        cur_capacity = self._array_capacity
        capacity = util.next_power_of_2(n)

        if capacity == cur_capacity:
            return  # already correct size
        elif capacity <= self._min_capacity and cur_capacity == self._min_capacity:
            return  # not allowed to shrink smaller
        if cur_capacity // 4 < capacity < cur_capacity:
            # don't shrink until we're only using 25% of array (want to prevent repeatedly
            # shrinking & growing if we're near the border of two thresholds).
            return

        # pycharm's debugger likes to hold refs to these in debug mode~
        self.vertices.resize(capacity * self._parent_layer.vertex_stride(), refcheck=False)
        self.tex_coords.resize(capacity * self._parent_layer.texture_stride(), refcheck=False)
        self.indices.resize(capacity * self._parent_layer.index_stride(), refcheck=False)
        if self.colors is not None:
            self.colors.resize(capacity * self._parent_layer.color_stride(), refcheck=False)

        self._array_capacity = capacity

    def update(self, spr_list):
        self._size = len(spr_list)
        self._ensure_capacity(self._size)
        for i, spr in enumerate(spr_list):
            spr.add_urself(
                i,
                self.vertices,
                self.tex_coords,
                self.colors,
                self.indices)

    def pass_attributes_and_draw(self, engine):
        engine.set_vertices(self.vertices)
        engine.set_texture_coords(self.tex_coords)
        if self.colors is not None:
            engine.set_colors(self.colors)
        engine.draw_elements(self.indices, n=self._size * self._parent_layer.index_stride())


class ImageLayer(_Layer):
    """
        Layer for ImageSprites.
    """

    def __init__(self, layer_id, layer_z, sort_sprites=True, use_color=True):
        _Layer.__init__(self, layer_id, layer_z, sort_sprites=sort_sprites, use_color=use_color)

        self.images = []  # ordered list of image ids
        self._image_set = set()  # set of image ids

        self._last_known_last_modified_ticks = {}  # image id -> int

        self.opaque_data_arrays = ImageDataArray(self)
        self.trans_data_arrays = ImageDataArray(self)

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
        opaques, trans = util.partition((sprite_info_lookup[idx].sprite for idx in self.images),
                                        lambda spr: not spr.is_translucent())
        # order doesn't matter for opaque sprites
        self.opaque_data_arrays.update(opaques)

        # translucent sprites must be sorted for proper rendering
        trans.sort(key=lambda spr: -spr.depth())
        self.trans_data_arrays.update(trans)

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
            import random
            random.shuffle(self.images)

        self.populate_data_arrays(sprite_info_lookup)

    def render(self, engine):
        if engine.is_opengl():
            # split up like this to make it easier to find performance bottlenecks
            self.set_client_states(True, engine)
            self._set_uniforms(engine)

            self.opaque_data_arrays.pass_attributes_and_draw(engine)

            engine.set_depth_write_enabled(False)
            self.trans_data_arrays.pass_attributes_and_draw(engine)
            engine.set_depth_write_enabled(True)

            self.set_client_states(False, engine)
        else:
            # compatibility mode
            engine.set_camera_2d(self.get_offset(), scale=[self.get_scale()] * 2)

            all_sprites = [engine.sprite_info_lookup[spr_id].sprite for spr_id in self.images]
            all_sprites.sort(key=lambda spr: -spr.depth())
            for spr in all_sprites:
                engine.blit_sprite(spr)

    def _set_uniforms(self, engine):
        engine.set_camera_2d(self.get_offset(), scale=[self.get_scale()] * 2)

    def set_client_states(self, enable, engine):
        engine.set_vertices_enabled(enable)
        engine.set_texture_coords_enabled(enable)
        if self.is_color():
            engine.set_colors_enabled(enable)
        engine.set_alpha_test_enabled(enable)
        engine.set_depth_test_enabled(enable)

    def _draw_elements(self, engine):
        engine.draw_elements(self.indices, n=self.get_num_sprites() * self.index_stride())

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

