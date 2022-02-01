from OpenGL.GL import *
from OpenGL.GLU import *

import numpy
import math
import re
import traceback
import pygame
import configs

import src.engine.globaltimer as globaltimer
import src.engine.crashreporting as crashreporting
import src.utils.util as util
import src.utils.matutils as matutils


_SINGLETON = None


def create_instance(glsl_version):
    """Initializes (or re-initializes) the RenderEngine singleton."""
    global _SINGLETON
    old_engine = _SINGLETON
    _SINGLETON = _get_best_render_engine(glsl_version)

    if old_engine is not None:
        for lay_id in old_engine.layers:
            lay = old_engine.layers[lay_id]
            _SINGLETON.add_layer(lay)
            if lay_id in old_engine.hidden_layers:
                _SINGLETON.hide_layer(lay_id)

        _SINGLETON.init(*old_engine.size)
        _SINGLETON.set_min_size(*old_engine.min_size)
        _SINGLETON.set_pixel_scale(old_engine.get_pixel_scale())

        _SINGLETON.set_texture_atlas(old_engine.cached_texture_atlas)
        _SINGLETON.sprite_info_lookup.update(old_engine.sprite_info_lookup)

    return _SINGLETON


def check_system_glsl_version(or_else_throw=True):
    # XXX note that this only works *after* an OPENGL window has been made.
    try:
        vstring = glGetString(GL_VERSION)
        vstring = vstring.decode() if vstring is not None else None
        print("INFO: running OpenGL version: {}".format(vstring))
        crashreporting.add_runtime_info("OpenGL Version", vstring)

        # this line will throw a GLerror if the system's OpenGL version is < 2.0
        # (because GL_SHADING_LANGUAGE_VERSION isn't valid before then).
        glsl_version = glGetString(GL_SHADING_LANGUAGE_VERSION)
        glsl_version = glsl_version.decode() if glsl_version is not None else None
        print("INFO: with shading language version: {}".format(glsl_version))
        crashreporting.add_runtime_info("Shader Language Version", glsl_version)

        return glsl_version

    except GLerror as e:
        if or_else_throw:
            raise e
        else:
            print("WARN: failed to query OpenGL Shader Language (GLSL) version, falling back to compatibility mode.")
            traceback.print_exc()
            return None


def _get_best_render_engine(glsl_version):
    major_vers, minor_vers = 1, 0

    if glsl_version is not None:
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

    if major_vers > 2 or minor_vers >= 30:  # 1.30 is OpenGL 3.0
        crashreporting.add_runtime_info("Render Engine", "RenderEngine130")
        return RenderEngine130()
    elif 20 <= minor_vers:  # 1.20 is OpenGL 2.1
        crashreporting.add_runtime_info("Render Engine", "RenderEngine120")
        return RenderEngine120()
    else:
        # Anything earlier than that, we fallback to CPU rendering.
        crashreporting.add_runtime_info("Render Engine", "PurePygameRenderEngine (Compatibility Mode)")
        return PurePygameRenderEngine()


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


class _SpriteInfoBundle:

    def __init__(self, sprite, last_updated_tick):
        self.sprite = sprite
        self.last_updated_tick = last_updated_tick


