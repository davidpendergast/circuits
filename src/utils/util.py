import math
import random
import os
import json
import re
import sys
import heapq
import traceback
import copy

import appdirs


def bound(val, lower, upper):
    if upper is not None and val > upper:
        return upper
    elif lower is not None and val < lower:
        return lower
    else:
        return val


def signum(val):
    return (val > 0) - (val < 0)


def next_power_of_2(val):
    return 1 if val <= 0 else 2 ** math.ceil(math.log2(val))


def add(v1, v2):
    return tuple(i[0] + i[1] for i in zip(v1, v2))


def sum_vecs(v_list):
    if len(v_list) == 0:
        raise ValueError("can't sum 0 vectors")
    else:
        res = []
        for v in v_list:
            for i in range(0, len(v)):
                if i >= len(res):
                    res.append(v[i])
                else:
                    res[i] += v[i]
        return tuple(res)


def sub(v1, v2):
    return tuple(i[0] - i[1] for i in zip(v1, v2))


def negate(v, components=None):
    return tuple(-v[i] if (components is None or i in components) else v[i] for i in range(0, len(v)))


def mult(v, a):
    return tuple(a*v_i for v_i in v)


def average(v_list):
    if len(v_list) == 0:
        raise ValueError("cannot take average of 0 vectors.")
    n = len(v_list[0])
    if n == 0:
        return tuple()

    sum_v = [0 for _ in range(0, n)]
    for v in v_list:
        for i in range(0, n):
            sum_v[i] = sum_v[i] + v[i]

    return mult(sum_v, 1 / len(v_list))


def rotate(v, rad):
    cos = math.cos(rad)
    sin = math.sin(rad)
    return (v[0]*cos - v[1]*sin, v[0]*sin + v[1]*cos)


def angle_between(v1, v2, signed=False, vn=(0, 0, 1)):
    v1_dot_v2 = dot_prod(v1, v2)
    mag1 = mag(v1)
    mag2 = mag(v2)
    if mag1 == 0 or mag2 == 0:
        return 0
    else:
        angle = math.acos(v1_dot_v2 / (mag1 * mag2))
        if signed:
            cross = cross_prod(v1, v2)
            if dot_prod(cross, vn) <= 0:
                angle = -angle
        return angle

def rotate_towards(v1, v2, rad):
    if angle_between(v1, v2) == 0:
        return v1
    else:
        # https://en.wikipedia.org/wiki/Rodrigues%27_rotation_formula
        k = set_length(cross_prod(v1, v2), 1)
        v1_cos_theta = mult(v1, math.cos(rad))
        k_cross_v1_sin_theta = mult(cross_prod(k, v1), math.sin(rad))
        k_k_dot_v1 = mult(k, dot_prod(k, v1))

        t = add(v1_cos_theta, k_cross_v1_sin_theta)
        return add(t, mult(k_k_dot_v1, (1 - math.cos(rad))))


def cardinal_direction_between(from_xy, to_xy):
    """example: (0, 0) to (5, -6) would give (1, -1)"""
    return tuple(signum(v) for v in sub(to_xy, from_xy))


def to_degrees(rads):
    return rads * 180 / 3.141529


def to_rads(degrees):
    return degrees * 3.141529 / 180


def set_length(v, length):
    cur_length = mag(v)
    if cur_length == 0:
        return rand_vec(length, size=len(v))
    else:
        return mult(v, length / cur_length)


def mag(v):
    return math.sqrt(sum(i*i for i in v))


def dist(v1, v2):
    return mag(sub(v1, v2))


def dist_manhattan(v1, v2):
    res = 0
    for i, j in zip(v1, v2):
        res += abs(i - j)
    return res


def rand_vec(length=1, size=2):
    if size == 1:
        return [length * 1 if random.random() < 0.5 else -1]
    elif size == 2:
        theta = 6.2832 * random.random()
        return [length * math.cos(theta),
                length * math.sin(theta)]
    elif size == 3:
        theta = 6.2832 * random.random()
        phi = 3.1415 * random.random()
        return spherical_to_cartesian(length, theta, phi)
    else:
        raise ValueError("todo - implement algorithm that finds a random point on an n-sphere")


def spherical_to_cartesian(r, theta, phi):
    return [
        r * math.sin(phi) * math.cos(theta),
        r * math.sin(phi) * math.sin(theta),
        r * math.cos(phi)
    ]


def cartesian_to_spherical(v):
    r = mag(v)
    if r == 0:
        return (0, 0, 0)
    else:
        phi = math.atan2(mag((v[0], v[1])), v[2])
        theta = math.atan2(v[1], v[0])
        return (r, theta, phi)


def interpolate_spherical(v1, v2, a):
    r1, theta1, phi1 = cartesian_to_spherical(v1)
    r2, theta2, phi2 = cartesian_to_spherical(v2)
    return spherical_to_cartesian(linear_interp(r1, r2, a),
                                  linear_interp(theta1, theta2, a),
                                  linear_interp(phi1, phi2, a))


def rect_expand(rect, all_expand=0, left_expand=0, right_expand=0, up_expand=0, down_expand=0):
    return [rect[0] - left_expand - all_expand,
            rect[1] - up_expand - all_expand,
            rect[2] + (left_expand + right_expand + 2 * all_expand),
            rect[3] + (up_expand + down_expand + 2 * all_expand)]


def rect_contains(rect, v_or_rect):
    if len(v_or_rect) == 4:
        r = v_or_rect
        return (rect[0] <= r[0] <= rect[0] + rect[2] - r[2] and
                rect[1] <= r[1] <= rect[1] + rect[3] - r[3])
    else:
        v = (v_or_rect[0], v_or_rect[1])
        return rect[0] <= v[0] < rect[0] + rect[2] and rect[1] <= v[1] < rect[1] + rect[3]


def constrain_point_to_rect(rect, p):
    px = bound(p[0], rect[0], rect[0] + rect[2] - 1)
    py = bound(p[1], rect[1], rect[1] + rect[3] - 1)
    return (px, py)


def rect_center(rect):
    return (int(rect[0] + rect[2] / 2),
            int(rect[1] + rect[3] / 2))


