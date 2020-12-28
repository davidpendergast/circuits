from OpenGL.GL import *

import numpy
import math

import src.engine.layers as layers
import src.engine.sprites as sprites
import src.utils.util as util
import src.utils.matutils as matutils
import configs


class ThreeDeeLayer(layers.ImageLayer):

    def __init__(self, layer_id, layer_depth, use_color=True):
        super().__init__(layer_id, layer_depth, sort_sprites=False, use_color=use_color)

        self.camera_position = (0, 0, 0)
        self.camera_direction = (0, 0, -1)
        self.camera_fov = 35

    def accepts_sprite_type(self, sprite_type):
        return sprite_type == sprites.SpriteTypes.THREE_DEE

    def populate_data_arrays(self, sprite_info_lookup):
        pass  # we don't actually use these

    def get_sprites_grouped_by_model_id(self, engine):
        res = {}  # model_id -> list of Sprite3D
        for sprite_id in self.images:
            spr_3d = engine.sprite_info_lookup[sprite_id].sprite
            if spr_3d.model().get_model_id() not in res:
                res[spr_3d.model().get_model_id()] = []
            res[spr_3d.model().get_model_id()].append(spr_3d)
        return res

    def render(self, engine):
        self.set_client_states(True, engine)
        self._set_uniforms_for_scene(engine)

        model_ids_to_sprites = self.get_sprites_grouped_by_model_id(engine)
        for model_id in model_ids_to_sprites:
            # only pass model data (vertices, tex_coords, indices) once per unique model in the scene
            model = model_ids_to_sprites[model_id][0].model()
            self._pass_attributes_for_model(engine, model)

            # draw each sprite with that model, using the same data data, but different uniforms
            for spr_3d in model_ids_to_sprites[model_id]:
                self._set_uniforms_for_sprite(engine, spr_3d)
                glDrawElements(GL_TRIANGLES, len(self.indices), GL_UNSIGNED_INT, self.indices)
        self.set_client_states(False, engine)

    def set_client_states(self, enable, engine):
        super().set_client_states(enable, engine)

        if enable:
            glEnable(GL_DEPTH_TEST)
            glEnable(GL_CULL_FACE)
            if configs.wireframe_3d:
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        else:
            glDisable(GL_DEPTH_TEST)
            glDisable(GL_CULL_FACE)
            if configs.wireframe_3d:
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    def get_view_matrix(self):
        # XXX I'm not sure why we have to flip the y components like this. It's either reversing errors introduced
        # elsewhere, or fixing a discrepancy between the world coordinate system and GL's internal coordinate system.
        # Either way though, the scene renders upside down without it, so... we flip
        target_pt = util.add(self.camera_position, util.negate(self.camera_direction, components=(1,)))
        m = matutils.get_matrix_looking_at2(self.camera_position, target_pt, self.get_camera_up())

        y_flipped = numpy.identity(4, dtype=numpy.float32)
        y_flipped.itemset((1, 1), -1)
        return y_flipped.dot(m)

    def get_proj_matrix(self, engine):
        w, h = engine.get_game_size()
        return matutils.perspective_matrix(self.camera_fov / 360 * 6.283, w / h, 0.5, 1000000)

    def get_camera_up(self):
        return (0, 1, 0)

    def _set_uniforms_for_scene(self, engine):
        view = self.get_view_matrix()
        engine.set_view_matrix(view)

        proj = self.get_proj_matrix(engine)
        engine.set_proj_matrix(proj)

    def _set_uniforms_for_sprite(self, engine, spr_3d: 'Sprite3D'):
        model = spr_3d.get_xform()
        engine.set_model_matrix(model)

    def _pass_attributes_for_model(self, engine, model_3d):
        self.vertices.resize(3 * len(model_3d.get_vertices()), refcheck=False)
        self.tex_coords.resize(2 * len(model_3d.get_texture_coords()), refcheck=False)
        self.indices.resize(len(model_3d.get_indices()), refcheck=False)

        model_3d.add_urself(self.vertices,
                          self.tex_coords,
                          self.indices)

        engine.set_vertices(self.vertices)
        engine.set_texture_coords(self.tex_coords)


