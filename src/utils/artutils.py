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


if __name__ == "__main__":
    test_img = pygame.image.load("planning/mockup_5.png")
    output_img_path = "planning/mockup_5_mazified.png"

    blue = colors.to_int(colors.BLUE)
    green = colors.to_int(colors.GREEN)
    tan = colors.to_int(colors.TAN)
    purple = colors.to_int(colors.PURPLE)

    avoid_colors = [colors.to_int(colors.PERFECT_BLACK)]

    colors_to_mazify = [blue, green, tan, purple]
    print("colors_to_mazify={}".format(colors_to_mazify))

    pcnts = (-0.6, -0.5, 0.3, 0.4, 0.5)

    color_shifts = {
        blue: [darker(blue, pcnt=v) for v in pcnts],
        green: [darker(green, pcnt=v) for v in pcnts],
        tan: [darker(tan, pcnt=v) for v in pcnts],
        purple: [darker(purple, pcnt=v) for v in pcnts]
    }

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
