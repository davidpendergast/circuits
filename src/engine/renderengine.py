from OpenGL.GL import *
from OpenGL.GLU import *

import numpy
import math
import re
import traceback

import src.engine.globaltimer as globaltimer


def printOpenGLError():
    err = glGetError()
    if err != GL_NO_ERROR:
        print("GLERROR: {}".format(gluErrorString(err)))


class Shader:

    def __init__(self, vertex_shader_source, fragment_shader_source):
        self.program = glCreateProgram()
        printOpenGLError()

        self.vs = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(self.vs, [vertex_shader_source])
        glCompileShader(self.vs)
        glAttachShader(self.program, self.vs)
        printOpenGLError()
        info_log = glGetShaderInfoLog(self.vs)
        if len(info_log) > 0:
            print("INFO: vertex shader has non-empty info log: {}".format(info_log))

        self.fs = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(self.fs, [fragment_shader_source])
        glCompileShader(self.fs)
        glAttachShader(self.program, self.fs)
        printOpenGLError()
        info_log = glGetShaderInfoLog(self.fs)
        if len(info_log) > 0:
            print("INFO: fragment shader has non-empty info log: {}".format(info_log))

        glLinkProgram(self.program)
        printOpenGLError()

    def get_program(self):
        return self.program

    def begin(self):
        if glUseProgram(self.program):
            printOpenGLError()

    def end(self):
        glUseProgram(0)


_SINGLETON = None


def create_instance():
    """intializes the RenderEngine singleton."""
    global _SINGLETON
    if _SINGLETON is None:
        vstring = glGetString(GL_VERSION)
        vstring = vstring.decode() if vstring is not None else None
        print("INFO: running OpenGL version: {}".format(vstring))

        glsl_version = glGetString(GL_SHADING_LANGUAGE_VERSION)
        glsl_version = glsl_version.decode() if glsl_version is not None else None
        print("INFO: with shading language version: {}".format(glsl_version))

        _SINGLETON = _get_best_render_engine(glsl_version)
        return _SINGLETON
    else:
        raise ValueError("There is already a RenderEngine initialized.")


def get_instance():
    """after init is called, returns the RenderEngine singleton."""
    return _SINGLETON


def _get_best_render_engine(glsl_version):
    major_vers = 1
    minor_vers = 0

    try:
        # it's formatted like "##.##.## <Anything>", so we split on periods and spaces
        chunks = re.split("[. ]", glsl_version)
        chunks = [c for c in chunks if len(c) > 0]

        if len(chunks) >= 1:
            major_vers = int(chunks[0])
        if len(chunks) >= 2:
            minor_vers = int(chunks[1])

    except Exception:
        print("ERROR: failed to parse glsl_version: {}".format(glsl_version))
        traceback.print_exc()

    if major_vers <= 1 and minor_vers < 30:
        return RenderEngine120()
    else:
        return RenderEngine130()


class _SpriteInfoBundle:

    def __init__(self, sprite, last_updated_tick):
        self.sprite = sprite
        self.last_updated_tick = last_updated_tick