class RenderEngine:

    def __init__(self):
        self.sprite_info_lookup = {}  # (int) id -> _SpriteInfoBundle
        self.size = (0, 0)
        self.min_size = (0, 0)
        self._pixel_scale = 1  # the number of screen "pixels" per game pixel
        self.layers = {}  # layer_id -> layer
        self.hidden_layers = {}  # layer_id -> None
        self.ordered_layers = []
        self.shader = None

        self.tex_id = None

        self.cached_texture_atlas = None
        self.raw_texture_data = (None, 0, 0)  # data, width, height
        
    def add_layer(self, layer):
        self.layers[layer.get_layer_id()] = layer
        
        self.ordered_layers = list(self.layers.values())
        self.ordered_layers.sort(key=lambda x: x.get_layer_z())
        
    def remove_layer(self, layer_id):
        del self.layers[layer_id]
        
        self.ordered_layers = list(self.layers.values())
        self.ordered_layers.sort(key=lambda x: x.get_layer_z())

    def get_layer(self, layer_id):
        return self.layers[layer_id]

    def hide_layer(self, layer_id):
        self.hidden_layers[layer_id] = None

    def show_layer(self, layer_id):
        if layer_id in self.hidden_layers:
            del self.hidden_layers[layer_id]
        
    def set_layer_offset(self, layer_id, offs_x, offs_y):
        self.layers[layer_id].set_offset(offs_x, offs_y)

    def set_layer_scale(self, layer_id, scale):
        self.layers[layer_id].set_scale(scale)

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
            params: tuple of floats (r, g, b) each between 0 and 1.0
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

    def set_view_matrix(self, mat):
        raise NotImplementedError()

    def set_model_matrix(self, mat):
        raise NotImplementedError()

    def set_proj_matrix(self, mat):
        raise NotImplementedError()

    def set_camera_2d(self, offs2d, scale=(1, 1)):
        """
            Convenience method. Can be called instead of the three `set_XXX_matrix()`
            methods for simple 2D scenes.
        """
        model = numpy.identity(4, dtype=numpy.float32)
        self.set_model_matrix(model)

        view = matutils.translation_matrix(util.mult(offs2d, -1))
        matutils.scale_matrix(scale, mat=view)
        self.set_view_matrix(view)

        game_width, game_height = self.get_game_size()
        proj = matutils.ortho_matrix(0, game_width, game_height, 0, 1, -1)
        self.set_proj_matrix(proj)

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

    def is_opengl(self):
        return True

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
            self._set_texture_data_as_str(img_data, w, h, tex_id=self.tex_id)

    def set_texture_atlas(self, texture: pygame.Surface):
        self.cached_texture_atlas = texture
        img_data = pygame.image.tostring(texture, 'RGBA', True)
        self._set_texture_data_as_str(img_data, texture.get_width(), texture.get_height())

    def _set_texture_data_as_str(self, img_data, width, height, tex_id=None):
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

        self.on_texture_changed()

    def on_texture_changed(self):
        pass
        
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

    def clear_screen(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    def render_layers(self):
        self.clear_screen()

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
            
            self.render_layer(layer)

    def render_layer(self, layer):
        layer.render(self)

    def draw_elements(self, indices):
        glDrawElements(GL_TRIANGLES, len(indices), GL_UNSIGNED_INT, indices)

    def cleanup(self):
        self.shader.end()

    def count_sprites(self):
        res = 0
        for layer in self.layers.values():
            res += layer.get_num_sprites()
        return res


def get_instance() -> RenderEngine:
    """after init is called, returns the RenderEngine singleton."""
    return _SINGLETON


class RenderEngine130(RenderEngine):

    def __init__(self):
        super().__init__()
        self._tex_uniform_loc = None
        self._tex_size_uniform_loc = None

        self._model_matrix_uniform_loc = None
        self._view_matrix_uniform_loc = None
        self._proj_matrix_uniform_loc = None

        self._position_attrib_loc = None
        self._texture_pos_attrib_loc = None
        self._color_attrib_loc = None

        self._model_matrix = numpy.identity(4, dtype=numpy.float32)
        self._view_matrix = numpy.identity(4, dtype=numpy.float32)
        self._proj_matrix = numpy.identity(4, dtype=numpy.float32)

    def get_glsl_version(self):
        return "130"

    def build_shader(self):
        return Shader(
            '''
            # version 130
            in vec3 position;
            
            uniform mat4 model;
            uniform mat4 view;
            uniform mat4 proj;
            
            in vec2 vTexCoord;
            out vec2 texCoord;
            
            in vec3 vColor;
            out vec3 color;
    
            void main()
            {
                texCoord = vTexCoord;
                color = vColor;
                gl_Position = proj * view * model * vec4(position.x, position.y, position.z, 1.0);
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

        self._model_matrix_uniform_loc = glGetUniformLocation(prog_id, "model")
        self._assert_valid_var("model", self._model_matrix_uniform_loc)
        glUniformMatrix4fv(self._model_matrix_uniform_loc, 1, GL_TRUE, self._model_matrix)
        printOpenGLError()

        self._view_matrix_uniform_loc = glGetUniformLocation(prog_id, "view")
        self._assert_valid_var("view", self._view_matrix_uniform_loc)
        glUniformMatrix4fv(self._view_matrix_uniform_loc, 1, GL_TRUE, self._view_matrix)
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

    def set_model_matrix(self, mat):
        self._model_matrix = mat if mat is not None else numpy.identity(4, dtype=numpy.float32)
        glUniformMatrix4fv(self._model_matrix_uniform_loc, 1, GL_TRUE, self._model_matrix)
        printOpenGLError()

    def set_view_matrix(self, mat):
        self._view_matrix = mat if mat is not None else numpy.identity(4, dtype=numpy.float32)
        glUniformMatrix4fv(self._view_matrix_uniform_loc, 1, GL_TRUE, self._view_matrix)
        printOpenGLError()

    def set_proj_matrix(self, mat):
        self._proj_matrix = mat if mat is not None else numpy.identity(4, dtype=numpy.float32)
        glUniformMatrix4fv(self._proj_matrix_uniform_loc, 1, GL_TRUE, self._proj_matrix)
        printOpenGLError()

    def resize_internal(self):
        self.set_proj_matrix(numpy.identity(4, dtype=numpy.float32))
        self.set_view_matrix(numpy.identity(4, dtype=numpy.float32))
        self.set_model_matrix(numpy.identity(4, dtype=numpy.float32))

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

    def on_texture_changed(self):
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
        glVertexAttribPointer(self._position_attrib_loc, 3, GL_FLOAT, GL_FALSE, 0, data)
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
            attribute vec3 position;
            
            uniform mat4 model;
            uniform mat4 view;
            uniform mat4 proj;
            
            attribute vec2 vTexCoord;
            varying vec2 texCoord;
            
            attribute vec3 vColor;
            varying vec3 color;
            
            void main()
            {
                texCoord = vTexCoord;
                color = vColor;
                gl_Position = proj * view * model * vec4(position.x, position.y, position.z, 1.0);
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


import src.engine.sprites as sprites


class PurePygameRenderEngine(RenderEngine):

    def __init__(self):
        super().__init__()
        self.clear_color = (0, 0, 0)

        self.camera_xy = [0, 0]
        self.camera_scale = (1, 1)
        self.camera_surface = None

    def is_opengl(self):
        return False

    def get_glsl_version(self): return None
    def build_shader(self): pass
    def setup_shader(self): pass

    def set_view_matrix(self, mat): raise ValueError("set_view_matrix() not supported in RenderEnginePurePygame.")
    def set_model_matrix(self, mat): raise ValueError("set_model_matrix() not supported in RenderEnginePurePygame.")
    def set_proj_matrix(self, mat): raise ValueError("set_proj_matrix() not supported in RenderEnginePurePygame.")

    def resize_internal(self): pass
    def set_vertices_enabled(self, val): pass
    def set_vertices(self, data): pass
    def set_texture_coords_enabled(self, val): pass
    def set_texture_coords(self, data): pass

    def set_colors_enabled(self, val): pass
    def set_colors(self, data): pass

    def reset_for_display_mode_change(self, new_surface):
        self.set_camera_2d(self.camera_xy, self.camera_scale)

    def on_texture_changed(self): pass
    def cleanup(self): pass

    def init(self, w, h):
        """
        params w, h: The dimension of the window (not the "game size"!)
        """
        self.resize(w, h)

    def set_clear_color(self, color):
        self.clear_color = tuple(util.bound(int(c * 256), 0, 255) for c in color)

    def _get_render_mult(self) -> int:
        return self.get_pixel_scale()

    def set_camera_2d(self, xy, scale=(1, 1)):
        self.camera_xy = xy
        self.camera_scale = scale
        game_size = self.get_game_size()
        mult = self._get_render_mult()
        camera_surface_size = (int(game_size[0] * mult), int(game_size[1] * mult))
        display_size = pygame.display.get_surface().get_size()
        if (abs(display_size[0] - camera_surface_size[0]) < mult
                and abs(display_size[1] - camera_surface_size[1]) < mult):
            # can just draw directly to the display
            self.camera_surface = None
        else:
            if self.camera_surface is None or self.camera_surface.get_size() != camera_surface_size:
                self.camera_surface = pygame.Surface(camera_surface_size, pygame.SRCALPHA)

    def set_texture_atlas(self, texture: pygame.Surface):
        self.cached_texture_atlas = texture.convert_alpha()
        self.on_texture_changed()

    def _get_drawing_surface(self):
        if self.camera_surface is not None:
            return self.camera_surface
        else:
            return pygame.display.get_surface()

    def blit_sprite(self, sprite: 'sprites.AbstractSprite'):
        if sprite is None:
            return
        elif isinstance(sprite, sprites.MultiSprite):
            for spr in sprite.all_sprites():
                self.blit_sprite(spr)
        else:
            mult = self._get_render_mult()
            offs = (self.camera_xy[0] * mult,
                    self.camera_xy[1] * mult)

            if isinstance(sprite, sprites.ImageSprite):
                if sprite.model() is not None:
                    src_rect_on_atlas = sprite.model().rect()
                    dest_rect_in_world = sprite.rect()

                    surf = self._get_drawing_surface()
                    dest_rect = [dest_rect_in_world[0] * mult * self.camera_scale[0] - offs[0],
                                 dest_rect_in_world[1] * mult * self.camera_scale[1] - offs[1],
                                 dest_rect_in_world[2] * mult * self.camera_scale[0],
                                 dest_rect_in_world[3] * mult * self.camera_scale[1]]

                    if (src_rect_on_atlas[2] == dest_rect[2]
                            and src_rect_on_atlas[3] == dest_rect[3]
                            and sprite.rotation() == 0
                            and sprite.xflip() is False
                            and sprite.color() == (1, 1, 1)):
                        # already the correct size, just blit it
                        surf.blit(self.cached_texture_atlas, (dest_rect[0], dest_rect[1]), src_rect_on_atlas)
                    else:
                        subsurf = self.cached_texture_atlas.subsurface(src_rect_on_atlas)
                        orig_subsurf = subsurf
                        if sprite.xflip():
                            subsurf = pygame.transform.flip(subsurf, True, False)

                        if sprite.rotation() == 0:
                            subsurf = subsurf.copy()
                        elif sprite.rotation() == 1:
                            subsurf = pygame.transform.rotate(subsurf, -90)
                        elif sprite.rotation() == 2:
                            subsurf = pygame.transform.rotate(subsurf, -180)
                        else:
                            subsurf = pygame.transform.rotate(subsurf, -270)

                        if sprite.color() != (1, 1, 1):
                            if subsurf == orig_subsurf:
                                subsurf = subsurf.copy()
                            color255 = tuple(util.bound(int(c * 256), 0, 255) for c in sprite.color())
                            subsurf.fill(color255, [0, 0, subsurf.get_width(), subsurf.get_height()], pygame.BLEND_MULT)

                        xformed = pygame.transform.scale(subsurf, (int(dest_rect[2]), int(dest_rect[3])))
                        surf.blit(xformed, (dest_rect[0], dest_rect[1]))
            elif isinstance(sprite, sprites.TriangleSprite):
                surf = self._get_drawing_surface()
                color255 = list(util.bound(int(c * 256), 0, 255) for c in sprite.color())
                xformed_pts = [(p[0] * mult - offs[0], p[1] * mult - offs[1]) for p in sprite.points()]
                pygame.draw.polygon(surf, color255, xformed_pts)

    def render_layer(self, layer):
        super().render_layer(layer)

        if self.camera_surface is not None:
            display_surf = pygame.display.get_surface()
            temp = pygame.transform.scale(self.camera_surface, display_surf.get_size())
            display_surf.blit(temp, (0, 0), temp.get_rect(), pygame.BLEND_PREMULTIPLIED)

    def clear_screen(self):
        self._get_drawing_surface().fill(self.clear_color)