def all_rect_corners(rect, inclusive=False):
    yield (rect[0], rect[1])
    if inclusive:
        if rect[2] == 0 or rect[3] == 0:
            if rect[2] > 0:
                yield (rect[0] + rect[2] - 1, rect[1])
            elif rect[3] > 0:
                yield (rect[0], rect[1] + rect[3] - 1)
        else:
            yield (rect[0] + rect[2] - 1, rect[1])
            yield (rect[0], rect[1] + rect[3] - 1)
            yield (rect[0] + rect[2] - 1, rect[1] + rect[3] - 1)
    else:
        yield (rect[0] + rect[2], rect[1])
        yield (rect[0], rect[1] + rect[3])
        yield (rect[0] + rect[2], rect[1] + rect[3])


def get_rect_intersect(rect1, rect2):
    x1 = max(rect1[0], rect2[0])
    x2 = min(rect1[0] + rect1[2], rect2[0] + rect2[2])
    y1 = max(rect1[1], rect2[1])
    y2 = min(rect1[1] + rect1[3], rect2[1] + rect2[3])
    if x1 >= x2 or y1 >= y2:
        return None
    else:
        return get_rect_containing_points([(x1, y1), (x2, y2)])


def rects_intersect(rect1, rect2):
    return get_rect_intersect(rect1, rect2) is not None


def get_rect_containing_points(pts, inclusive=False):
    if len(pts) == 0:
        raise ValueError("pts is empty")
    else:
        min_x = pts[0][0]
        max_x = pts[0][0]
        min_y = pts[0][1]
        max_y = pts[0][1]

        for pt in pts:
            min_x = min(min_x, pt[0])
            max_x = max(max_x, pt[0])
            min_y = min(min_y, pt[1])
            max_y = max(max_y, pt[1])

        if inclusive:
            max_x += 1
            max_y += 1

        return [min_x, min_y, (max_x - min_x), (max_y - min_y)]


def rect_union(rect_list):
    all_points = []
    for r in rect_list:
        if r[2] > 0 and r[3] > 0:
            all_points.append((r[0], r[1]))
            all_points.append((r[0] + r[2], r[1] + r[3]))
    if len(all_points) == 0:
        return None
    else:
        return get_rect_containing_points(all_points, inclusive=False)


def _new_bound_size(existing_rects, new_rect):
    min_x = new_rect[0]
    max_x = new_rect[0] + new_rect[2]
    min_y = new_rect[1]
    max_y = new_rect[1] + new_rect[3]
    for r in existing_rects:
        if get_rect_intersect(r, new_rect) is not None:
            return None
        else:
            min_x = min(min_x, r[0])
            max_x = max(max_x, r[0] + r[2])
            min_y = min(min_y, r[1])
            max_y = max(max_y, r[1] + r[3])

    return (max_x - min_x, max_y - min_y)


def _get_new_roots(existing_rects, new_rect):
    res = [(new_rect[0], new_rect[1] + new_rect[3]),    # bottom left
           (new_rect[0] + new_rect[2], new_rect[1])]    # top right
    for r in existing_rects:
        if new_rect[0] < r[0] + r[2] < new_rect[0] + new_rect[2]:
            if r[1] < new_rect[1]:
                res.append((new_rect[0] + new_rect[2], r[1]))
            else:
                res.append((r[0] + r[2], new_rect[1]))
        if new_rect[1] < r[1] + r[3] < new_rect[3]:
            if r[0] < new_rect[0]:
                res.append((r[0], new_rect[1] + new_rect[3]))
            else:
                res.append((new_rect[0] + new_rect[2], r[1] + r[3]))
    return res


def pack_rects_into_smallest_rect(rect_sizes):
    """
    Note that this is very O(n^2)
    :param rect_sizes: list of non-empty sizes (w, h)
    :return: (
                list of rects (x, y, w, h) that are packed into a "minimal" bounding rect,
                (w, h) the total bound size
             )
    """
    sizes = [r for r in rect_sizes]
    sizes.sort(key=lambda s: s[0] * s[1], reverse=True)

    roots = set()
    roots.add((0, 0))

    total_bound = (0, 0)

    res = []

    for s in sizes:
        if s[0] <= 0 or s[1] <= 0:
            raise ValueError("invalid rect size: {}".format(s))
        else:
            best_root = None
            best_new_bound = None

            for root in roots:
                candidate_rect = [root[0], root[1], s[0], s[1]]
                new_bound = _new_bound_size(res, candidate_rect)
                if new_bound is not None:  # it fits
                    if best_new_bound is None or new_bound[0] * new_bound[1] < best_new_bound[0] * best_new_bound[1]:
                        best_new_bound = new_bound
                        best_root = root

            if best_root is None:
                # only possible if i messed this up
                raise ValueError("can't fit {} in any roots: {}".format(s, roots))
            else:
                new_rect = [best_root[0], best_root[1], s[0], s[1]]
                new_roots = _get_new_roots(res, new_rect)
                for root in new_roots:
                    roots.add(root)
                roots.remove(best_root)
                res.append(new_rect)
                total_bound = best_new_bound

    return res, total_bound


def shift_bounding_rect_to(v_list, pos=(0, 0)):
    rect = get_rect_containing_points(v_list)
    return [(v[0] - rect[0] + pos[0], v[1] - rect[1] + pos[1]) for v in v_list]


def circle_contains(center, radius, pt):
    return dist(center, pt) <= radius


def dot_prod(p1, p2):
    if isinstance(p1, int) or isinstance(p1, float):
        return p1 * p2
    else:
        return sum(i1 * i2 for (i1, i2) in zip(p1, p2))


def cross_prod(v1, v2):
    a1 = v1[0] if len(v1) >= 1 else 0
    a2 = v1[1] if len(v1) >= 2 else 0
    a3 = v1[2] if len(v1) >= 3 else 0

    b1 = v2[0] if len(v2) >= 1 else 0
    b2 = v2[1] if len(v2) >= 2 else 0
    b3 = v2[2] if len(v2) >= 3 else 0

    return (det2x2(a2, a3, b2, b3),
            det2x2(a1, a3, b1, b3),
            det2x2(a1, a2, b1, b2))


def dist_from_point_to_line(p, l1, l2):
    return mag(vector_from_point_to_line(p, l1, l2))