class Sprite3D(sprites.AbstractSprite):
    def __init__(self, model, layer_id, position=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1), color=(1, 1, 1), uid=None):
        sprites.AbstractSprite.__init__(self, sprites.SpriteTypes.THREE_DEE, layer_id, uid=uid)
        self._model = model

        self._position = position   # location of the model's origin
        self._rotation = rotation   # rotation of the model in each plane w.r.t. the origin
        self._scale = scale         # scale of the model in each axis

        self._color = color

    def model(self) -> 'ThreeDeeModel':
        return self._model

    def get_xform(self):
        # translation matrix
        T = numpy.identity(4, dtype=numpy.float32)
        T.itemset((3, 0), -self._position[0])
        T.itemset((3, 1), -self._position[1])
        T.itemset((3, 2), -self._position[2])
        T = T.transpose()  # this is weird T_T

        # rotation matrices
        Rx = numpy.identity(4, dtype=numpy.float32)
        Rx.itemset((1, 1), math.cos(self._rotation[0]))
        Rx.itemset((2, 1), -math.sin(self._rotation[0]))
        Rx.itemset((1, 2), math.sin(self._rotation[0]))
        Rx.itemset((2, 2), math.cos(self._rotation[0]))
        # Rx = Rx.transpose()

        Ry = numpy.identity(4, dtype=numpy.float32)
        Ry.itemset((0, 0), math.cos(self._rotation[1]))
        Ry.itemset((2, 0), math.sin(self._rotation[1]))
        Ry.itemset((0, 2), -math.sin(self._rotation[1]))
        Ry.itemset((2, 2), math.cos(self._rotation[1]))
        # Ry = Ry.transpose()

        Rz = numpy.identity(4, dtype=numpy.float32)
        Rz.itemset((0, 0), math.cos(self._rotation[2]))
        Rz.itemset((1, 0), -math.sin(self._rotation[2]))
        Rz.itemset((0, 1), math.sin(self._rotation[2]))
        Rz.itemset((1, 1), math.cos(self._rotation[2]))
        # Rz = Rz.transpose()

        # scale matrix
        S = numpy.identity(4, dtype=numpy.float32)
        S.itemset((0, 0), self._scale[0])
        S.itemset((1, 1), self._scale[1])
        S.itemset((2, 2), self._scale[2])

        return T.dot(Rx).dot(Ry).dot(Rz).dot(S)

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

        position = [v for v in self._position]
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

        rotation = [v for v in self._rotation]
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

        scale = [v for v in self._scale]
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

    def add_urself(self, vertices, tex_coords, colors, indices):
        # TODO color?
        self.model().add_urself(vertices, tex_coords, indices)


class ThreeDeeModel:

    def __init__(self, model_id, model_path, map_texture_xy_to_atlas):
        self._model_id = model_id

        self._vertices = []                 # list of (x, y, z)
        self._normals = []                  # list of (x, y, z)
        self._native_texture_coords = []    # list of (x, y)
        self._indices = []                  # list of ints, one for each corner of each triangle

        self._map_texture_xy_to_atlas = map_texture_xy_to_atlas
        self._cached_atlas_coords = []      # list of (x, y)

        self._load_from_disk(model_path)

    def get_model_id(self):
        return self._model_id

    def get_vertices(self):
        return self._vertices

    def get_indices(self):
        return self._indices

    def get_normals(self):
        return self._normals

    def get_texture_coords(self):
        if len(self._cached_atlas_coords) == 0:
            self._cached_atlas_coords = [self._map_texture_xy_to_atlas(xy) for xy in self._native_texture_coords]
        return self._cached_atlas_coords

    def add_urself(self, vertices, tex_coords, indices):
        for i in range(0, 3 * len(self.get_vertices())):
            vertices[i] = self.get_vertices()[i // 3][i % 3]
        for i in range(0, 2 * len(self.get_texture_coords())):
            tex_coords[i] = self.get_texture_coords()[i // 2][i % 2]
        for i in range(0, len(self.get_indices())):
            indices[i] = self.get_indices()[i]

    def _load_from_disk(self, model_path):
        try:
            raw_vertices = []
            raw_normals = []
            raw_native_texture_coords = []
            triangle_faces = []

            safe_path = util.resource_path(model_path)
            with open(safe_path) as f:
                for line in f:
                    line = line.rstrip()  # remove trailing newlines and whitespace
                    if line.startswith("v "):
                        xyz = line[2:].split(" ")
                        vertex = (float(xyz[0]), float(xyz[1]), float(xyz[2]))
                        raw_vertices.append(vertex)

                    elif line.startswith("vn "):
                        xyz = line[3:].split(" ")
                        normal_vec = (float(xyz[0]), float(xyz[1]), float(xyz[2]))
                        raw_normals.append(normal_vec)

                    elif line.startswith("vt "):
                        xy = line[3:].split(" ")
                        texture_coords = (float(xy[0]), float(xy[1]))
                        raw_native_texture_coords.append(texture_coords)

                    elif line.startswith("f "):
                        corners = []
                        for corner in line[2:].split(" "):
                            vtn = corner.split("/")  # vertex, texture, normal
                            vertex_idx = int(vtn[0]) - 1
                            texture_idx = int(vtn[1]) - 1 if len(vtn) > 1 and len(vtn[1]) > 0 else -1
                            normal_idx = int(vtn[2]) - 1 if len(vtn) > 2 and len(vtn[2]) > 0 else -1
                            corners.append((vertex_idx, texture_idx, normal_idx))
                        triangle_faces.append(tuple(corners))

            for tri in triangle_faces:
                for c in tri:  # TODO use the normals
                    v_idx, t_idx, norm_idx = c
                    vertex_xyz = raw_vertices[v_idx]
                    texture_xy = raw_native_texture_coords[t_idx] if t_idx >= 0 else None
                    norm_xyz = raw_normals[norm_idx] if norm_idx >= 0 else None
                    # TODO can probably condense this a bit (only have one index per unique (vertex, texture, normal))
                    # TODO would that ever matter for most models? probably not?
                    index = len(self._indices)

                    self._vertices.append(vertex_xyz)
                    self._native_texture_coords.append(texture_xy)
                    self._normals.append(norm_xyz)
                    self._indices.append(index)
            print("INFO: loaded model ({} faces): {}".format(len(triangle_faces), model_path))
        except IOError:
            print("ERROR: failed to load model: {}".format(model_path))