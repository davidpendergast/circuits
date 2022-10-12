from OpenGL.GL import *

import numpy

import src.engine.sprites as sprites
import src.utils.util as util


def assert_int(val):
    if not isinstance(val, int):
        raise ValueError("value is not an int: {}".format(val))


class _Layer:

    def __init__(self, layer_id, layer_height):
        """
            layer_id: The string identifier for this layer.
            layer_z: The z-depth of this layer, in relation to other layers in the engine. Higher z = on top.
        """
        self._layer_id = layer_id
        self._layer_z = layer_height

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
        self.colors = numpy.array([], dtype=float)

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
        self.colors.resize(capacity * self._parent_layer.color_stride(), refcheck=False)

        self._array_capacity = capacity

    def update(self, spr_list, start_idx=0):
        self._size = len(spr_list)
        self._ensure_capacity(self._size)
        for i, spr in enumerate(spr_list[start_idx:]):
            spr.add_urself(
                i + start_idx,
                self.vertices,
                self.tex_coords,
                self.colors,
                self.indices)

    def pass_attributes_and_draw(self, engine):
        engine.set_vertices(self.vertices)
        engine.set_texture_coords(self.tex_coords)
        engine.set_colors(self.colors)
        engine.draw_elements(self.indices, n=self._size * self._parent_layer.index_stride())


class ImageLayer(_Layer):
    """
        Layer for ImageSprites.
    """

    def __init__(self, layer_id, layer_z):
        _Layer.__init__(self, layer_id, layer_z)

        self.opaque_images = []
        self.trans_images = []
        self._id_to_idx = {}

        self._last_known_last_modified_ticks = {}  # image id -> int

        self.opaque_data_arrays = ImageDataArray(self)
        self.trans_data_arrays = ImageDataArray(self)

        self._first_dirty_idx = 0
        self._dirty_sprites = set()
        self._to_remove = set()
        self._to_add = set()

    def update(self, sprite_id, last_mod_time):
        assert_int(sprite_id)
        if sprite_id in self._id_to_idx:
            if last_mod_time > self._last_known_last_modified_ticks[sprite_id]:
                self._dirty_sprites.add(sprite_id)

                opaque_idx = self._id_to_idx[sprite_id]
                if opaque_idx >= 0:
                    self._first_dirty_idx = min(self._first_dirty_idx, opaque_idx)
        else:
            self._id_to_idx[sprite_id] = -1
            self._to_add.add(sprite_id)

        self._last_known_last_modified_ticks[sprite_id] = last_mod_time

    def remove(self, sprite_id):
        assert_int(sprite_id)
        if sprite_id in self._id_to_idx:
            del self._id_to_idx[sprite_id]
            self._to_remove.add(sprite_id)
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

    def populate_data_arrays(self, opaque_ids, translucent_ids, sprite_info_lookup, first_dirty_opaque_idx=0):
        # order doesn't matter for opaque sprites
        opaques = [sprite_info_lookup[spr_id].sprite for spr_id in opaque_ids]
        self.opaque_data_arrays.update(opaques, start_idx=first_dirty_opaque_idx)

        # translucent sprites should already be sorted (necessary for proper rendering)
        trans = [sprite_info_lookup[spr_id].sprite for spr_id in translucent_ids]
        self.trans_data_arrays.update(trans)

    def rebuild(self, sprite_info_lookup):
        first_dirty_idx = self._first_dirty_idx
        if len(self._to_remove) > 0:
            for sprite_id in self._to_remove:
                if sprite_id in self._id_to_idx:
                    del self._id_to_idx[sprite_id]
                if sprite_id in self._last_known_last_modified_ticks:
                    del self._last_known_last_modified_ticks[sprite_id]

            self._to_add.difference_update(self._to_remove)
            util.remove_all_from_list_in_place(self.trans_images, self._to_remove)

            rm_idx = util.remove_all_from_list_in_place(self.opaque_images, self._to_remove)
            if rm_idx >= 0:
                first_dirty_idx = min(rm_idx, first_dirty_idx)
            self._to_remove.clear()

        new_opaque_sprites = []
        for spr_id in self._to_add:
            if sprite_info_lookup[spr_id].sprite.is_translucent():
                self.trans_images.append(spr_id)
            else:
                new_opaque_sprites.append(spr_id)
        self._to_add.clear()

        super_clean_sprites = self.opaque_images[0:first_dirty_idx]
        dirty_opaque_sprites = []
        clean_opaque_sprites = []
        for i in range(first_dirty_idx, len(self.opaque_images)):
            spr_id = self.opaque_images[i]
            if spr_id not in self._dirty_sprites:
                clean_opaque_sprites.append(spr_id)
            elif sprite_info_lookup[spr_id].sprite.is_translucent():
                self._id_to_idx[spr_id] = -1
                self.trans_images.append(spr_id)  # opaque sprite became translucent
            else:
                dirty_opaque_sprites.append(spr_id)
        self._dirty_sprites.clear()

        # This is the point of all the convoluted logic above. We essentially want the static (aka 'super clean')
        # sprites to percolate towards the beginning of the list so that we can skip over them when updating the
        # data arrays. This way large number of static sprites can be kept in layers almost for free.
        self.opaque_images = super_clean_sprites + clean_opaque_sprites + dirty_opaque_sprites + new_opaque_sprites
        self._first_dirty_idx = len(self.opaque_images)

        self.trans_images.sort(key=lambda x: -sprite_info_lookup[x].sprite.depth())

        for idx in range(len(super_clean_sprites), len(self.opaque_images)):
            self._id_to_idx[self.opaque_images[idx]] = idx

        self.populate_data_arrays(self.opaque_images, self.trans_images, sprite_info_lookup,
                                  first_dirty_opaque_idx=first_dirty_idx)

        # if self.get_num_sprites() > 100:
        #     print(f"INFO: Rebuilt {self.get_num_sprites()} sprites with a no-op rate of: "
        #           f"{(first_dirty_idx + 1) / len(self.opaque_images)}")

    def render(self, engine):
        engine.set_camera_2d(self.get_offset(), scale=[self.get_scale()] * 2)

        if engine.is_opengl():
            self.set_client_states(True, engine)
            self.opaque_data_arrays.pass_attributes_and_draw(engine)

            engine.set_depth_write_enabled(False)
            self.trans_data_arrays.pass_attributes_and_draw(engine)
            engine.set_depth_write_enabled(True)

            self.set_client_states(False, engine)
        else:
            # compatibility mode
            all_sprites = [engine.sprite_info_lookup[spr_id].sprite for spr_id in self._id_to_idx]
            all_sprites.sort(key=lambda sprite: -sprite.depth())
            for spr in all_sprites:
                engine.blit_sprite(spr)

    def set_client_states(self, enable, engine):
        engine.set_vertices_enabled(enable)
        engine.set_texture_coords_enabled(enable)
        engine.set_colors_enabled(enable)
        engine.set_alpha_test_enabled(enable)
        engine.set_depth_test_enabled(enable)

    def __contains__(self, uid):
        return uid in self._id_to_idx

    def get_num_sprites(self):
        return len(self._id_to_idx)

    def __repr__(self):
        return "{}({}, {})".format(type(self).__name__, self.get_layer_id(), self.get_layer_z())


class PolygonLayer(ImageLayer):

    def __init__(self, layer_id, layer_z):
        ImageLayer.__init__(self, layer_id, layer_z)

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

