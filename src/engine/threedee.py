import numpy

import src.engine.layers as layers
import src.engine.sprites as sprites
import src.utils.util as util


class ThreeDeeLayer(layers._Layer):

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


class Sprite3D(sprites.AbstractSprite):
    def __init__(self, model, layer_id, position=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1), color=(0, 0, 0), uid=None):
        sprites.AbstractSprite.__init__(self, sprites.SpriteTypes.THREE_DEE, layer_id, uid=uid)
        self._model = model

        self._position = position   # location of the model's origin
        self._rotation = rotation   # rotation of the model in each plane w.r.t. the origin
        self._scale = scale         # scale of the model in each axis

        self._color = color

    def model(self):
        return self._model

    def get_xform(self):
        # TODO hmmm
        return numpy.identity(4, dtype=numpy.float32)

    def position(self):
        return self._position

    def x(self):
        return self._position[0]

    def y(self):
        return self._position[1]

    def z(self):
        return self._position[2]

    def rotation(self):
        return self._rotation

    def scale(self):
        return self._scale

    def color(self):
        return self._color

    def update(self, new_model=None,
               new_x=None, new_y=None, new_z=None, new_position=None,
               new_xrot=None, new_yrot=None, new_zrot=None, new_rotation=None,
               new_xscale=None, new_yscale=None, new_zscale=None, new_scale=None,
               new_color=None):
        did_change = False

        model = self._model
        if new_model is not None and new_model != self._model:
            did_change = True
            model = new_model

        position = [self._position]
        if new_position is not None:
            new_x = new_position[0]
            new_y = new_position[1]
            new_z = new_position[2]
        if new_x is not None and new_x != self._position[0]:
            position[0] = new_x
            did_change = True
        if new_y is not None and new_y != self._position[1]:
            position[1] = new_y
            did_change = True
        if new_z is not None and new_z != self._position[2]:
            position[2] = new_z
            did_change = True

        rotation = [self._rotation]
        if new_rotation is not None:
            new_xrot = new_rotation[0]
            new_yrot = new_rotation[1]
            new_zrot = new_rotation[2]
        if new_xrot is not None and new_xrot != self._rotation[0]:
            rotation[0] = new_xrot
            did_change = True
        if new_yrot is not None and new_yrot != self._rotation[1]:
            rotation[1] = new_yrot
            did_change = True
        if new_zrot is not None and new_zrot != self._rotation[2]:
            rotation[2] = new_zrot
            did_change = True

        scale = [self._scale]
        if new_scale is not None:
            if isinstance(new_scale, (int, float)):
                new_scale = (new_scale, new_scale, new_scale)
            new_xscale = new_scale[0]
            new_yscale = new_scale[1]
            new_zscale = new_scale[2]
        if new_xscale is not None and new_xscale != self._scale[0]:
            scale[0] = new_xscale
            did_change = True
        if new_yscale is not None and new_yscale != self._scale[1]:
            scale[1] = new_yscale
            did_change = True
        if new_zscale is not None and new_zscale != self._scale[2]:
            scale[2] = new_zscale
            did_change = True

        color = self._color
        if new_color is not None and new_color != self._color:
            color = new_color
            did_change = True

        if not did_change:
            return self
        else:
            return Sprite3D(model, self.layer_id(), position=position, rotation=rotation,
                            scale=scale, color=color, uid=self.uid())


class ThreeDeeModel:

    def __init__(self, model_id, model_path, map_texture_xy_to_atlas):
        self._model_id = model_id

        self._vertices = []
        self._triangle_faces = []
        self._normals = []
        self._native_texture_coords = []

        self._map_texture_xy_to_atlas = map_texture_xy_to_atlas
        self._cached_atlas_coords = []

        self._load_from_disk(model_path)

    def get_model_id(self):
        return self._model_id

    def get_vertices(self):
        return self._vertices

    def get_faces(self):
        return self._triangle_faces

    def get_normals(self):
        return self._normals

    def get_texture_coords(self):
        if len(self._cached_atlas_coords) == 0:
            self._cached_atlas_coords = [self._map_texture_xy_to_atlas(xy) for xy in self._native_texture_coords]
        return self._cached_atlas_coords

    def _load_from_disk(self, model_path):
        self._cached_atlas_coords = []
        try:
            safe_path = util.resource_path(model_path)
            with open(safe_path) as f:
                for line in f:
                    line = line.rstrip()  # remove trailing newlines and whitespace
                    if line.startswith("v "):
                        xyz = line[2:].split(" ")
                        vertex = (float(xyz[0]), float(xyz[1]), float(xyz[2]))
                        self._vertices.append(vertex)

                    elif line.startswith("vn "):
                        xyz = line[3:].split(" ")
                        normal_vec = (float(xyz[0]), float(xyz[1]), float(xyz[2]))
                        self._normals.append(normal_vec)

                    elif line.startswith("vt "):
                        xy = line[3:].split(" ")
                        texture_coords = (float(xy[0]), float(xy[1]))
                        self._native_texture_coords.append(texture_coords)

                    elif line.startswith("f "):
                        corners = []
                        for corner in line[2:].split(" "):
                            vtn = corner.split("/")  # vertex, texture, normal
                            vertex_idx = int(vtn[0])
                            texture_idx = int(vtn[1]) if len(vtn) > 1 and len(vtn[1]) > 0 else 0
                            normal_idx = int(vtn[2]) if len(vtn) > 2 and len(vtn[2]) > 0 else 0
                            corners.append((vertex_idx, texture_idx, normal_idx))
                        self._triangle_faces.append(tuple(corners))
        except IOError:
            print("ERROR: failed to load model: {}".format(model_path))