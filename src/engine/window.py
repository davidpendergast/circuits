
import pygame
import configs


_INSTANCE = None


def create_instance(window_size=(640, 480), min_size=(0, 0)):
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = WindowState(window_size, min_size=min_size)
        return _INSTANCE
    else:
        raise ValueError("There is already a WindowState initialized.")


def get_instance() -> 'WindowState':
    return _INSTANCE


class WindowState:

    def __init__(self, window_size, min_size=(0, 0)):
        self._is_fullscreen = False
        self._window_size = window_size
        self._min_size = min_size

        self._fullscreen_size = None

        self._caption = "Game"
        self._caption_info = {}  # str -> str, for example "FPS" -> "60.0"
        self._icon_surface = None  # pygame.Surface

    def _get_mods(self):
        mods = pygame.OPENGL | pygame.DOUBLEBUF

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

        import src.engine.renderengine as renderengine
        render_eng = renderengine.get_instance()
        if render_eng is not None:
            # XXX otherwise everything breaks on Windows (see docs on this method)
            render_eng.reset_for_display_mode_change(new_surface)

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

    def _update_caption(self):
        cap = self._caption
        if len(self._caption_info) > 0:
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
        self._update_display_mode()

    def is_fullscreen(self):
        return self._is_fullscreen

    def set_fullscreen(self, val):
        if self.is_fullscreen() == val:
            return
        else:
            self._fullscreen_size = None
            self._is_fullscreen = val

            if self._is_fullscreen:
                pygame.display.quit()

            self._update_display_mode()

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

