
import pygame
import configs


_INSTANCE = None


def create_instance(window_size=(640, 480), min_size=(0, 0), opengl_mode=True):
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = WindowState(window_size, min_size=min_size, opengl_mode=opengl_mode)
        return _INSTANCE
    else:
        raise ValueError("There is already a WindowState initialized.")


def get_instance() -> 'WindowState':
    return _INSTANCE


def calc_pixel_scale(screen_size):
    if configs.auto_resize_pixel_scale:
        screen_w, screen_h = screen_size
        optimal_w = configs.optimal_window_size[0]
        optimal_h = configs.optimal_window_size[1]

        optimal_scale = configs.optimal_pixel_scale
        min_scale = configs.minimum_auto_pixel_scale
        max_scale = min(int(screen_w / optimal_w * optimal_scale + 1), int(screen_h / optimal_h * optimal_scale + 1))

        # when the screen is large enough to fit this quantity of (minimal) screens at a
        # particular scaling setting, that scale is considered good enough to switch to.
        # we choose the largest (AKA most zoomed in) "good" scale.
        step_up_x_ratio = 1.0
        step_up_y_ratio = 1.0

        best = min_scale
        for i in range(min_scale, max_scale + 1):
            if (optimal_w / optimal_scale * i * step_up_x_ratio <= screen_w
                    and optimal_h / optimal_scale * i * step_up_y_ratio <= screen_h):
                best = i
            else:
                break

        return best
    else:
        return configs.optimal_pixel_scale


class WindowState:

    def __init__(self, window_size, min_size=(0, 0), opengl_mode=True):
        self._is_fullscreen = False
        self._window_size = window_size
        self._min_size = min_size

        self._fullscreen_size = None

        self._icon_surface: pygame.Surface = None

        self._caption = "Game"
        self._caption_info = {}  # str -> str, for example "FPS" -> "60.0"
        self._show_caption_info = configs.is_dev

        self._opengl_mode: bool = opengl_mode

    def _get_mods(self):
        mods = 0
        if self._opengl_mode:
            mods = pygame.OPENGL | pygame.DOUBLEBUF | mods

        if configs.allow_window_resize:
            mods = pygame.RESIZABLE | mods

        if self.is_fullscreen():
            mods = pygame.FULLSCREEN | mods

        return mods

    def show(self):
        self._update_display_mode()

    def _update_display_mode(self):
        self._update_caption()
        self._update_icon()

        if self._is_fullscreen:
            new_surface = pygame.display.set_mode((0, 0), self._get_mods())
            self._fullscreen_size = new_surface.get_size()
            print(f"INFO: fullscreen size = {new_surface.get_size()}")
        else:
            new_surface = pygame.display.set_mode(self._window_size, self._get_mods())

        # TODO this OpenGL compatibility-mode dance between the window and render engine could probably be improved?
        # At game start, we're:
        # 1. Creating an OPENGL-flagged window (via pygame.display.set_mode())
        # 2. Checking to see if OpenGL actually works (via check_system_glsl_version())
        # 3a. If it does, we're all good.
        # 3b. If it doesn't, we kill the window (pygame.display.quit()), and make another window(!) without the flag.
        import src.engine.renderengine as renderengine
        render_eng = renderengine.get_instance()
        if render_eng is not None:
            if self.is_opengl_mode() != render_eng.is_opengl():
                if self.is_opengl_mode():
                    glsl_version_to_use = renderengine.check_system_glsl_version(or_else_throw=False)
                else:
                    glsl_version_to_use = None

                if self.is_opengl_mode() and glsl_version_to_use is None:
                    # nice try, but it's not supported.
                    self._opengl_mode = False
                    pygame.display.quit()  # kill the existing OPENGL-flagged window.
                    new_surface = pygame.display.set_mode(self._window_size, self._get_mods())
                    render_eng.reset_for_display_mode_change(new_surface)
                else:
                    # This call copies over all the cached data from the old render engine (texture_atlas, layers, etc.)
                    # Note that it also copies over its size, which may be stale if the game was fullscreen before.
                    render_eng = renderengine.create_instance(glsl_version_to_use)
            else:
                # XXX otherwise everything breaks on Windows (see docs on this method)
                render_eng.reset_for_display_mode_change(new_surface)

            # If the display's size changed (e.g. due to fullscreen state changing), gotta update the render engine.
            render_eng.resize(*new_surface.get_size(), px_scale=calc_pixel_scale(new_surface.get_size()))

    def set_caption(self, title):
        if title != self._caption:
            self._caption = title
            self._update_caption()

    def set_caption_info(self, name, value):
        if value is None:
            if name in self._caption_info:
                del self._caption_info[name]
                self._update_caption()
        elif (name not in self._caption_info or self._caption_info[name] != value):
            self._caption_info[name] = value
            self._update_caption()

    def is_showing_caption_info(self):
        return self._show_caption_info

    def set_show_caption_info(self, val):
        if val != self._show_caption_info:
            self._show_caption_info = val
            self._update_caption()

    def _update_caption(self):
        cap = self._caption
        if self._show_caption_info and len(self._caption_info) > 0:
            info = []
            for name in self._caption_info:
                info.append("{}={}".format(name, self._caption_info[name]))
            cap += " (" + ", ".join(info) + ")"
        pygame.display.set_caption(cap)

    def set_icon(self, surface):
        if surface != self._icon_surface:
            self._icon_surface = surface
            self._update_icon()

    def _update_icon(self):
        pygame.display.set_icon(self._icon_surface)

    def get_display_size(self):
        if self._is_fullscreen:
            return self._fullscreen_size
        else:
            return self._window_size

    def set_window_size(self, w, h):
        self._window_size = (w, h)

    def is_fullscreen(self):
        return self._is_fullscreen

    def set_fullscreen(self, val):
        if self.is_fullscreen() == val:
            return
        else:
            self._fullscreen_size = None
            self._is_fullscreen = val

            pygame.display.quit()
            self._update_display_mode()

    def set_opengl_mode(self, val):
        if self.is_opengl_mode() == val:
            return
        else:
            # in pygame 1.9.x, it blackscreens without this call when going from GL to non-GL
            pygame.display.quit()

            self._opengl_mode = val
            self._update_display_mode()

    def is_opengl_mode(self):
        return self._opengl_mode

    def window_to_screen_pos(self, pos):
        if pos is None:
            return None
        else:
            # screen is anchored at bottom left corner of window.
            # no real reason for that, it's just what happened
            if self.get_display_size()[1] < self._min_size[1]:
                dy = self._min_size[1] - self.get_display_size()[1]
            else:
                dy = 0
            return (pos[0], pos[1] + dy)

