import pygame
import random
from collections import deque

import src.utils.util as util
import src.game.colors as colors


def save_to_png(surface: pygame.Surface, filepath):
    pygame.image.save(surface, filepath)


def bft(start_pos, cond, with_diags=False, bound_rect=None, rng_seed=None):
    """breadth-first traverse"""
    seen = set()
    q = deque()
    seen.add(start_pos)
    q.append(start_pos)

    if rng_seed is not None:
        random.seed(rng_seed)

    while len(q) > 0:
        n = q.pop()
        if cond(n):
            yield n

            neighbors = [m for m in util.neighbors(n[0], n[1], and_diags=with_diags)]
            if rng_seed is not None:
                random.shuffle(neighbors)

            for m in neighbors:
                if m not in seen and (bound_rect is None or util.rect_contains(bound_rect, m)):
                    q.append(m)
                seen.add(m)


def rm_alpha(color):
    if len(color) == 4:
        return (color[0], color[1], color[2])
    else:
        return color


def add_alpha(color):
    if len(color) == 3:
        return (color[0], color[1], color[2], 255)
    else:
        return color


def flood_fill(surface: pygame.Surface, target_colors, start_pos, bound_rect=None, rng_seed=None):
    bound_rect = _make_bound_for_surface(surface, bound_rect)

    def _cond(xy):
        color = rm_alpha(tuple(surface.get_at(xy)))
        return color in target_colors

    return [p for p in bft(start_pos, _cond, bound_rect=bound_rect, rng_seed=rng_seed)]


def maze_fill(surface: pygame.Surface, target_colors, start_pos,
              avoid_colors=None, density=1.0, rng_seed=None, bound_rect=None):

    bound_rect = _make_bound_for_surface(surface, bound_rect)
    domain = [pt for pt in flood_fill(surface, target_colors, start_pos,
                                      bound_rect=bound_rect, rng_seed=rng_seed)]
    filled = set()

    for n in domain:
        if avoid_colors is not None:
            should_skip = False
            for m in util.neighbors(n[0], n[1], and_diags=True):
                if util.rect_contains(bound_rect, m):
                    m_color = rm_alpha(tuple(surface.get_at(m)))
                    if m_color in avoid_colors:
                        should_skip = True
                        break
            if should_skip:
                continue

        total_connection_count = len([n for n in util.neighbors(n[0], n[1], and_diags=True) if n in filled])
        if total_connection_count == 0:
            if random.random() < density:
                filled.add(n)
        else:
            skip = False
            for m in util.diag_neighbors(n[0], n[1]):
                if m in filled:
                    bridge1 = (n[0], m[1])
                    bridge2 = (m[0], n[1])
                    if (bridge1 in filled) is (bridge2 in filled):
                        skip = True
                        break
            if skip:
                continue
            else:
                # the position is valid to fill
                ortho_connection_count = len([n for n in util.neighbors(n[0], n[1], and_diags=False) if n in filled])
                fill_chance = density * (1 - ortho_connection_count / 4)
                if random.random() < fill_chance:
                    filled.add(n)
    return filled


def find_color_regions(surface: pygame.Surface, bound_rect=None, colors_to_include=None):
    bound_rect = _make_bound_for_surface(surface, bound_rect)
    res = {}  # color -> list of sets of (x, y)

    all_points = set()
    for x in range(bound_rect[0], bound_rect[0] + bound_rect[2]):
        for y in range(bound_rect[1], bound_rect[1] + bound_rect[3]):
            all_points.add((x, y))

    if colors_to_include is not None:
        for c in colors_to_include:
            res[c] = []

    while len(all_points) > 0:
        pt = all_points.pop()
        pt_color = rm_alpha(tuple(surface.get_at(pt)))

        if colors_to_include is not None and pt_color not in colors_to_include:
            continue
        if pt_color not in res:
            res[pt_color] = []
        region = set()
        for r in flood_fill(surface, [pt_color], pt, bound_rect=bound_rect):
            region.add(r)
            if r in all_points:
                all_points.remove(r)
        res[pt_color].append(region)

    return res


def _make_bound_for_surface(surface: pygame.Surface, bound_rect):
    max_rect = [0, 0, surface.get_width(), surface.get_height()]
    if bound_rect is None:
        return max_rect
    else:
        return util.get_rect_intersect(bound_rect, max_rect)


def region_color_fill(surface: pygame.Surface, regions, color_provider):
    """
    :param color_provider: lambda region -> color
    """
    for reg in regions:
        color = color_provider(reg)
        for r in reg:
            surface.set_at(r, add_alpha(color))


def darker(color, pcnt=0.2):
    if pcnt < 0:
        return lighter(color, pcnt=-pcnt)
    res = []
    for c in color:
        res.append(max(0, min(255, int(c * (1 - pcnt)))))
    return tuple(res)


def lighter(color, pcnt=0.2):
    if pcnt < 0:
        return darker(color, pcnt=-pcnt)
    res = []
    for c in color:
        dist = 255 - c
        new_dist = int(dist) * (1 - pcnt)
        res.append(max(0, min(255, int(255 - new_dist))))
    return tuple(res)


def is_transparent(color):
    if len(color) < 4:
        return False
    else:
        return color[2] == 0