def dist_from_point_to_rect(p, rect):
    if rect_contains(rect, p):
        return 0
    elif rect[0] <= p[0] <= rect[0] + rect[2]:
        # it's directly above or below the rect
        return min(abs(rect[1] - p[1]), abs(rect[1] + rect[3] - p[1]))
    elif rect[1] <= p[1] <= rect[1] + rect[3]:
        # it's directly left or right of the rect
        return min(abs(rect[0] - p[0]), abs(rect[0] + rect[2] - p[0]))
    else:
        return min([mag(sub(p, c)) for c in all_rect_corners(rect)])


def vector_from_point_to_line(p, l1, l2):
    if l1 == l2:
        return sub(p, l1)  # kind of a lie
    else:
        a = l1
        n = set_length(sub(l2, a), 1)  # unit vector along line

        # copied from wikipedia "Distance from a point to a line: Vector formulation"
        a_minus_p = sub(a, p)
        n_with_a_useful_length = set_length(n, dot_prod(a_minus_p, n))
        return sub(a_minus_p, n_with_a_useful_length)


def det2x2(a, b, c, d):
    return a * d - b * c


def line_line_intersection(xy1, xy2, xy3, xy4):
    x1, y1 = xy1
    x2, y2 = xy2
    x3, y3 = xy3
    x4, y4 = xy4

    det = det2x2

    denominator = det(
        det(x1,  1, x2, 1),
        det(y1,  1, y2, 1),
        det(x3,  1, x4, 1),
        det(y3,  1, y4, 1)
    )

    if denominator == 0:
        # lines are parallel
        return None

    p_x_numerator = det(
        det(x1, y1, x2, y2),
        det(x1,  1, x2,  1),
        det(x3, y3, x4, y4),
        det(x3,  1, x4,  1)
    )

    p_y_numerator = det(
        det(x1, y1, x2, y2),
        det(y1,  1, y2, 1),
        det(x3, y3, x4, y4),
        det(y3,  1, y4, 1)
    )

    return (p_x_numerator / denominator,
            p_y_numerator / denominator)


def projection(v1, v2):
    """finds the vector projection of v1 onto v2, or None if it doesn't exist"""
    v2_mag = mag(v2)
    if v2_mag == 0:
        return None
    else:
        v1_dot_v2 = dot_prod(v1, v2)
        return set_length(v2, v1_dot_v2 / v2_mag)


def rejection(v1, v2):
    """finds the vector rejection of v1 onto v2, or None if it doesn't exist"""
    proj_v1_onto_v2 = projection(v1, v2)
    if proj_v1_onto_v2 is None:
        return None
    else:
        return sub(v1, proj_v1_onto_v2)


def linear_interp(v1, v2, a):
    if isinstance(v1, int) or isinstance(v1, float):
        return _lerp_num_safely(v1, v2, a)
    else:
        return tuple([_lerp_num_safely(v1[i], v2[i], a) for i in range(0, len(v1))])


def linear_interp_list(v_list, a, wrap=True):
    n = len(v_list)
    if n == 0:
        return ValueError("cannot interpolate between 0 items")
    elif n == 1 or a <= 0:
        return v_list[0]
    elif a >= 1:
        return v_list[0] if wrap else v_list[-1]
    else:
        if wrap:
            v_list += [v_list[0]]
        idx1 = int(a * n)
        idx2 = (idx1 + 1) % (n + 1)

        return linear_interp(v_list[idx1], v_list[idx2], a * n - idx1)


def _lerp_num_safely(n1, n2, a, tolerance=0.00001):
    if abs(n1 - n2) < tolerance:
        return (n1 + n2) / 2
    else:
        return n1 * (1 - a) + n2 * a


def smooth_interp(v1, v2, a):
    return linear_interp(v1, v2, 0.5 * (1 - math.cos(a * math.pi)))


def round_vec(v):
    return tuple([round(i) for i in v])


def sample_uniform(lower, upper):
    return lower + random.random() * (upper - lower)


def sample_triangular(lower, upper, center=None):
    # https://en.wikipedia.org/wiki/Triangular_distribution#Generating_triangular-distributed_random_variates
    a = lower
    b = upper
    if center is None:
        c = (upper + lower) / 2
    else:
        c = center

    u = random.random()
    if u < (c - a) / (b - a):
        return a + math.sqrt(u * (b - a) * (c - a))
    else:
        return b - math.sqrt((1 - u) * (b - a) * (b - c))


def replace_all_except(text, replace_txt, except_for=()):
    return "".join(x if (x in except_for) else replace_txt for x in text)


def listify(obj):
    if (isinstance(obj, list)):
        return obj
    elif (isinstance(obj, tuple)):
        return [e for e in obj]
    else:
        return [obj]


def tuplify(obj):
    if (isinstance(obj, tuple)):
        return obj
    elif (isinstance(obj, list)):
        return tuple(obj)
    else:
        return (obj,)


def add_repeats(l, item_counts, copy_func=lambda x: x):
    """add_repeats([a, b, c], [1, 2, 3]) --> [a, b, b, c, c, c]"""
    if len(l) != len(item_counts):
        raise ValueError("list length doesn't match length of item counts: {} != {}".format(len(l), len(item_counts)))
    else:
        res = []
        for i in range(len(l)):
            for _ in range(item_counts[i]):
                res.append(copy_func(l[i]))
        return res


def index_into(l, val, wrap=False):
    if wrap:
        if val < 0:
            val = val - int(val) + 1
        else:
            val = val - int(val)
    elif val <= 0:
        return l[0]
    elif val >= 1:
        return l[-1]

    return l[int(val * len(l))]


def min_component(v_list, i):
    res = None
    for v in v_list:
        if i < len(v):
            res = min(v[i], res) if res is not None else v[i]
    return res


def max_component(v_list, i):
    res = None
    for v in v_list:
        if i < len(v):
            res = max(v[i], res) if res is not None else v[i]
    return res


def flatten_list(l):
    return [x for x in _flatten_helper(l)]


def _flatten_helper(l):
    for x in l:
        if isinstance(x, list):
            for y in _flatten_helper(x):
                yield y
        else:
            yield x


def remove_all_from_list_in_place(l, elements):
    if len(l) == 0:
        return l

    rem_set = set(elements)
    last_element = len(l) - 1
    i = 0

    while i <= last_element:
        if l[i] in rem_set:
            while i <= last_element and l[last_element] in rem_set:
                last_element -= 1
            if i > last_element:
                break
            else:
                l[i] = l[last_element]
                last_element -= 1
        i += 1

    del l[(last_element + 1):]