class RenderEngine:

    def __init__(self):
        self.sprite_info_lookup = {}  # (int) id -> _SpriteInfoBundle
        self.camera_pos = [0, 0]
        self.size = (0, 0)
        self.min_size = (0, 0)
        self._pixel_scale = 1  # the number of screen "pixels" per game pixel
        self.layers = {}  # layer_id -> layer
        self.hidden_layers = {}  # layer_id -> None
        self.ordered_layers = []
        self.shader = None

        self.tex_id = None

        self.raw_texture_data = (None, 0, 0)  # data, width, height
        
    def add_layer(self, layer):
        self.layers[layer.get_layer_id()] = layer
        
        self.ordered_layers = list(self.layers.values())
        self.ordered_layers.sort(key=lambda x: x.get_layer_depth())
        
    def remove_layer(self, layer_id):
        del self.layers[layer_id]
        
        self.ordered_layers = list(self.layers.values())
        self.ordered_layers.sort(key=lambda x: x.get_layer_depth())

    def hide_layer(self, layer_id):
        self.hidden_layers[layer_id] = None

    def show_layer(self, layer_id):
        if layer_id in self.hidden_layers:
            del self.hidden_layers[layer_id]
        
    def set_layer_offset(self, layer_id, offs_x, offs_y):
        self.layers[layer_id].set_offset(offs_x, offs_y)

    def resize(self, w, h, px_scale=None):
        if px_scale is not None:
            self._pixel_scale = px_scale

        w = max(w, self.min_size[0])
        h = max(h, self.min_size[1])

        self.size = (w, h)

        self.resize_internal()

    def set_min_size(self, w, h):
        self.min_size = (w, h)

        if self.size[0] < self.min_size[0] or self.size[1] < self.min_size[1]:
            self.resize(self.size[0], self.size[1])

    def get_game_size(self):
        return (math.ceil(self.size[0] / self.get_pixel_scale()),
                math.ceil(self.size[1] / self.get_pixel_scale()))

    def set_clear_color(self, color):
        """
            params: tuple of ints (r, g, b) each between 0 and 1.0
        """
        r, g, b = color
        glClearColor(r, g, b, 0.0)

    def get_pixel_scale(self):
        return self._pixel_scale

    def set_pixel_scale(self, val):
        self.resize(self.size[0], self.size[1], px_scale=val)

    def get_glsl_version(self):
        raise NotImplementedError()

    def build_shader(self):
        raise NotImplementedError()

    def setup_shader(self):
        raise NotImplementedError()

    def set_matrix_offset(self, x, y):
        raise NotImplementedError()

    def resize_internal(self):
        raise NotImplementedError()

    def set_vertices_enabled(self, val):
        raise NotImplementedError()

    def set_vertices(self, data):
        raise NotImplementedError()

    def set_texture_coords_enabled(self, val):
        raise NotImplementedError()

    def set_texture_coords(self, data):
        raise NotImplementedError()

    def set_colors_enabled(self, val):
        raise NotImplementedError()

    def set_colors(self, data):
        raise NotImplementedError()

    def get_shader(self):
        return self.shader

    def init(self, w, h):
        """
        params w, h: The dimension of the window (not the "game size"!)
        """
        glShadeModel(GL_FLAT)
        glClearColor(0.5, 0.5, 0.5, 0.0)

        print("INFO: building shader for GLSL version: {}".format(self.get_glsl_version()))
        self.shader = self.build_shader()
        self.shader.begin()
        self.setup_shader()

        self.resize(w, h)

    def reset_for_display_mode_change(self, new_surface):
        """
           XXX on Windows, when pygame.display.set_mode is called, it seems to wipe away the active
           gl context, so we get around that by rebuilding the shader program and rebinding the texture...
        """
        self.shader.end()

        self.shader = self.build_shader()
        self.shader.begin()
        self.setup_shader()

        img_data, w, h = self.raw_texture_data
        if img_data is not None:
            self.set_texture(img_data, w, h, tex_id=self.tex_id)

    def set_texture(self, img_data, width, height, tex_id=None):
        """
            img_data: image data in string RGBA format.
        """
        if tex_id is None:
            tex_id = glGenTextures(1)
            self.tex_id = tex_id

        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        glEnable(GL_TEXTURE_2D)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.raw_texture_data = (img_data, width, height)

        self.set_texture_internal()

    def set_texture_internal(self):
        pass

    def set_camera_pos(self, x, y, center=False):
        self.camera_pos[0] = x - (self.size[0] // 2) if center else 0
        self.camera_pos[1] = y - (self.size[1] // 2) if center else 0
        
    def update(self, sprite):
        if sprite is None:
            return

        if sprite.is_parent():
            for child_sprite in sprite.all_sprites():
                self.update(child_sprite)
        else:
            uid = sprite.uid()
            cur_tick = globaltimer.tick_count()

            if uid not in self.sprite_info_lookup:
                self.sprite_info_lookup[uid] = _SpriteInfoBundle(sprite, cur_tick)
            else:
                self.sprite_info_lookup[uid].sprite = sprite
                self.sprite_info_lookup[uid].last_updated_tick = cur_tick

            layer = self.layers[sprite.layer_id()]

            if layer.accepts_sprite_type(sprite.sprite_type()):
                layer.update(uid, sprite.last_modified_tick())
            else:
                raise ValueError("Incompatible sprite type: {}".format(sprite.sprite_type()))
        
    def render_layers(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # clear out sprites that weren't updated this tick
        cur_tick = globaltimer.tick_count()
        ids_to_remove = [sprite_id for sprite_id in self.sprite_info_lookup
                         if self.sprite_info_lookup[sprite_id].last_updated_tick < cur_tick]

        for sprite_id in ids_to_remove:
            sprite_info = self.sprite_info_lookup[sprite_id]
            self.layers[sprite_info.sprite.layer_id()].remove(sprite_id)
            del self.sprite_info_lookup[sprite_id]

        for layer in self.ordered_layers:
            if layer.is_dirty():
                layer.rebuild(self.sprite_info_lookup)

            if layer.get_layer_id() in self.hidden_layers:
                continue

            offs = layer.get_offset()

            self.set_matrix_offset(-offs[0], -offs[1])
            
            layer.render(self)

    def cleanup(self):
        self.shader.end()

    def count_sprites(self):
        res = 0
        for layer in self.layers.values():
            res += layer.get_num_sprites()
        return res


def translation_matrix(x, y):
    res = numpy.identity(4, dtype=numpy.float32)
    res.itemset((0, 3), float(x))
    res.itemset((1, 3), float(y))
    return res


def ortho_matrix(left, right, bottom, top, near_val, far_val):
    res = numpy.identity(4, dtype=numpy.float32)
    res.itemset((0, 0), float(2 / (right - left)))
    res.itemset((1, 1), float(2 / (top - bottom)))
    res.itemset((2, 2), float(-2 / (far_val - near_val)))

    t_x = -(right + left) / (right - left)
    t_y = -(top + bottom) / (top - bottom)
    t_z = -(far_val + near_val) / (far_val - near_val)
    res.itemset((0, 3), float(t_x))
    res.itemset((1, 3), float(t_y))
    res.itemset((2, 3), float(t_z))

    return res


class RenderEngine130(RenderEngine):

    def __init__(self):
        super().__init__()
        self._tex_uniform_loc = None
        self._tex_size_uniform_loc = None
        self._modelview_matrix_uniform_loc = None
        self._proj_matrix_uniform_loc = None

        self._position_attrib_loc = None
        self._texture_pos_attrib_loc = None
        self._color_attrib_loc = None

        self._modelview_matrix = numpy.identity(4, dtype=numpy.float32)
        self._proj_matrix = numpy.identity(4, dtype=numpy.float32)

    def get_glsl_version(self):
        return "130"

    def build_shader(self):
        return Shader(
            '''
            # version 130
            in vec2 position;
            
            uniform mat4 modelview;
            uniform mat4 proj;
            
            in vec2 vTexCoord;
            out vec2 texCoord;
            
            in vec3 vColor;
            out vec3 color;
    
            void main()
            {
                texCoord = vTexCoord;
                color = vColor;
                gl_Position = proj * modelview * vec4(position.x, position.y, 0.0, 1.0);
            }
            ''',
            '''
            #version 130
            in vec2 texCoord;
            in vec3 color;
            
            uniform vec2 texSize;
            uniform sampler2D tex0;

            void main(void) {
                vec2 texPos = vec2(texCoord.x / texSize.x, texCoord.y / texSize.y);
                vec4 tcolor = texture2D(tex0, texPos);
                
                for (int i = 0; i < 3; i++) {
                    if (tcolor[i] >= 0.99) {
                        gl_FragColor[i] = tcolor[i] * color[i];
                    } else {
                        gl_FragColor[i] = tcolor[i] * color[i] * color[i];                    
                    }
                }
                
                gl_FragColor.w = tcolor.w;
            }
            '''
        )

    def _assert_valid_var(self, varname, loc):
        if loc < 0:
            raise ValueError("invalid uniform or attribute: {}".format(varname))

    def setup_shader(self):
        prog_id = self.get_shader().get_program()

        self._tex_uniform_loc = glGetUniformLocation(prog_id, "tex0")
        self._assert_valid_var("tex0", self._tex_uniform_loc)
        glUniform1i(self._tex_uniform_loc, 0)
        printOpenGLError()

        self._tex_size_uniform_loc = glGetUniformLocation(prog_id, "texSize")
        self._assert_valid_var("texSize", self._tex_size_uniform_loc)
        printOpenGLError()

        self._modelview_matrix_uniform_loc = glGetUniformLocation(prog_id, "modelview")
        self._assert_valid_var("modelview", self._modelview_matrix_uniform_loc)
        glUniformMatrix4fv(self._modelview_matrix_uniform_loc, 1, GL_TRUE, self._modelview_matrix)
        printOpenGLError()

        self._proj_matrix_uniform_loc = glGetUniformLocation(prog_id, "proj")
        self._assert_valid_var("proj", self._proj_matrix_uniform_loc)
        glUniformMatrix4fv(self._proj_matrix_uniform_loc, 1, GL_TRUE, self._proj_matrix)
        printOpenGLError()

        self._position_attrib_loc = glGetAttribLocation(prog_id, "position")
        self._assert_valid_var("position", self._position_attrib_loc)

        self._texture_pos_attrib_loc = glGetAttribLocation(prog_id, "vTexCoord")
        self._assert_valid_var("vTexCoord", self._texture_pos_attrib_loc)

        self._color_attrib_loc = glGetAttribLocation(prog_id, "vColor")
        self._assert_valid_var("vColor", self._color_attrib_loc)

        # set default color to white
        glVertexAttrib3f(self._color_attrib_loc, 1.0, 1.0, 1.0)
        printOpenGLError()

    def set_matrix_offset(self, x, y):
        self._modelview_matrix = numpy.identity(4, dtype=numpy.float32)
        trans = translation_matrix(x, y)
        numpy.matmul(self._modelview_matrix, trans, out=self._modelview_matrix, dtype=numpy.float32)

        glUniformMatrix4fv(self._modelview_matrix_uniform_loc, 1, GL_TRUE, self._modelview_matrix)
        printOpenGLError()

    def resize_internal(self):
        game_width, game_height = self.get_game_size()

        self._proj_matrix = numpy.identity(4, dtype=numpy.float32)
        ortho = ortho_matrix(0, game_width, game_height, 0, 1, -1)
        numpy.matmul(self._proj_matrix, ortho, out=self._proj_matrix, dtype=numpy.float32)

        glUniformMatrix4fv(self._proj_matrix_uniform_loc, 1, GL_TRUE, self._proj_matrix)
        printOpenGLError()

        self.set_matrix_offset(0, 0)

        vp_width, vp_height = self._calc_optimal_vp_size(self.size, self.get_pixel_scale())
        glViewport(0, 0, vp_width, vp_height)
        printOpenGLError()

    def _calc_optimal_vp_size(self, window_size, px_scale):
        """
            finds the smallest dimensions greater than or equal to window_size
            that are evenly divisible by px_scale.
        """
        w, h = window_size
        if w % px_scale != 0:
            w += (px_scale - w % px_scale)
        if h % px_scale != 0:
            h += (px_scale - h % px_scale)
        return (w, h)

    def set_texture_internal(self):
        if self.raw_texture_data is not None:
            tex_w = self.raw_texture_data[1]
            tex_h = self.raw_texture_data[2]

            glUniform2f(self._tex_size_uniform_loc, float(tex_w), float(tex_h))
            printOpenGLError()

    def set_vertices_enabled(self, val):
        if val:
            glEnableVertexAttribArray(self._position_attrib_loc)
        else:
            glDisableVertexAttribArray(self._position_attrib_loc)
        printOpenGLError()

    def set_vertices(self, data):
        glVertexAttribPointer(self._position_attrib_loc, 2, GL_FLOAT, GL_FALSE, 0, data)
        printOpenGLError()

    def set_texture_coords_enabled(self, val):
        if val:
            glEnableVertexAttribArray(self._texture_pos_attrib_loc)
        else:
            glDisableVertexAttribArray(self._texture_pos_attrib_loc)
        printOpenGLError()

    def set_texture_coords(self, data):
        glVertexAttribPointer(self._texture_pos_attrib_loc, 2, GL_FLOAT, GL_FALSE, 0, data)
        printOpenGLError()

    def set_colors_enabled(self, val):
        if val:
            glEnableVertexAttribArray(self._color_attrib_loc)
        else:
            glDisableVertexAttribArray(self._color_attrib_loc)
        printOpenGLError()

    def set_colors(self, data):
        glVertexAttribPointer(self._color_attrib_loc, 3, GL_FLOAT, GL_FALSE, 0, data)
        printOpenGLError()


class RenderEngine120(RenderEngine130):

    def get_glsl_version(self):
        return "120"

    def build_shader(self):
        return Shader(
            '''
            # version 120
            attribute vec2 position;
            
            uniform mat4 modelview;
            uniform mat4 proj;
            
            attribute vec2 vTexCoord;
            varying vec2 texCoord;
            
            attribute vec3 vColor;
            varying vec3 color;
            
            void main()
            {
                texCoord = vTexCoord;
                color = vColor;
                gl_Position = proj * modelview * vec4(position.x, position.y, 0.0, 1.0);
            }
            ''',
            '''
            #version 120
            varying vec2 texCoord;
            varying vec3 color;
            
            uniform vec2 texSize;
            uniform sampler2D tex0;
            
            void main(void) {
                vec2 texPos = vec2(texCoord.x / texSize.x, texCoord.y / texSize.y);
                vec4 tcolor = texture2D(tex0, texPos);
                for (int i = 0; i < 3; i++) {
                    if (tcolor[i] >= 0.99) {
                        gl_FragColor[i] = tcolor[i] * color[i];
                    } else {
                        gl_FragColor[i] = tcolor[i] * color[i] * color[i];                    
                    }
                }
                gl_FragColor.w = tcolor.w;
            }
            '''
        )