def find_bounding_rect(search_rect, sheet, keep_horz=False, keep_vert=False):
    if keep_horz and keep_vert:
        return search_rect

    min_x = None
    min_y = None
    max_x = None
    max_y = None

    if keep_horz:
        min_x = search_rect[0]
        max_x = search_rect[0] + search_rect[2] - 1

    if keep_vert:
        min_y = search_rect[1]
        max_y = search_rect[1] + search_rect[3] - 1

    sheet_size = sheet.get_size()
    sheet.lock()
    for x in range(search_rect[0], search_rect[0] + search_rect[2]):
        for y in range(search_rect[1], search_rect[1] + search_rect[3]):
            if 0 <= x < sheet_size[0] and 0 <= y < sheet_size[1]:
                color = sheet.get_at((x, y))
                if not is_transparent(color):
                    if min_x is None:
                        min_x = x
                        max_x = x
                    else:
                        min_x = min(x, min_x)
                        max_x = max(x, max_x)

                    if min_y is None:
                        min_y = y
                        max_y = y
                    else:
                        min_y = min(y, min_y)
                        max_y = max(y, max_y)
    sheet.unlock()

    if min_x is None and min_y is None:
        return [search_rect[0], search_rect[1], 0, 0]
    elif min_x is None:
        return [search_rect[0], min_y, 0, max_y - min_y + 1]
    elif min_y is None:
        return [min_x, search_rect[1], max_x - min_x + 1, 0]
    else:
        return [min_x, min_y, max_x - min_x + 1, max_y - min_y + 1]


def draw_decay_animation_effect(src_sheet, src_rect, n_frames, dest_sheet, dest_rect_provider,
                                full_decay_rect_provider, partial_decay_rect_provider,
                                decay_chance_provider=lambda i, xy: 0.05):
    """
    src_sheet: Surface containing the source image
    src_rect: Location of the source image
    n_frames: Number of frames to draw
    dest_sheet: Surface to draw the decayed images
    dest_rect_provider: frm_idx -> rect
    full_decay_rect_provider: frm_idx -> rect
    partial_decay_rect_provider: frm_idx -> rect
    decay_chance_provider: frm_idx, xy -> rect

    returns: list of dest rects drawn
    """
    res = []
    decayed = set()  # set of decayed pixels
    for i in range(0, n_frames):
        dest_rect = dest_rect_provider(i)
        full_decay_rect = full_decay_rect_provider(i)
        partial_decay_rect = partial_decay_rect_provider(i)

        for x in range(0, min(dest_rect[2], src_rect[2])):
            for y in range(0, min(dest_rect[3], src_rect[3])):
                src_xy = (src_rect[0] + x, src_rect[1] + y)
                if src_xy in decayed:
                    continue
                elif util.rect_contains(full_decay_rect, src_xy):
                    decayed.add(src_xy)
                    continue
                elif util.rect_contains(partial_decay_rect, src_xy):
                    decay_chance = decay_chance_provider(i, src_xy)
                    if random.random() < decay_chance:
                        decayed.add(src_xy)
                        continue

                color = src_sheet.get_at(src_xy)
                dest_xy = (dest_rect[0] + x, dest_rect[1] + y)
                dest_sheet.set_at(dest_xy, color)

        res.append(dest_rect)
    return res


if __name__ == "__main__":
    test_img = pygame.image.load("planning/mockup_5.png")
    output_img_path = "planning/mockup_5_mazified_bg.png"

    blue = colors.to_int(colors.BLUE)
    green = colors.to_int(colors.GREEN)
    tan = colors.to_int(colors.TAN)
    purple = colors.to_int(colors.PURPLE)
    black = colors.to_int(colors.PERFECT_BLACK)
    red = (70, 25, 25)

    avoid_colors = [colors.to_int(colors.PERFECT_BLACK)]
    # avoid_colors = [blue, green, tan, purple]

    pcnts = (-0.3, 0.35, 0.5)
    pcnts = (0.1, 0.15, 0.2, 0.25)

    color_shifts = {
        # blue: [darker(blue, pcnt=v) for v in pcnts],
        # green: [darker(green, pcnt=v) for v in pcnts],
        # tan: [darker(tan, pcnt=v) for v in pcnts],
        # purple: [darker(purple, pcnt=v) for v in pcnts]
        # black: [lighter(red, pcnt=v) for v in pcnts]
        blue: [black],
        green: [black],
        tan: [black],
        purple: [black],
    }

    colors_to_mazify = [c for c in color_shifts]

    base_regions = find_color_regions(test_img, colors_to_include=colors_to_mazify)

    for c in colors_to_mazify:
        fill_color = (255, 0, 0)
        for reg in base_regions[c]:
            target_colors = [c]
            start_pos = random.choice([pt for pt in reg])

            to_fill = maze_fill(test_img, target_colors, start_pos,
                                avoid_colors=avoid_colors, rng_seed=123545, density=0.99)
            for pt in to_fill:
                test_img.set_at(pt, add_alpha(fill_color))

        maze_regions = find_color_regions(test_img, colors_to_include=[fill_color])[fill_color]
        # region_color_fill(test_img, maze_regions, lambda r: random.choice(color_shifts[c]))
        for reg in maze_regions:
            color = random.choice(color_shifts[c])
            print("INFO: filling region with color: {} {}".format(color, reg))
            for r in reg:
                test_img.set_at(r, add_alpha(color))

    pygame.image.save(test_img, output_img_path)