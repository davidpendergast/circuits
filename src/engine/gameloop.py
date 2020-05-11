import pygame

from src.utils.util import Utils
import src.engine.sounds as sounds
import src.engine.window as window
import src.engine.inputs as inputs

import src.engine.renderengine as renderengine
import src.engine.spritesheets as spritesheets
import src.engine.globaltimer as globaltimer
import configs


_INSTANCE = None


def create_instance(game):
    global _INSTANCE
    if _INSTANCE is not None:
        raise ValueError("a game loop has already been created")
    else:
        _INSTANCE = _GameLoop(game)
        return _INSTANCE


class _GameLoop:

    def __init__(self, game):
        self._game = game
        self._clock = pygame.time.Clock()

        print("INFO: pygame version: " + pygame.version.ver)
        print("INFO: initializing sounds...")
        pygame.mixer.pre_init(44100, -16, 1, 2048)

        pygame.mixer.init()
        pygame.init()

        window_icon = pygame.image.load(Utils.resource_path("assets/icon.png"))
        pygame.display.set_icon(window_icon)

        window.create_instance(window_size=configs.default_window_size, min_size=configs.minimum_window_size)
        window.get_instance().set_caption(configs.name_of_game)
        window.get_instance().show()

        render_eng = renderengine.create_instance()
        render_eng.init(*configs.default_window_size)
        render_eng.set_min_size(*configs.minimum_window_size)

        sprite_atlas = spritesheets.create_instance()
        for sheet in self._game.create_sheets():
            sprite_atlas.add_sheet(sheet)

        atlas_surface = sprite_atlas.create_atlas_surface()

        # uncomment to save out the full texture atlas
        # pygame.image.save(atlas_surface, "texture_atlas.png")

        texture_data = pygame.image.tostring(atlas_surface, "RGBA", 1)
        width = atlas_surface.get_width()
        height = atlas_surface.get_height()
        render_eng.set_texture(texture_data, width, height)

        for layer in self._game.create_layers():
            renderengine.get_instance().add_layer(layer)

        inputs.create_instance()

        px_scale = self._calc_pixel_scale(window.get_instance().get_display_size())
        render_eng.set_pixel_scale(px_scale)

    def _calc_pixel_scale(self, screen_size):
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

    def run(self):
        running = True

        ignore_resize_events_next_tick = False

        while running:
            # processing user input events
            all_resize_events = []

            input_state = inputs.get_instance()
            for py_event in pygame.event.get():
                if py_event.type == pygame.QUIT:
                    running = False
                    continue
                elif py_event.type == pygame.KEYDOWN:
                    input_state.set_key(py_event.key, True)
                elif py_event.type == pygame.KEYUP:
                    input_state.set_key(py_event.key, False)

                elif py_event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                    scr_pos = window.get_instance().window_to_screen_pos(py_event.pos)
                    game_pos = Utils.round(Utils.mult(scr_pos, 1 / renderengine.get_instance().get_pixel_scale()))
                    input_state.set_mouse_pos(game_pos)

                    if py_event.type == pygame.MOUSEBUTTONDOWN:
                        input_state.set_mouse_down(True, button=py_event.button)
                    elif py_event.type == pygame.MOUSEBUTTONUP:
                        input_state.set_mouse_down(False, button=py_event.button)

                elif py_event.type == pygame.VIDEORESIZE:
                    all_resize_events.append(py_event)

                if not pygame.mouse.get_focused():
                    input_state.set_mouse_pos(None)

            ignore_resize_events_this_tick = ignore_resize_events_next_tick
            ignore_resize_events_next_tick = False

            if input_state.was_pressed(pygame.K_F4) and configs.allow_fullscreen:
                win = window.get_instance()
                win.set_fullscreen(not win.is_fullscreen())

                new_size = win.get_display_size()
                new_pixel_scale = self._calc_pixel_scale(new_size)
                if new_pixel_scale != renderengine.get_instance().get_pixel_scale():
                    renderengine.get_instance().set_pixel_scale(new_pixel_scale)
                renderengine.get_instance().resize(new_size[0], new_size[1], px_scale=new_pixel_scale)

                # when it goes from fullscreen to windowed mode, pygame sends a VIDEORESIZE event
                # on the next frame that claims the window has been resized to the maximum resolution.
                # this is annoying so we ignore it. we want the window to remain the same size it was
                # before the fullscreen happened.
                ignore_resize_events_next_tick = True

            if not ignore_resize_events_this_tick and len(all_resize_events) > 0:
                last_resize_event = all_resize_events[-1]

                window.get_instance().set_window_size(last_resize_event.w, last_resize_event.h)

                display_w, display_h = window.get_instance().get_display_size()
                new_pixel_scale = self._calc_pixel_scale((last_resize_event.w, last_resize_event.h))

                renderengine.get_instance().resize(display_w, display_h, px_scale=new_pixel_scale)

            if configs.is_dev and input_state.was_pressed(pygame.K_F1):
                # used to help find performance bottlenecks
                import src.utils.profiling as profiling
                profiling.get_instance().toggle()

            input_state.update()
            sounds.update()

            # updates the actual game state
            self._game.update()

            # draws the actual game state
            for spr in self._game.all_sprites():
                if spr is not None:
                    renderengine.get_instance().update(spr)

            renderengine.get_instance().set_clear_color(configs.clear_color)
            renderengine.get_instance().render_layers()

            pygame.display.flip()

            slo_mo_mode = configs.is_dev and input_state.is_held(pygame.K_TAB)
            target_fps = configs.target_fps if not slo_mo_mode else configs.target_fps // 4

            self._wait_until_next_frame(target_fps)

            globaltimer.inc_tick_count()

            if globaltimer.tick_count() % configs.target_fps == 0:
                if globaltimer.get_fps() < 0.9 * configs.target_fps and configs.is_dev and not slo_mo_mode:
                    print("WARN: fps drop: {} ({} sprites)".format(round(globaltimer.get_fps() * 10) / 10.0,
                                                                   renderengine.get_instance().count_sprites()))

        print("INFO: quitting game")
        pygame.quit()

    def _wait_until_next_frame(self, target_fps):
        if configs.precise_fps:
            self._clock.tick_busy_loop(target_fps)
        else:
            self._clock.tick(target_fps)