def extend_or_empty_list_to_length(l, n, creator=None, in_place=True):
    if not in_place:
        l = list(l)
    while len(l) > n:
        l.pop(-1)
    while len(l) < n:
        l.append(None if creator is None else creator())
    return l


def cells_between(p1, p2, include_endpoints=True):
    if p1 == p2:
        return [tuple(p1)] if include_endpoints else []

    start = [p1[0] + 0.5, p1[1] + 0.5]
    end = [p2[0] + 0.5, p2[1] + 0.5]

    xy = [start[0], start[1]]
    step_dist = 0.1
    step_vec = set_length(sub(end, start), step_dist)

    res = []
    for i in range(0, int(dist(start, end) // step_dist)):
        xy[0] = xy[0] + step_vec[0]
        xy[1] = xy[1] + step_vec[1]
        cur_cell = (int(xy[0]), int(xy[1]))
        if len(res) > 0 and res[-1] == cur_cell:
            continue
        else:
            if cur_cell == p1 or cur_cell == p2:
                if include_endpoints:
                    res.append(cur_cell)
            else:
                res.append(cur_cell)

    return res


def line_segments_intersect(xy1, xy2, xy3, xy4) -> bool:
    pt = line_line_intersection(xy1, xy2, xy3, xy4)
    if pt is None:
        return False
    else:
        min_x1 = min(xy1[0], xy2[0])
        max_x1 = max(xy1[0], xy2[0])
        min_y1 = min(xy1[1], xy2[1])
        max_y1 = max(xy1[1], xy2[1])

        min_x2 = min(xy3[0], xy4[0])
        max_x2 = max(xy3[0], xy4[0])
        min_y2 = min(xy3[1], xy4[1])
        max_y2 = max(xy3[1], xy4[1])

        return ((min_x1 <= pt[0] <= max_x1) and (min_y1 <= pt[1] <= max_y1) and
                (min_x2 <= pt[0] <= max_x2) and (min_y2 <= pt[1] <= max_y2))


def same_side_of_line(xy1, xy2, pt1, pt2) -> bool:
    cp1 = cross_prod(sub(xy2, xy1), sub(pt1, xy1))
    cp2 = cross_prod(sub(xy2, xy1), sub(pt2, xy1))
    return dot_prod(cp1, cp2) >= 0  # no idea why this works


def triangle_area(tri):
    v1 = sub(tri[0], tri[1])
    v2 = sub(tri[0], tri[2])
    return mag(cross_prod(v1, v2)) / 2


def triangle_contains(tri, pt) -> bool:
    a, b, c = tri
    return (same_side_of_line(a, b, pt, c) and
            same_side_of_line(a, c, pt, b) and
            same_side_of_line(b, c, pt, a))


def triangles_intersect(tri1, tri2) -> bool:
    if triangle_area(tri1) == 0 or triangle_area(tri2) == 0:
        return False

    for p in tri1:
        if triangle_contains(tri2, p):
            return True
    for p in tri2:
        if triangle_contains(tri1, p):
            return True
    for i in range(0, 3):
        for j in range(0, 3):
            if line_segments_intersect(tri1[i], tri1[(i + 1) % 3], tri2[i], tri2[(i + 1) % 3]):
                return True
    return False


def is_triangle_degenerate(tri):
    if len(tri) != 3:
        return True
    else:
        return tri[0] == tri[1] or tri[1] == tri[2] or tri[2] == tri[0]


def triangle_angle(tri, idx):
    if is_triangle_degenerate(tri):
        return 0
    else:
        A = tri[idx]
        B = tri[(idx + 1) % 3]
        C = tri[(idx + 2) % 3]
        AB = sub(B, A)
        AC = sub(C, A)
        return angle_between(AB, AC)


def rect_intersects_triangle(rect, tri) -> bool:
    if rect[2] <= 0 or rect[3] <= 0:
        # rect is empty
        return False
    else:
        c1, c2, c3, c4 = (c for c in all_rect_corners(rect))
        return (triangles_intersect((c1, c2, c3), tri) or
                triangles_intersect((c4, c2, c3), tri))


def bfs(start_node, is_correct, get_neighbors,
        is_valid=lambda n: True, get_cost=lambda n: 0, limit=-1, find_path=False):
    """
    param start_node: starting node
    param is_correct: node -> bool
    param get_neighbors: node -> list of neighbors of node
    param is_valid: node -> bool, whether a node is valid to check
    param get_cost: node -> comparable (or None to evaluate nodes in an arbitrary order)
    param limit: maximum number of nodes to evaluate (or -1 to search indefinitely)
    param find_path: whether to return the entire solution path [start_node, ..., end_node]

    return: list: [start_node, ..., end_node] if the solution exists and find_path is True
            end_node if the solution exists and find_path is False
            None if no solution was found
    """
    if is_valid(start_node) and is_correct(start_node):
        return start_node if not find_path else [start_node]

    count = [0]
    seen = set()
    q = []

    prevs = {} if find_path else None  # node -> prev_node

    def add_to_queue(n, prev_n=None):
        if n in seen:
            return
        else:
            count[0] = count[0] + 1
            heapq.heappush(q, (get_cost(n), count[0], n))
            seen.add(n)
            if prevs is not None:
                prevs[n] = prev_n

    add_to_queue(start_node)

    end_node = None

    while len(q) > 0 and (limit < 0 or count[0] <= limit):
        _, _, node = heapq.heappop(q)
        if is_correct(node):
            end_node = node
            break
        else:
            for n in get_neighbors(node):
                if is_valid(n):
                    add_to_queue(n, node)

    if end_node is None or not find_path:
        return end_node
    else:
        path = [end_node]  # building it in reverse
        n = end_node
        while prevs[n] is not None:
            path.append(prevs[n])
            n = prevs[n]
        path.reverse()
        return path


def djikstras(nodes, connections, start_nodes):
    """
    param nodes: iterable of all nodes
    param connections: dict of node -> iterable of tuples (neighbor, distance)
    param start_nodes: starting node(s)
    return: dict of node -> tuple (distance from any start node, prev_node),
            with distance = float('inf') for nodes that can't be reached.
    """
    c = {}
    for n1 in connections:
        c[n1] = set()
        for n2_dist in connections[n1]:
            if n2_dist[1] < 0:
                raise ValueError("cannot have negative distances")
            c[n1].add((n2_dist[0], n2_dist[1]))

    res = {n: (float('inf'), None) for n in nodes}

    H = []  # min-heap of (total_dist, from_node, to_node)

    for s in start_nodes:
        res[s] = (0, None)
        if s in connections:
            for n2_dist in connections[s]:
                heapq.heappush(H, (n2_dist[1], s, n2_dist[0]))

            del connections[s]

    while len(H) > 0:
        d, n1, n2 = heapq.heappop(H)
        if d < res[n2][0]:
            res[n2] = (d, n1)
            if n2 in connections:
                for n3_dist in connections[n2]:
                    heapq.heappush(H, (d + n3_dist[1], n2, n3_dist[0]))
                del connections[n2]
        else:
            pass  # we've already found a better path for this node

    return res


def add_to_list(val, the_list):
    the_list.append(val)
    return val


def stringify_key(keycode):
    import pygame
    if keycode == pygame.K_LEFT:
        return "←"
    elif keycode == pygame.K_UP:
        return "↑"
    elif keycode == pygame.K_RIGHT:
        return "→"
    elif keycode == pygame.K_DOWN:
        return "↓"
    elif isinstance(keycode, str) and keycode.startswith("MOUSE_BUTTON_"):
        num = keycode.replace("MOUSE_BUTTON_", "")
        return "M{}".format(num)
    else:
        res = pygame.key.name(keycode)
        if len(res) == 1 and res.islower():
            return res.upper()
        else:
            return res


def stringify_keylist(keycodes, or_else=""):
    """returns: comma separated list of the given keys formatted as strings."""
    if len(keycodes) == 0:
        return or_else
    else:
        key_strings = [stringify_key(k) for k in keycodes]
        return ",".join(key_strings)


def parse_leading_int(text, or_else=-1):
    just_the_num = re.search(r"\d+", text).group()
    if just_the_num == "":
        return or_else
    else:
        return int(just_the_num)


def parse_ending_int(text, or_else=-1):
    just_the_num = re.search(r"\d+$", text).group()
    if just_the_num == "":
        return or_else
    else:
        return int(just_the_num)


def resource_path(relative_path):
    """ Get path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.normpath(os.path.join(base_path, relative_path))


_NAME_OF_GAME_FOR_USERDATA = None
_AUTHOR_FOR_USERDATA = None


def set_info_for_user_data_path(name_of_game, author):
    global _NAME_OF_GAME_FOR_USERDATA, _AUTHOR_FOR_USERDATA
    _NAME_OF_GAME_FOR_USERDATA = name_of_game
    _AUTHOR_FOR_USERDATA = author


def user_data_path(relative_path, forcelocal=False, local_subdir="userdata"):
    if forcelocal:
        return os.path.normpath(os.path.join(local_subdir, relative_path))
    else:
        if _NAME_OF_GAME_FOR_USERDATA is None or _AUTHOR_FOR_USERDATA is None:
            raise ValueError("Must call set_info_for_user_data_path(...) prior to user_data_path()")
        try:
            directory = appdirs.user_data_dir(appname=_NAME_OF_GAME_FOR_USERDATA,
                                              appauthor=_AUTHOR_FOR_USERDATA)
            return os.path.normpath(os.path.join(directory, relative_path))
        except Exception:
            print("ERROR: failed to get user's AppData directory...")
            traceback.print_exc()
            return None


def copy_json(json_blob):
    return copy.deepcopy(json_blob)


def load_json_from_path(filepath):
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
            return data
    except json.decoder.JSONDecodeError as e:
        print("ERROR: failed to load json from: {}".format(filepath))
        raise e


def save_json_to_path(json_blob, filepath, make_pretty=True):
    try:
        json_string = json.dumps(json_blob, indent=4, sort_keys=True)
    except (ValueError, TypeError) as e:
        print("ERROR: tried to save invalid json to file: {}".format(filepath))
        print("ERROR: json_blob: {}".format(json_blob))
        raise e

    if make_pretty:
        json_string = make_json_pretty(json_string)

    directory = os.path.dirname(filepath)
    if directory != "" and not os.path.exists(directory):
        os.makedirs(directory)

    with open(filepath, 'w') as outfile:
        outfile.write(json_string)


_paren_dict = {"(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{", "<": ">", ">": "<"}


def opposite_paren(paren_char):
    if paren_char in _paren_dict:
        return _paren_dict[paren_char]
    else:
        return paren_char


def make_json_pretty(json_string, _rm_newlines=True):
    """removes newlines between elements of innermost lists."""

    def find_close_paren(string, index, open='(', closed=')'):
        balance = 0
        for i in range(index, len(string)):
            if string[i] == open:
                balance += 1
            elif string[i] == closed:
                balance -= 1
            if balance == 0:
                return i
        raise ValueError("Unbalanced parenthesis in " + string)

    m = re.search('[({[]', json_string)
    if m is None:
        if _rm_newlines:
            # json_string has no inner collection, so remove all internal newlines
            res = re.sub("\s*,\s*", ", ", json_string)

            # remove leading and trailing whitespace
            res = re.sub("^\s*", "", res)
            res = re.sub("\s*$", "", res)
        else:
            res = json_string
    else:
        # TODO treat small lists like non-lists
        i = m.start(0)
        j = find_close_paren(json_string, i, json_string[i], opposite_paren(json_string[i]))
        substring = make_json_pretty(json_string[i + 1:j], True)

        res = json_string[:i + 1] + substring + make_json_pretty(json_string[j:], False)

    return res


def read_int(json_blob, key, default):
    return read_safely(json_blob, key, default, mapper=lambda x: int(x))


def read_string(json_blob, key, default):
    return read_safely(json_blob, key, default, mapper=lambda x: str(x))


def read_strings(json_blob, key, default):
    return read_list_safely(json_blob, key, default, item_mapper=lambda x: str(x))


def read_bool(json_blob, key, default):
    return read_safely(json_blob, key, default, mapper=lambda x: bool(x))


def read_map(json_blob, key, default):
    return default  # hmmm, one day~


def get_value_or_create_new(the_map, key, creator):
    if key not in the_map or the_map[key] is None:
        the_map[key] = creator()
    return the_map[key]


def prompt_question(question, accepted_answers=(), max_tries=3) -> str:
    n = 0
    try:
        while n < max_tries:
            print()
            if len(accepted_answers) == 0:
                return input("INPUT: {}\n".format(question))
            else:
                ans_str = "(" + "/".join(accepted_answers) + ")"
                answer = input("INPUT: {} {}\n".format(question, ans_str))
                if answer in accepted_answers:  # TODO should be case insensitive probably
                    return answer
                else:
                    print("ERROR: invalid response")
            n += 1
    except Exception:
        print("ERROR: failed to get user input")
        traceback.print_exc()

    return None


def assert_int(n, msg=None, error=True):
    if n != int(n):
        msg = "expected an integer: {}".format(n) if msg is None else msg
        if error:
            raise ValueError(msg)
        else:
            print("WARN: " + msg)
            return int(n)
    else:
        return int(n)


def parabola_height(vertex_y, x):
    """
    finds f(x) of the parabola for which f(0) = 0, f(0.5) = vertex_y, f(1.0) = 0
    """
    #  mmm delicious math
    a = -4 * vertex_y
    b = 4 * vertex_y
    return (a * x * x) + (b * x)


class JumpInfo:

    def __init__(self, H, T, g, vel):
        self.H = H
        self.T = T
        self.g = g
        self.vel = vel

    def __repr__(self):
        return "JumpInfo(H={}, T={}, g={}, vel={})".format(self.H, self.T, self.g, self.vel)


def calc_missing_jump_info(H=None, T=None, g=None, vel=None) -> JumpInfo:
    # fundamental equations:
    #   g * T + vel = 0
    #   H = (g / 4) * T ** 2 + vel / 2 * T

    if H is not None and H < 0:
        raise ValueError("H cannot be negative: {}".format(H))
    if g is not None and g >= 0:
        raise ValueError("g must be negative: {}".format(g))

    # TODO - currently only works for known H, T or known H, g
    # TODO - turns out it's not so trivial to (perfectly) solve a system of non-linear equations
    if H is not None and T is not None:
        a = -4 * H / (T * T)
        vel = -a * T
        g = a * 2
    elif H is not None and g is not None:
        a = g / 2
        T = math.sqrt(-4 * H / a)
        vel = -a * T
    else:
        raise NotImplementedError("currently only works for known H, T or known H, g")

    return JumpInfo(H, T, g, vel)


def get_shake_points(strength, duration, falloff=3, freq=6):
    """
    int strength: max pixel offset of shake
    int duration: ticks for which the shake will remain active
    int freq: "speed" of the shake. 1 is really fast, higher is slower
    """

    if duration % freq != 0:
        duration += freq - (duration % freq)

    decay = lambda t: math.exp(-falloff*(t / duration))
    num_keypoints = int(duration / freq)
    x_pts = [round(2 * (0.5 - random.random()) * strength * decay(t * freq)) for t in range(0, num_keypoints)]
    y_pts = [round(2 * (0.5 - random.random()) * strength * decay(t * freq)) for t in range(0, num_keypoints)]
    x_pts.append(0)
    y_pts.append(0)

    shake_pts = []
    for i in range(0, duration):
        if i % freq == 0:
            shake_pts.append((x_pts[i // freq], y_pts[i // freq]))
        else:
            prev_pt = (x_pts[i // freq], y_pts[i // freq])
            next_pt = (x_pts[i // freq + 1], y_pts[i // freq + 1])
            shake_pts.append(linear_interp(prev_pt, next_pt, (i % freq) / freq))

    if len(shake_pts) == 0:
        return  # this shouldn't happen but ehh

    shake_pts.reverse()  # this is used as a stack
    return shake_pts


def neighbors(x, y, and_diags=False, dist=1):
    if dist <= 0:
        return
    yield (x + dist, y)
    yield (x, y + dist)
    yield (x - dist, y)
    yield (x, y - dist)
    if and_diags:
        for n in diag_neighbors(x, y, dist=dist):
            yield n


def diag_neighbors(x, y, dist=1):
    yield (x + dist, y + dist)
    yield (x - dist, y + dist)
    yield (x + dist, y - dist)
    yield (x - dist, y - dist)


def time_string_to_ticks(time_string: str, fps=60, or_else=-1):
    try:
        res = 0
        parts = time_string.split(":")
        for idx, val in enumerate(reversed(parts)):
            if len(val) == 0:
                continue

            if idx == 0:  # seconds
                res += int(fps * float(val))
            elif idx == 1:  # minutes
                res += 60 * fps * int(val)
            elif idx == 2:  # hours
                res += 3600 * fps * int(val)
            else:
                raise ValueError("Time string has too many sections (max 3, for H:M:S): {}".format(time_string))
        return res
    except Exception:
        print("ERROR: failed to parse time string: {}".format(time_string))
        traceback.print_exc()
        return or_else


def ticks_to_time_string(n_ticks, fps=60, show_hours_if_zero=False, show_minutes_if_zero=True, n_decimals=0):
    neg = n_ticks < 0
    n_ticks = abs(n_ticks)

    seconds = max(0, n_ticks // fps)
    hours = seconds // 3600
    seconds = seconds % 3600
    minutes = seconds // 60
    seconds = seconds % 60
    sub_seconds = n_ticks % fps

    res = ""

    # handle hours
    if hours > 0 or show_hours_if_zero:
        res += str(hours)

    # handle minutes
    if len(res) > 0 or minutes > 0 or show_minutes_if_zero:
        if len(res) > 0:
            if minutes < 10:
                res += ":0" + str(minutes)
            else:
                res += ":" + str(minutes)
        else:
            res += str(minutes)

    # handle seconds
    if len(res) > 0:
        if seconds < 10:
            res += ":0" + str(seconds)
        else:
            res += ":" + str(seconds)
    else:
        res += str(seconds)

    # handle decimals
    if n_decimals > 0:
        res = res + "{:.{}f}".format(sub_seconds / fps, n_decimals)[1:]

    # handle negativity
    if neg:
        res = "-" + res

    return res


def read_safely(json_blob, key, default, mapper=lambda x: x):
    if key not in json_blob or json_blob[key] is None:
        return default
    else:
        try:
            return mapper(json_blob[key])
        except Exception:
            return default


def read_list_safely(json_blob, key, default, item_mapper=lambda x: x, accept_non_lists=True):
    def _mapper(value):
        if isinstance(value, list):
            return [item_mapper(v) for v in value]
        elif accept_non_lists:
            return item_mapper(value)
        else:
            return default
    return read_safely(json_blob, key, default, mapper=_mapper)


def python_version_string():
    major = sys.version_info[0]
    minor = sys.version_info[1]
    patch = sys.version_info[2]
    return "{}.{}.{}".format(major, minor, patch)


_FAKE_CLIPBOARD = ""


def set_clipboard(text):
    # TODO find a good platform-independent way to use the system clipboard
    global _FAKE_CLIPBOARD
    _FAKE_CLIPBOARD = text if text is not None else ""


def get_clipboard() -> str:
    # TODO find a good platform-independent way to use the system clipboard
    return _FAKE_CLIPBOARD


class Grid:

    def __init__(self, width, height, missing_val=None):
        self._size = (width, height)
        self._missing_val = missing_val

        self.grid = []  # stored as [x_idx][y_idx]
        for _ in range(0, width):
            self.grid.append([missing_val] * height)

    def resize(self, width, height):
        new_grid = []
        for _ in range(0, width):
            new_grid.append([self._missing_val] * height)

        for x in range(0, self._size[0]):
            for y in range(0, self._size[1]):
                if x < width and y < height:
                    # TODO break
                    new_grid[x][y] = self.grid[x][y]

        self._size = (width, height)
        self.grid = new_grid
        return self

    def size(self):
        return self._size

    def width(self):
        return self.size()[0]

    def height(self):
        return self.size()[1]

    def is_valid(self, xy):
        return 0 <= xy[0] < self.width() and 0 <= xy[1] < self.height()

    def is_empty(self, xy):
        if not self.is_valid(xy):
            return True
        else:
            return self.get(xy) == self._missing_val

    def get(self, xy):
        if self.is_valid(xy):
            return self.grid[xy[0]][xy[1]]
        else:
            raise ValueError("index out of range for grid size {}: {}".format(self.size(), xy))

    def set(self, xy, val, expand_if_needed=False):
        if self.is_valid(xy):
            self.grid[xy[0]][xy[1]] = val
        elif expand_if_needed and xy[0] >= 0 and xy[1] >= 0:
            new_w = max(self.width(), xy[0] + 1)
            new_h = max(self.height(), xy[1] + 1)
            self.resize(new_w, new_h)
            self.set(xy, val, expand_if_needed=False)  # shouldn't need to expand again
        else:
            raise ValueError("index out of range for grid size {}: {}".format(self.size(), xy))

    def indices(self, ignore_missing=False):
        for y in range(0, self.height()):
            for x in range(0, self.width()):
                xy = (x, y)
                if not ignore_missing or self.get(xy) != self._missing_val:
                    yield xy

    def values(self, ignore_missing=True):
        for xy in self.indices():
            val = self.get(xy)
            if not ignore_missing or val != self._missing_val:
                yield val

    def to_string(self, to_str=str, delim=", ", spacer=" ", newline_char="\n"):
        all_values = []
        max_len = 0
        for v in self.values(ignore_missing=False):
            as_str = to_str(v) + delim
            max_len = max(max_len, len(as_str))
            all_values.append(as_str)

        formatted = []
        for i in range(0, len(all_values)):
            val = all_values[i]
            if i % self.width() < self.width() - 1:
                if len(val) < max_len:
                    val = val + (spacer * (max_len - len(val)))
            elif (i // self.width()) % self.height() < self.height() - 1:
                val = val + newline_char
            formatted.append(val)

        return "".join(formatted)

    def __repr__(self):
        return self.to_string()


def string_checksum(the_string, m=982451653):
    res = 0
    for c in the_string:
        res += ord(c)
        res = (res * 31) % m
    return res


def to_key(obj):
    return _HashableWrapper(obj)


def apply_ascii_edits_to_text(text, ascii_edits, cursor_pos=-1, max_len=None, allowlist=None,
                              blocklist=('\t', '\r', "^[")):
    if cursor_pos < 0 or len(text) == 0:
        pre_text = text
        post_text = ""
        cursor_pos = len(text)
    else:
        cursor_pos = bound(cursor_pos, 0, len(text))
        pre_text = text[:cursor_pos]
        post_text = text[cursor_pos:]

    for add_char in ascii_edits:
        if add_char == '\b' and '\b' not in blocklist:  # backspace
            if len(pre_text) > 0:
                pre_text = pre_text[:len(pre_text) - 1]
                cursor_pos -= 1
        elif add_char == "~delete~":
            if len(post_text) > 0:
                post_text = post_text[1:]
        elif allowlist is not None and add_char not in allowlist:
            continue
        elif add_char in blocklist:
            continue
        elif max_len is None or len(pre_text) + len(add_char) + len(post_text) <= max_len:
            pre_text += add_char
            cursor_pos += len(add_char)

    return (pre_text + post_text, cursor_pos)


class SpacialHashMap:

    def __init__(self, cellsize):
        self._cellsize = cellsize

        self._cell_to_keys = {}   # cell_xy -> set of keys
        self._key_to_cells = {}   # key -> set of cell_xy
        self._key_to_values = {}  # key -> (rect, value)

    def _get_cell_at(self, xy):
        grid_x = xy[0] // self._cellsize
        grid_y = xy[1] // self._cellsize
        return (grid_x, grid_y)

    def _all_cells_in_rect(self, rect, include_empty=True):
        xy1 = (rect[0], rect[1])
        xy2 = (rect[0] + rect[2], rect[1] + rect[3])
        cell_min = self._get_cell_at(xy1)
        cell_max = self._get_cell_at(xy2)

        for grid_y in range(cell_min[1], cell_max[1] + 1):
            for grid_x in range(cell_min[0], cell_max[0] + 1):
                grid_xy = (grid_x, grid_y)
                if include_empty or grid_xy in self._cell_to_keys:
                    yield grid_xy

    def _get_cell_rect(self, grid_xy):
        return [self._cellsize * grid_xy[0], self._cellsize * grid_xy[1], self._cellsize, self._cellsize]

    def put(self, key, rect, value=None):
        if key in self._key_to_values:
            old_rect, old_value = self._key_to_values[key]
            if old_rect != rect:
                self.remove(key)
            else:
                # just updating the value, no need to rehash
                self._key_to_values[key] = (old_rect, value)
                return

        self._key_to_values[key] = (rect, value)
        for grid_xy in self._all_cells_in_rect(rect):
            self._add_key_to_cell(key, grid_xy)
            self._add_cell_to_key(key, grid_xy)

    def __contains__(self, key):
        return key in self._key_to_values

    def remove(self, key):
        if key in self._key_to_values:
            del self._key_to_values[key]
        if key in self._key_to_cells:
            for xy in self._key_to_cells[key]:
                self._rm_key_from_cell(key, xy)
            del self._key_to_cells[key]

    def clear(self):
        self._cell_to_keys.clear()
        self._key_to_cells.clear()
        self._key_to_values.clear()

    def get(self, key):
        """returns: (rect, value) for the given key, or None if the key is not mapped."""
        if key in self._key_to_values:
            return (self._key_to_values[key][0], self._key_to_values[key][1])
        else:
            return None

    def __len__(self):
        """returns: the number of items in the map."""
        return len(self._key_to_values)

    def _all_items_in_cell(self, cell_xy):
        """yields: (key, rect, value) for each item in the specified cell."""
        if cell_xy in self._cell_to_keys:
            for key in self._cell_to_keys[cell_xy]:
                yield (key, self._key_to_values[key][0], self._key_to_values[key][1])

    def all_items_at_point(self, pt):
        """yields: (key, rect, value) for each item containing the specified point."""
        grid_xy = self._get_cell_at(pt)
        for item in self._all_items_in_cell(grid_xy):
            key, rect, val = item
            if rect_contains(rect, pt):
                yield item

    def all_items_in_rect(self, target_rect):
        """yields: (key, rect, value) for each item intersecting the specified rect."""
        seen = set()  # holds the keys of items we've already processed
        for grid_xy in self._all_cells_in_rect(target_rect, include_empty=False):
            for item in self._all_items_in_cell(grid_xy):
                key, rect, val = item
                if key in seen:
                    continue
                else:
                    seen.add(key)
                    if rects_intersect(target_rect, rect):
                        yield item

    def _rm_key_from_cell(self, key, xy):
        if xy in self._cell_to_keys:
            keys = self._cell_to_keys[xy]
            if key in keys:
                keys.remove(key)
                if len(keys) == 0:
                    del self._cell_to_keys[xy]

    def _rm_cell_from_key(self, key, xy):
        if key in self._key_to_cells:
            cells = self._key_to_cells[key]
            cells.remove(xy)
            if len(cells) == 0:
                del self._key_to_cells[key]

    def _add_key_to_cell(self, key, xy):
        if xy not in self._cell_to_keys:
            self._cell_to_keys[xy] = set()
        self._cell_to_keys[xy].add(key)

    def _add_cell_to_key(self, key, xy):
        if key not in self._key_to_cells:
            self._key_to_cells[key] = set()
        self._key_to_cells[key].add(xy)

    def __repr__(self):
        return "{}:[num_items={}, num_cells={}]".format(type(self).__name__, len(self), len(self._cell_to_keys))

    def pretty_print(self):
        all_cells = []
        for c_xy in self._cell_to_keys:
            all_cells.append(c_xy)
        all_cells.sort()

        for c_xy in all_cells:
            print("[Cell {}: {}]:".format(c_xy, self._get_cell_rect(c_xy)))
            for key in self._cell_to_keys[c_xy]:
                rect, val = self.get(key)
                print("\t({}, {}, {})".format(key, rect, val))
            print()


class _HashableWrapper:
    """You can make mutable objects hashable with this handy wrapper. Is this a good idea? No."""

    def __init__(self, obj):
        if isinstance(obj, _HashableWrapper):
            self.obj = obj.obj
        else:
            self.obj = obj

    def __hash__(self):
        return checksum(self.obj, strict=False)

    def __eq__(self, other):
        return other.obj == self.obj


def checksum(blob, m=982451653, strict=True):
    """
        Calculates a checksum of any composition of dicts, lists, tuples, bools, strings, and ints.
        Lists and tuples are considered identical. The only restriction is that keys of maps must
        be comparable, and there can't be loops (like a map containing itself).

        param strict: if False, illegal types will be converted to strings and included in the checksum.
                      if True, illegal types will cause a ValueError to be thrown.
    """
    if blob is None:
        return 11 % m
    elif isinstance(blob, bool):
        return (31 if blob else 1279) % m
    elif isinstance(blob, int):
        return blob % m
    elif isinstance(blob, str):
        return string_checksum(blob, m=m)
    elif isinstance(blob, (list, tuple)):
        res = 0
        for c in blob:
            res += checksum(c, m=m, strict=strict)
            res = (res * 37) % m
        return res
    elif isinstance(blob, dict):
        keys = [k for k in blob]
        keys.sort()

        res = 0
        for key in keys:
            k_checksum = checksum(key, m=m, strict=strict)
            val_checksum = checksum(blob[key], m=m, strict=strict)
            res += k_checksum
            res = (res * 41) % m
            res += val_checksum
            res = (res * 53) % m

        return res
    else:
        if strict:
            raise ValueError("blob has illegal type: {}".format(blob))
        else:
            return string_checksum(str(blob), m=m)


if __name__ == "__main__":
    hashmap = SpacialHashMap(10)
    hashmap.put("rect1", [0, 0, 15, 15], value="A")
    hashmap.put("rect2", [10, 10, 20, 20], value="B")
    hashmap.pretty_print()
    print([x for x in hashmap.all_items_at_point((0, 5))])


if __name__ == "__main__" and False:
    sizes = [(5, 5), (2, 3), (7, 2), (1, 5), (9, 4), (3, 16), (3, 3), (3, 4)]
    packed, bound = pack_rects_into_smallest_rect(sizes)
    print("sizes={}".format(sizes))
    print("packed into {}: ={}".format(bound, packed))

    for y in range(0, bound[1]):
        line = []
        for x in range(0, bound[0]):
            c = " -"
            for i in range(0, len(packed)):
                if rect_contains(packed[i], (x, y)):
                    if c == " -":
                        c = str(i) if i > 9 else "0" + str(i)
                    else:
                        c = "XX"
            line.append(c)
        print(" ".join(line))


