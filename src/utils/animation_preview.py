
import time
import pygame


class _Config:

    def __init__(self):
        self.sheet_path = "../../assets/circuits.png"

        self.anim_xy = (64, 72)
        self.anim_size = (32, 24)
        self.n_frames = 8
        self.row_len = 1000

        self.bg_color = (0, 0, 0)

        self.reload_freq = 60  # reloads the sheet every N frames
        self.fps = 60

        self.anim_rects = [pygame.Rect(self.anim_xy[0] + (i % self.row_len) * self.anim_size[0],
                                       self.anim_xy[1] + (i // self.row_len) * self.anim_size[1],
                                       self.anim_size[0],
                                       self.anim_size[1]) for i in range(0, self.n_frames)]

        self.max_frame_width = 0.25
        self.min_frame_size = (16, 16)


class _State:

    def __init__(self, config: _Config):
        self.config = config
        self.sprite_sheet = None
        self.active_frame = 0
        self.anim_rate = 16  # ticks per frame
        self.paused = False

        self.tick_count = 0

        self.primary_rect = pygame.Rect(0, 0, 0, 0)
        self.frame_rects = []

    def update(self, screen: pygame.Surface):
        if self.tick_count % self.config.reload_freq == 0:
            self.sprite_sheet = None
        if self.sprite_sheet is None:
            self.reload_sheet(self.config.sheet_path)

        if not self.paused:
            if self.tick_count % self.anim_rate == 0:
                self.inc_frame(1)

        frame_zoom = self._calc_frame_zoom(screen)
        self.frame_rects.clear()
        for i in range(0, self.config.n_frames):
            self.frame_rects.append(pygame.Rect(0,
                                                i * self.config.anim_size[1] * frame_zoom,
                                                self.config.anim_size[0] * frame_zoom,
                                                self.config.anim_size[1] * frame_zoom))
            scaled_frame = scale_image(self.sprite_sheet, self.config.anim_rects[i], frame_zoom, self.config.bg_color)
            screen.blit(scaled_frame, self.frame_rects[i])
            if i == self.active_frame:
                pygame.draw.rect(screen, (255, 0, 0), self.frame_rects[i], 1)

        primary_zone = pygame.Rect(self.config.anim_size[0] * frame_zoom, 0,
                                   screen.get_width() - self.config.anim_size[0] * frame_zoom,
                                   screen.get_height())
        primary_zoom = self._calc_primary_zoom(primary_zone)
        scaled_primary = scale_image(self.sprite_sheet, self.config.anim_rects[self.active_frame],
                                     primary_zoom, self.config.bg_color)
        primary_x = primary_zone.x + primary_zone.width // 2 - scaled_primary.get_width() // 2
        primary_y = primary_zone.y + primary_zone.height // 2 - scaled_primary.get_height() // 2
        screen.blit(scaled_primary, (primary_x, primary_y))

        self.tick_count += 1

    def _calc_frame_zoom(self, screen):
        screen_size = screen.get_size()
        max_width = int(screen_size[0] * self.config.max_frame_width)
        max_height = screen_size[1] // self.config.n_frames

        if max_width < self.config.anim_size[0] or max_height < self.config.anim_size[1]:
            return 1  # window too small, just cram it
        else:
            max_horz_zoom = max_width / self.config.anim_size[0]
            max_vert_zoom = max_height / self.config.anim_size[1]
            return min(max_horz_zoom, max_vert_zoom)

    def _calc_primary_zoom(self, rect):
        max_horz_zoom = rect.width // self.config.anim_size[0]
        max_vert_zoom = rect.height // self.config.anim_size[1]
        return min(max_horz_zoom, max_vert_zoom)

    def toggle_paused(self):
        self.paused = not self.paused

    def set_paused(self, paused):
        self.paused = paused

    def inc_frame(self, val):
        self.active_frame = (self.active_frame + val) % self.config.n_frames

    def activate_frame(self, n):
        self.active_frame = n % self.config.n_frames

    def inc_anim_rate(self, val):
        self.anim_rate = min(32, max(4, self.anim_rate + val))

    def reload_sheet(self, sheet_path):
        n_tries = 10
        delay = 200
        for i in range(0, n_tries):
            try:
                self.sprite_sheet = pygame.image.load(sheet_path)
                return
            except Exception:
                pass
            time.sleep(delay / 1000)
        raise ValueError("failed to load {} after {} attempts".format(sheet_path, n_tries))


_TEMP_SHEETS = {}  # size -> sheet


def scale_image(src_sheet, src_rect: pygame.Rect, scale, bg_color) -> pygame.Surface:
    input_size = (src_rect.width, src_rect.height)
    if input_size not in _TEMP_SHEETS:
        _TEMP_SHEETS[input_size] = pygame.Surface(input_size, pygame.SRCALPHA, 32)

    unscaled_temp_sheet = _TEMP_SHEETS[input_size]
    unscaled_temp_sheet.fill(bg_color)
    unscaled_temp_sheet.blit(src_sheet, (0, 0), area=src_rect)

    output_size = (int(0.5 + src_rect.width * scale), int(0.5 + src_rect.height * scale))
    if output_size not in _TEMP_SHEETS:
        _TEMP_SHEETS[output_size] = pygame.Surface(output_size, pygame.SRCALPHA, 32)
    res = _TEMP_SHEETS[output_size]
    res.fill(bg_color)

    pygame.transform.scale(unscaled_temp_sheet, output_size, res)
    return res


if __name__ == "__main__":

    pygame.init()
    clock = pygame.time.Clock()

    screen = pygame.display.set_mode((640, 480), pygame.RESIZABLE | pygame.DOUBLEBUF)

    state = _State(_Config())

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE | pygame.DOUBLEBUF)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    state.toggle_paused()
                elif event.key in (pygame.K_DOWN, pygame.K_RIGHT, pygame.K_s, pygame.K_d):
                    state.set_paused(True)
                    state.inc_frame(1)
                elif event.key in (pygame.K_UP, pygame.K_LEFT, pygame.K_w, pygame.K_a):
                    state.set_paused(True)
                    state.inc_frame(-1)
                elif event.key == pygame.K_EQUALS:
                    state.inc_anim_rate(-4)
                elif event.key == pygame.K_MINUS:
                    state.inc_anim_rate(4)

        screen.fill(state.config.bg_color)

        state.update(screen)

        clock.tick(60)
        pygame.display.flip()

    pygame.quit()