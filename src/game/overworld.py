
import math
import traceback
import os
import random
import re
from collections import deque
import typing

import src.engine.scenes as scenes
import src.game.blueprints as blueprints
import src.game.worldview as worldview
import src.engine.inputs as inputs
import src.engine.keybinds as keybinds
import src.engine.sprites as sprites
import src.game.globalstate as gs
import src.engine.renderengine as renderengine
import src.engine.spritesheets as spritesheets
import src.game.const as const
import configs as configs
import src.game.debug as debug
import src.utils.util as util
import src.game.ui as ui
import src.game.spriteref as spriteref
import src.game.colors as colors
import src.game.playertypes as playertypes


class OverworldGrid:

    class OverworldNode:

        def __init__(self, xy):
            self._enabled = True
            self._xy = xy

        def get_xy(self):
            return self._xy

        def is_enabled(self):
            return self._enabled

        def set_enabled(self, val):
            self._enabled = val

        def is_selectable(self):
            return True

        def is_level(self):
            return False

        def is_connector(self):
            return False

        def is_endpoint(self):
            return False

        def is_exit(self):
            return False

        def is_start(self):
            return False

    class LevelNode(OverworldNode):

        def __init__(self, xy, overworld_id: str):
            """
            xy: grid position
            overworld_id: ID of level in overworld (e.g. "3", "i1", "c1")
            """
            OverworldGrid.OverworldNode.__init__(self, xy)
            self.n = overworld_id

        def __repr__(self):
            return self.n

        @staticmethod
        def is_valid_level_text(text):
            if len(text) == 0:
                return False
            elif text.isnumeric():
                return True
            elif text[0] in ("i", "a", "b", "c", "d", "u") and text[1:].isnumeric():
                return True
            else:
                return False

        def get_level_num(self):
            return self.n

        def get_level_info(self, state: 'OverworldState'):
            """returns: (level_num, level_id, level_bp)"""
            level_id = state.get_level_id_for_num(self.n)
            level_bp = state.get_level_blueprint(level_id)
            return (self.n, level_id, level_bp)

        def get_pretty_level_num(self):
            if self.n.isnumeric():
                return self.n
            elif self.n[0] == "i":
                return "!"
            else:
                return "?"

        def is_level(self):
            return True

    class ConnectionNode(OverworldNode):
        VERT = "|"
        HORZ = "~"
        FREE = "*"

        @staticmethod
        def is_valid_con_type(text):
            if text == OverworldGrid.ConnectionNode.FREE:
                return True
            elif text == OverworldGrid.ConnectionNode.VERT:
                return True
            elif text == OverworldGrid.ConnectionNode.HORZ:
                return True
            else:
                return False

        def __init__(self, xy, con_type):
            OverworldGrid.OverworldNode.__init__(self, xy)
            self.con_type = con_type

        def __repr__(self):
            return self.con_type

        def is_selectable(self):
            return False

        def allows_connection(self, n=False, e=False, w=False, s=False, direction=None):
            if direction is not None:
                n = n or direction[1] < 0
                e = e or direction[0] > 0
                w = w or direction[0] < 0
                s = s or direction[1] > 0
            if self.con_type == OverworldGrid.ConnectionNode.FREE:
                return True
            elif self.con_type == OverworldGrid.ConnectionNode.VERT:
                return not e and not w
            elif self.con_type == OverworldGrid.ConnectionNode.HORZ:
                return not n and not s
            else:
                raise ValueError("unhandled connection type: {}".format(self.con_type))

        def is_connector(self):
            return True

    class ExitNode(OverworldNode):

        @staticmethod
        def get_exit_id_from_text(text) -> int:
            if bool(re.match("e[0-9]+", text)):
                return int(text[1:])
            else:
                return None

        @staticmethod
        def is_valid_exit_text(text) -> bool:
            return OverworldGrid.ExitNode.get_exit_id_from_text(text) is not None

        def __init__(self, xy, exit_text):
            OverworldGrid.OverworldNode.__init__(self, xy)
            self._exit_id = OverworldGrid.ExitNode.get_exit_id_from_text(exit_text)

        def is_endpoint(self):
            return True

        def is_exit(self):
            return True

        def get_exit_id(self):
            return self._exit_id

        def __repr__(self):
            return "e{}".format(self._exit_id)

    class GameStartNode(OverworldNode):

        @staticmethod
        def is_valid_game_start_node(text) -> bool:
            return text == "s"

        def is_endpoint(self):
            return True

        def is_start(self):
            return True

        def is_selectable(self):
            return False

        def __repr__(self):
            return "s"

    class GameEndNode(OverworldNode):

        @staticmethod
        def is_valid_game_end_text(text) -> bool:
            return text == "f"

        def is_endpoint(self):
            return True

        def is_end(self):
            return True

        def is_selectable(self):
            return False

        def __repr__(self):
            return "f"

    def __init__(self, w, h):
        self.grid = util.Grid(w, h)

    def size(self):
        return self.grid.size()

    def is_valid(self, xy):
        w, h = self.size()
        return 0 <= xy[0] < w and 0 <= xy[1] < h

    def get_node(self, xy) -> 'OverworldGrid.OverworldNode':
        if self.grid.is_valid(xy):
            return self.grid.get(xy)
        else:
            return None

    def is_empty_at(self, xy):
        return self.get_node(xy) is None

    def set_node(self, xy, val):
        self.grid.set(xy, val, expand_if_needed=True)

    def is_connected(self, xy1, xy2):
        if self.is_empty_at(xy1) or self.is_empty_at(xy2):
            return False
        elif util.dist_manhattan(xy1, xy2) != 1:
            return False
        else:
            n1 = self.get_node(xy1)
            n2 = self.get_node(xy2)
            dir_between = util.cardinal_direction_between(xy1, xy2)
            if isinstance(n1, OverworldGrid.ConnectionNode) and not n1.allows_connection(direction=dir_between):
                return False
            elif isinstance(n2, OverworldGrid.ConnectionNode) and not n2.allows_connection(direction=util.negate(dir_between)):
                return False
            else:
                return True

    def get_connected_directions(self, xy):
        """returns (north: bool, east: bool, south: bool, west: bool)"""
        if self.is_empty_at(xy):
            return (False, False, False, False)
        else:
            n_xy = (xy[0], xy[1] - 1)
            e_xy = (xy[0] + 1, xy[1])
            s_xy = (xy[0], xy[1] + 1)
            w_xy = (xy[0] - 1, xy[1])
            neighbors = [n_xy, e_xy, s_xy, w_xy]
            return tuple(self.is_connected(xy, n) for n in neighbors)

    def all_connected_neighbors(self, xy):
        for n in util.neighbors(xy[0], xy[1]):
            if self.is_connected(xy, n):
                yield n

    def all_nodes(self, cond=lambda n: True):
        for node in self.grid.values(ignore_missing=True):
            if cond(node):
                yield node

    def search_for_node(self, cond) -> 'OverworldGrid.OverworldNode':
        for n in self.all_nodes(cond):
            return n
        return None

    def get_game_start_node_if_present(self):
        return self.search_for_node(lambda n: n.is_start())

    def get_game_end_node_if_present(self):
        return self.search_for_node(lambda n: n.is_end())

    def get_all_exit_nodes(self):
        return [e for e in self.all_nodes(cond=lambda n: n.is_exit())]

    def get_exit_node(self, exit_id):
        return self.search_for_node(lambda n: n.is_exit() and n.get_exit_id() == exit_id)

    def get_all_level_nodes(self) -> typing.List[LevelNode]:
        res = [l for l in self.all_nodes(cond=lambda n: n.is_level())]
        res.sort(key=lambda l: l.get_level_num())
        return res

    def get_closest_selectable_connected_node(self, xy, cond=lambda n: True):
        for n in self.bf_traverse(xy, enabled_only=False):
            if n.is_selectable() and cond(n):
                return n
        return None

    def get_connected_node_in_dir(self, xy, direction, selectable_only=True, enabled_only=True) -> 'OverworldGrid.OverworldNode':
        start_node = self.get_node(xy)
        if start_node is None:
            return None
        else:
            n, e, s, w = self.get_connected_directions(xy)
            to_search = []
            if direction[1] < 0 and n:
                to_search.append(((xy[0], xy[1] - 1)))
            elif direction[1] > 0 and s:
                to_search.append(((xy[0], xy[1] + 1)))
            if direction[0] < 0 and w:
                to_search.append(((xy[0] - 1, xy[1])))
            elif direction[0] > 0 and e:
                to_search.append(((xy[0] + 1, xy[1])))

            for start_xy in to_search:
                for candidate in self.bf_traverse(start_xy, ignore=(xy,),
                                                  enabled_only=enabled_only, selectable_only=False):
                    if not selectable_only or candidate.is_selectable():
                        return candidate
            return None

    def bf_traverse(self, start_xy, ignore=(), enabled_only=False, selectable_only=False):

        def _allow(xy):
            if not self.grid.is_valid(xy):
                return False
            else:
                n = self.get_node(xy)
                if n is None:
                    return False
                elif enabled_only and not n.is_enabled():
                    return False
                elif selectable_only and not n.is_selectable():
                    return False
                else:
                    return True

        if not _allow(start_xy):
            pass
        else:
            q = deque()
            q.append(start_xy)

            seen = set()
            seen.update(ignore)
            seen.add(start_xy)

            while len(q) > 0:
                cur_xy = q.pop()
                yield self.get_node(cur_xy)

                for n in util.neighbors(cur_xy[0], cur_xy[1]):
                    if _allow(n) and n not in seen:
                        seen.add(n)
                        q.append(n)

    def __repr__(self):
        return self.grid.to_string()


class OverworldPack:

    @staticmethod
    def load_from_dir(path):
        try:
            print("INFO: loading overworld pack from {}".format(path))

            json_blob = util.load_json_from_path(os.path.join(path, "_game_spec.json"))
            name = util.read_string(json_blob, "name", "Unnamed World")
            ident = str(json_blob["ref_id"])
            author = util.read_string(json_blob, "author", "Unknown")
            overworlds = {}

            overworld_ids = [str(ov_id) for ov_id in json_blob["overworlds"]]
            for overworld_id in overworld_ids:
                ov_path = os.path.join(path, overworld_id)
                loaded_overworld = OverworldBlueprint.load_from_dir(ov_path)
                if loaded_overworld is not None:
                    overworlds[overworld_id] = loaded_overworld

            connections = {}
            if "connections" in json_blob:
                for ov_id in overworld_ids:
                    if ov_id in json_blob["connections"]:
                        for exit_id in json_blob["connections"][ov_id]:
                            if exit_id[0] == "e":
                                exit_num = int(exit_id[1:])
                                connected_overworld_id = json_blob["connections"][ov_id][exit_id][0]
                                connected_exit_id = json_blob["connections"][ov_id][exit_id][1]

                                if connected_exit_id[0] == "e":
                                    connected_exit_num = int(connected_exit_id[1:])
                                    if ov_id in overworlds and connected_overworld_id in overworlds:
                                        if ov_id not in connections:
                                            connections[ov_id] = {}
                                        connections[ov_id][exit_num] = connected_overworld_id

                                        if connected_overworld_id not in connections:
                                            connections[connected_overworld_id] = {}
                                        connections[connected_overworld_id][connected_exit_num] = ov_id
                                    else:
                                        if ov_id not in overworlds:
                                            print("WARN: cannot connect overworld because id is unrecognized: {}".format(ov_id))
                                        if connected_overworld_id not in overworlds:
                                            print("WARN: cannot connect overworld because id is unrecognized: {}".format(connected_overworld_id))
                                else:
                                    print("WARN: unrecognized exit id: {}".format(connected_exit_id))
                            else:
                                print("WARN: unrecognized exit id: {}".format(exit_id))

            return OverworldPack(ident, name, author, overworlds, connections, path)

        except Exception:
            print("ERROR: failed to load overworld \"{}\"".format(path))
            traceback.print_exc()
            return None

    def __init__(self, ref_id, name, author, overworlds, connections, directory):
        """
        :param ref_id: id of the pack
        :param name: name of the pack
        :param author: author of the pack
        :param overworlds: map from overworld_id -> OverworldBlueprint
        :param connections: map from overworld_id -> (map from exit_num -> overworld_id)
        """
        self.ref_id = ref_id
        self.name = name
        self.author = author
        self.overworlds = overworlds
        self.connections = connections

        self.directory = directory

        self._starting_world = self._find_starting_overworld()

    def get_start(self) -> 'OverworldBlueprint':
        return self._starting_world

    def get_overworld_with_id(self, ref_id) -> 'OverworldBlueprint':
        if ref_id in self.overworlds:
            return self.overworlds[ref_id]
        else:
            return None

    def all_overworlds(self):
        for ov_id in self.overworlds:
            yield self.overworlds[ov_id]

    def get_neighbor(self, overworld: 'OverworldBlueprint', exit_num: int) -> 'OverworldBlueprint':
        if overworld.ref_id in self.connections:
            exit_mapping = self.connections[overworld.ref_id]
            if exit_num in exit_mapping:
                dest_id = exit_mapping[exit_num]
                return self.get_overworld_with_id(dest_id)
        return None

    def get_exit_leading_to(self, start_overworld, dest_overworld) -> int:
        if start_overworld.ref_id in self.connections:
            exit_mapping = self.connections[start_overworld.ref_id]
            for exit_num in exit_mapping:
                if exit_mapping[exit_num] == dest_overworld.ref_id:
                    return exit_num
        return None

    def _find_starting_overworld(self) -> 'OverworldBlueprint':
        for ow_id in self.overworlds:
            if self.overworlds[ow_id].has_start_node():
                return self.overworlds[ow_id]
        print("WARN: overworld pack {} has no starting node.".format(self.name))
        return None


class OverworldBlueprint:

    @staticmethod
    def load_from_dir(path):
        try:
            json_blob = util.load_json_from_path(os.path.join(path, "_spec.json"))

            name = util.read_string(json_blob, "name", "Unnamed World")
            ident = str(json_blob["ref_id"])
            author = util.read_string(json_blob, "author", "Unknown")

            data_stride = int(json_blob["data_stride"])
            raw_grid = json_blob["data"]

            parsed_grid = []
            y = 0
            for line in raw_grid:
                parsed = []
                for i in range(0, int(math.ceil(len(line) / data_stride))):
                    start = i * data_stride
                    end = min(len(line), (i + 1) * data_stride)
                    node_text = line[start:end]
                    node_text = node_text.strip()  # rm whitespace

                    xy = (i, y)

                    if OverworldGrid.LevelNode.is_valid_level_text(node_text):
                        parsed.append(OverworldGrid.LevelNode(xy, node_text))
                    elif OverworldGrid.ConnectionNode.is_valid_con_type(node_text):
                        parsed.append(OverworldGrid.ConnectionNode(xy, node_text))
                    elif OverworldGrid.ExitNode.is_valid_exit_text(node_text):
                        parsed.append(OverworldGrid.ExitNode(xy, node_text))
                    elif OverworldGrid.GameStartNode.is_valid_game_start_node(node_text):
                        parsed.append(OverworldGrid.GameStartNode(xy))
                    elif OverworldGrid.GameEndNode.is_valid_game_end_text(node_text):
                        parsed.append(OverworldGrid.GameEndNode(xy))
                    else:
                        if bool(re.match(".*[a-zA-Z0-9]+.*", node_text)):
                            print("WARN: unrecognized token in overworld spec: {}".format(node_text))
                        parsed.append(None)
                parsed_grid.append(parsed)
                y += 1

            grid_w = len(parsed_grid[0])
            grid_h = len(parsed_grid)

            grid = OverworldGrid(grid_w, grid_h)
            levels = {}  # int -> level_id

            for x in range(0, grid_w):
                for y in range(0, grid_h):
                    node = parsed_grid[y][x]
                    if node is not None:
                        grid.set_node((x, y), node)
                    if node is not None and isinstance(node, OverworldGrid.LevelNode):
                        levels[node.n] = util.read_string(json_blob, "lvl_{}".format(node.n), default=None)

            color_mapping = {  # TODO this should not be here
                "light_gray": colors.LIGHT_GRAY,
                "dark_gray": colors.DARK_GRAY,
                "green": colors.GREEN,
                "dark_green": colors.DARK_GREEN,
                "tan": colors.TAN,
                "dark_tan": colors.DARK_TAN,
                "purple": colors.PURPLE,
                "dark_purple": colors.DARK_PURPLE,
                "blue": colors.BLUE,
                "dark_blue": colors.DARK_BLUE,
                "black": colors.PERFECT_BLACK,
                "white": colors.WHITE
            }

            bg_triangles = [[] for _ in range(0, 9)]
            if "bg_triangles" in json_blob:
                def get_triangles(tri_list):
                    res = []
                    for tup in tri_list:
                        p1 = (int(tup[0][0]), int(tup[0][1]))
                        p2 = (int(tup[1][0]), int(tup[1][1]))
                        p3 = (int(tup[2][0]), int(tup[2][1]))
                        color = tup[3]
                        if isinstance(color, str):
                            if color in color_mapping:
                                color = color_mapping[color]
                            else:
                                print("WARN: Unrecognized color: {}".format(color))
                                color = colors.WHITE
                        else:
                            color = colors.to_float(int(color[0]), int(color[1]), int(color[2]))
                        res.append((p1, p2, p3, color))
                    return res

                tri_keys = ["top_left", "top", "top_right", "left", "center", "right", "bottom_left", "bottom", "bottom_right"]
                try:
                    for i in range(0, 9):
                        if tri_keys[i] in json_blob["bg_triangles"]:
                            bg_triangles[i].extend(get_triangles(json_blob["bg_triangles"][tri_keys[i]]))

                except Exception as e:
                    print("ERROR: failed to load bg_triangles")
                    traceback.print_exc()

            return OverworldBlueprint(ident, name, author, grid, levels, bg_triangles, path)

        except Exception:
            print("ERROR: failed to load overworld \"{}\"".format(path))
            traceback.print_exc()
            return None

    def __init__(self, ref_id, name, author, grid, level_lookup, bg_triangles, directory):
        """
        :param grid: an OverworldGrid
        :param level_lookup: map of level_num -> level_id
        :param bg_triangles: list of (p1, p2, p3, color)
        """
        self.name = name
        self.ref_id = ref_id
        self.author = author
        self.grid = grid
        self.levels = level_lookup
        self.bg_triangles = bg_triangles

        self.directory = directory

    def get_grid(self) -> OverworldGrid:
        return self.grid

    def has_start_node(self):
        return self.grid.get_game_start_node_if_present() is not None

    def __repr__(self):
        return "\n".join([
            "OverworldBlueprint: {}".format(self.ref_id),
            "  name={}".format(self.name),
            "  author={}".format(self.author),
            "  grid=\n{}".format(self.grid),
            "  levels={}".format(self.levels)
        ])


class OverworldState:

    def __init__(self, overworld_pack: OverworldPack, came_from=None):
        self.overworld_pack = overworld_pack
        self.current_overworld = self.overworld_pack.get_start()
        self.requested_overworld = None  # (OverworldBlueprint, entry_num)

        """level_blueprints level_id -> level_blueprint"""
        self.level_blueprints = {}
        self.reload_level_blueprints_from_disk()

        self.selected_cell = self.find_initial_selection(came_from_exit_id=came_from)

        self._unlocked_nodes = set()
        self.refresh_unlocked_levels()

        self.cell_under_mouse = None

    def get_grid(self) -> OverworldGrid:
        return self.current_overworld.get_grid()

    def get_overworld(self) -> OverworldBlueprint:
        return self.current_overworld

    def refresh_unlocked_levels(self):
        self._unlocked_nodes = self._calc_unlocked_nodes(self.selected_cell)
        for n in self.get_grid().get_all_level_nodes():
            n.set_enabled(n.get_xy() in self._unlocked_nodes)
        for n in self.get_grid().get_all_exit_nodes():
            n.set_enabled(n.get_xy() in self._unlocked_nodes)

    def next_requested_overworld(self):
        """returns: (OverworldBlueprint, entry_num)"""
        return self.requested_overworld

    def activate_exit_node(self, exit_num, instantly=False):
        new_overworld = self.overworld_pack.get_neighbor(self.current_overworld, exit_num)
        if new_overworld is not None:
            entry_num = self.overworld_pack.get_exit_leading_to(new_overworld, self.current_overworld)
            if instantly:
                self.set_current_overworld(new_overworld, entry_num=entry_num)
            else:
                self.requested_overworld = (new_overworld, entry_num)

    def set_current_overworld(self, overworld, entry_num=None):
        new_overworld = self.overworld_pack.get_overworld_with_id(overworld.ref_id)
        if new_overworld is not None:
            self.current_overworld = new_overworld
            self.selected_cell = self.find_initial_selection(came_from_exit_id=entry_num)
            self.cell_under_mouse = None
            self.requested_overworld = None
            self.refresh_unlocked_levels()
        else:
            print("WARN: unrecognized overworld_id: {}".format(overworld.ref_id))

    def reload_level_blueprints_from_disk(self):
        self.level_blueprints.clear()
        for overworld_bp in self.overworld_pack.all_overworlds():
            level_dir = os.path.join(overworld_bp.directory, "levels")
            loaded_levels = blueprints.load_all_levels_from_dir(level_dir)
            self.level_blueprints.update(loaded_levels)

    def get_level_blueprint(self, level_id) -> blueprints.LevelBlueprint:
        if level_id in self.level_blueprints:
            return self.level_blueprints[level_id]
        else:
            return None

    def get_level_id_for_num(self, n) -> str:
        if n in self.current_overworld.levels:
            return self.current_overworld.levels[n]
        else:
            return None

    def get_level_id_at(self, xy):
        if self.get_grid().is_empty_at(xy):
            return None
        else:
            node = self.get_grid().get_node(xy)
            if isinstance(node, OverworldGrid.LevelNode):
                return self.get_level_id_for_num(node.n)
            else:
                return None

    def get_world_num(self):
        # TODO figure out a better way to display the active sector
        return 1

    def is_complete(self, level_id):
        return gs.get_instance().save_data().is_completed(level_id)

    def is_selected_at(self, xy):
        if self.selected_cell is None:
            return False
        else:
            return xy == self.selected_cell

    def get_selected_node(self) -> OverworldGrid.OverworldNode:
        if self.selected_cell is not None:
            return self.get_grid().get_node(self.selected_cell)
        else:
            return None

    def get_selected_level(self) -> tuple:
        """returns: (level_num, level_blueprint)"""
        selected_node = self.get_selected_node()
        if selected_node is not None and isinstance(selected_node, OverworldGrid.LevelNode):
            level_num = selected_node.get_level_num()
            level_id = self.get_level_id_for_num(level_num)
            level_bp = self.get_level_blueprint(level_id)
            return (level_num, level_bp)
        else:
            return (None, None)

    def get_selected_level_id(self):
        selected_node = self.get_selected_node()
        if selected_node is not None and isinstance(selected_node, OverworldGrid.LevelNode):
            return self.get_level_id_for_num(selected_node.get_level_num())
        else:
            return None

    def set_selected_node(self, node):
        if node is None:
            self.selected_cell = None
        else:
            self.selected_cell = node.get_xy()

    def is_unlocked_at(self, xy):
        return xy in self._unlocked_nodes

    def get_completion_time(self, level_id):
        completed_levels = gs.get_instance().save_data().completed_levels()
        if level_id in completed_levels:
            return completed_levels[level_id]
        else:
            return None

    def set_completed(self, level_id, time):
        cur_time = self.get_completion_time(level_id)
        if cur_time is None or cur_time > time:
            gs.get_instance().save_data().set_completed(level_id, time)
            self.refresh_unlocked_levels()

    def _calc_unlocked_nodes(self, starting_xy):
        unlocked = set()
        q = [starting_xy]

        seen = set()
        seen.add(starting_xy)

        while len(q) > 0:
            xy = q.pop(-1)
            unlocked.add(xy)
            level_id = self.get_level_id_at(xy)
            if level_id is None or xy == starting_xy or self.is_complete(level_id) or debug.is_all_unlocked():
                for d in util.neighbors(0, 0):
                    neighbor = self.get_grid().get_connected_node_in_dir(xy, d, selectable_only=False, enabled_only=False)
                    if neighbor is not None:
                        if neighbor.get_xy() not in seen:
                            seen.add(neighbor.get_xy())
                            q.append(neighbor.get_xy())
        return unlocked

    def get_nodes_with_id(self, level_id):
        res = []
        for level_node in self.get_grid().all_nodes(cond=lambda n: n.is_level()):
            node_num = level_node.get_level_num()
            node_id = self.get_level_id_for_num(node_num)
            if node_id == level_id:
                res.append(level_node)
        return res

    def find_initial_selection(self, came_from_exit_id=None):
        entry_node = None
        if came_from_exit_id is not None:
            entry_node = self.get_grid().get_exit_node(came_from_exit_id)
            if entry_node is None:
                print("WARN: couldn't find exit node with id: {}".format(came_from_exit_id))
        if entry_node is None:
            entry_node = self.get_grid().get_game_start_node_if_present()

        if entry_node is None:
            level_nodes = self.get_grid().get_all_level_nodes()
            if len(level_nodes) > 0:
                return level_nodes[0].get_xy()  # just select the first level
            else:
                print("WARN: grid has no levels...?")
                return None
        else:
            res = self.get_grid().get_closest_selectable_connected_node(entry_node.get_xy(),
                                                                        cond=lambda n: n.is_level())
            if res is not None:
                return res.get_xy()
        return None


class LevelNodeElement(ui.UiElement):

    UNLOCK_ANIM_DURATION = 180

    def __init__(self, xy, level_id, level_num, overworld_state):
        ui.UiElement.__init__(self)
        self.grid_xy = xy
        self.level_id = level_id
        self.level_num = level_num
        self.state: OverworldState = overworld_state

        self._cached_player_types = None

    def get_icon_color(self, selected, completed, unlocked):
        if completed:
            return colors.LIGHT_GRAY
        elif unlocked:
            return colors.WHITE
        else:
            return colors.DARK_GRAY

    def get_player_types(self):
        if self._cached_player_types is None:
            level_bp = self.state.get_level_blueprint(self.level_id)
            self._cached_player_types = level_bp.get_player_types() if level_bp is not None else []

        return self._cached_player_types

    def get_size(self):
        return (24, 24)

    def update(self):
        self.update_sprites()

    def update_sprites(self):
        pass  # subclasses should impl this

    @staticmethod
    def new_element(xy, level_id, level_num, state):
        if level_num.isnumeric():
            return NumberedLevelNodeElement(xy, level_id, level_num, state)
        else:
            return InfoLevelNodeElement(xy, level_id, level_num, state)


class NumberedLevelNodeElement(LevelNodeElement):

    def __init__(self, xy, level_id, level_num, overworld_state):
        super().__init__(xy, level_id, level_num, overworld_state)
        self.border_sprites = [None] * 9
        self.icon_sprite = None

        self.freshly_unlocked_counter = 0

    def _get_border_img_and_color_at(self, idx, selected, completed, unlocked, players_in_level):
        corners = {
            0: playertypes.PlayerTypes.FAST,
            2: playertypes.PlayerTypes.SMALL,
            6: playertypes.PlayerTypes.HEAVY,
            8: playertypes.PlayerTypes.FLYING
        }
        if unlocked:
            full_sprites = spriteref.overworld_sheet().level_icon_full_pieces
            empty_sprites = spriteref.overworld_sheet().level_icon_empty_pieces
        else:
            full_sprites = spriteref.overworld_sheet().level_icon_full_gray_pieces
            empty_sprites = spriteref.overworld_sheet().level_icon_empty_gray_pieces

        if selected:
            color = colors.PERFECT_RED
        elif completed:
            color = colors.LIGHT_GRAY
        elif unlocked:
            color = colors.PERFECT_WHITE  # XXX the sprites are drawn with off-white already
        else:
            color = colors.PERFECT_WHITE  # sprites are already colored

        if idx in corners:
            player_type = corners[idx]
            if player_type in players_in_level:
                return full_sprites[idx], colors.PERFECT_WHITE
            else:
                return empty_sprites[idx], color
        else:
            return empty_sprites[idx], color

    def update_sprites(self):
        selected = self.state.is_selected_at(self.grid_xy)
        unlocked = self.state.is_unlocked_at(self.grid_xy)

        completed = self.state.is_complete(self.level_id)
        players = self.get_player_types()

        xy = self.get_xy(absolute=True)
        i_x = 0
        i_y = 0
        for i in range(0, len(self.border_sprites)):
            if i % 3 == 0:
                i_x = 0
            if self.border_sprites[i] is None:
                self.border_sprites[i] = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER, scale=1, depth=5)
            model, color = self._get_border_img_and_color_at(i, selected, completed, unlocked, players)

            self.border_sprites[i] = self.border_sprites[i].update(new_model=model,
                                                                   new_x=xy[0] + i_x, new_y=xy[1] + i_y,
                                                                   new_color=color)
            i_x += self.border_sprites[i].width()
            if i % 3 == 2:
                i_y += self.border_sprites[i].height()

        icon_color = self.get_icon_color(selected, completed, unlocked)
        size = self.get_size()

        if selected:
            # once you select a level, cancel the unlocking animation.
            self.freshly_unlocked_counter = LevelNodeElement.UNLOCK_ANIM_DURATION * 2
        elif self.freshly_unlocked_counter < LevelNodeElement.UNLOCK_ANIM_DURATION * 2:
            self.freshly_unlocked_counter += 1

        if not unlocked or (not completed and not selected and self.freshly_unlocked_counter < LevelNodeElement.UNLOCK_ANIM_DURATION):
            if not unlocked:
                prog = 0
            else:
                prog = self.freshly_unlocked_counter / LevelNodeElement.UNLOCK_ANIM_DURATION
                if prog > 0.5:
                    # fade out as it unlocks
                    icon_color = colors.darken(icon_color, min(0.5, (prog - 0.5)) / 0.5)

            if self.icon_sprite is None or not isinstance(self.icon_sprite, sprites.ImageSprite):
                self.icon_sprite = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER)
            icon_xy = (xy[0] + size[0] // 2 - self.icon_sprite.size()[0] // 2,
                       xy[1] + size[1] // 2 - self.icon_sprite.size()[1] // 2)
            self.icon_sprite = self.icon_sprite.update().update(new_model=spriteref.overworld_sheet().get_lock_icon(prog),
                                                                new_x=icon_xy[0], new_y=icon_xy[1],
                                                                new_color=icon_color, new_depth=0, new_scale=1)
        else:
            if self.icon_sprite is None or not isinstance(self.icon_sprite, sprites.TextSprite):
                self.icon_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, str(self.level_num), x_kerning=0)

            icon_xy = (xy[0] + size[0] // 2 - self.icon_sprite.size()[0] // 2,
                    xy[1] + size[1] // 2 - self.icon_sprite.size()[1] // 2)
            if not completed:
                if LevelNodeElement.UNLOCK_ANIM_DURATION <= self.freshly_unlocked_counter < 1.25 * LevelNodeElement.UNLOCK_ANIM_DURATION:
                    # fade in after it unlocks
                    fade_in_prog = (self.freshly_unlocked_counter - LevelNodeElement.UNLOCK_ANIM_DURATION) / (0.25 * LevelNodeElement.UNLOCK_ANIM_DURATION)
                    icon_color = colors.darken(icon_color, util.bound(1 - fade_in_prog, 0, 1))
            self.icon_sprite = self.icon_sprite.update(new_x=icon_xy[0], new_y=icon_xy[1], new_text=str(self.level_num),
                                                       new_color=icon_color, new_depth=0, new_scale=1)

    def all_sprites(self):
        for spr in super().all_sprites():
            yield spr
        for spr in self.border_sprites:
            if spr is not None:
                yield spr
        for spr in self.icon_sprite.all_sprites():
            yield spr


class InfoLevelNodeElement(LevelNodeElement):

    def __init__(self, xy, level_id, level_num, overworld_state):
        super().__init__(xy, level_id, level_num, overworld_state)
        self.connection_sprites = [None] * 4
        self.icon_sprite = None
        self.icon_border_sprite = None

    def _get_icon_model_and_color(self, selected, completed, unlocked):
        letter = self.level_num[0]
        color = self.get_icon_color(selected, completed, unlocked)
        if letter in "uabcd":
            model = spriteref.overworld_sheet().level_small_icon_unit
            if unlocked:
                color = spriteref.get_color("uabcd".index(letter), dark=completed)
        else:
            model = spriteref.overworld_sheet().level_small_icon_exclam

        return model, color

    def update_sprites(self):
        selected = self.state.is_selected_at(self.grid_xy)
        completed = self.state.is_complete(self.level_id)
        unlocked = self.state.is_unlocked_at(self.grid_xy)

        xy = self.get_xy(absolute=True)
        size = self.get_size()

        model, icon_color = self._get_icon_model_and_color(selected, completed, unlocked)
        if self.icon_sprite is None:
            self.icon_sprite = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER)
        self.icon_sprite = self.icon_sprite.update(new_model=model,
                                                   new_x=xy[0] + size[0] // 2 - model.width() // 2,
                                                   new_y=xy[1] + size[1] // 2 - model.height() // 2,
                                                   new_color=icon_color)

        border_color = colors.PERFECT_RED if selected else self.get_icon_color(selected, completed, unlocked)
        border_model = spriteref.overworld_sheet().level_small_border
        if self.icon_border_sprite is None:
            self.icon_border_sprite = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER, depth=5)
        self.icon_border_sprite = self.icon_border_sprite.update(new_model=border_model,
                                                                 new_x=xy[0] + size[0] // 2 - border_model.width() // 2,
                                                                 new_y=xy[1] + size[1] // 2 - border_model.height() // 2,
                                                                 new_color=border_color)

        node_rect = [xy[0], xy[1], size[0], size[1]]
        con_models = spriteref.overworld_sheet().level_small_icon_connections

        n, e, s, w = self.state.get_grid().get_connected_directions(self.grid_xy)

        self._update_connection_sprite(n, 0, con_models[0], node_rect, (0, -1))
        self._update_connection_sprite(e, 1, con_models[1], node_rect, (1, 0))
        self._update_connection_sprite(s, 2, con_models[2], node_rect, (0, 1))
        self._update_connection_sprite(w, 3, con_models[3], node_rect, (-1, 0))

    def _update_connection_sprite(self, connected, idx, model, rect, direction):
        if not connected:
            self.connection_sprites[idx] = None
        else:
            if self.connection_sprites[idx] is None:
                self.connection_sprites[idx] = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER)

            node = self.state.get_grid().get_node(self.grid_xy)
            neighbor = self.state.get_grid().get_connected_node_in_dir(self.grid_xy, direction,
                                                                       selectable_only=True, enabled_only=True)
            if (node is not None and node.is_enabled()
                    and neighbor is not None and neighbor.is_enabled()):
                color = colors.WHITE
            else:
                color = colors.DARK_GRAY

            self.connection_sprites[idx] = self.connection_sprites[idx].update(
                new_model=model,
                new_x=rect[0] + rect[2] // 2 - model.width() // 2,
                new_y=rect[1] + rect[3] // 2 - model.height() // 2,
                new_color=color)

    def all_sprites(self):
        for spr in super().all_sprites():
            yield spr
        yield self.icon_sprite
        yield self.icon_border_sprite
        for spr in self.connection_sprites:
            yield spr


class OverworldGridElement(ui.UiElement):

    CELL_SIZE = 24

    def __init__(self, state: OverworldState):
        ui.UiElement.__init__(self)
        self.state = state

        self.level_nodes = {}        # xy -> LevelNodeElement
        self.connector_sprites = {}  # xy -> ImageSprite

        self.locked_color = colors.DARK_GRAY
        self.unlocked_color = colors.WHITE

    def update(self):
        sprites_to_clear = set()
        for xy in self.connector_sprites:
            sprites_to_clear.add(xy)
        level_nodes_to_clear = set()
        for xy in self.level_nodes:
            level_nodes_to_clear.add(xy)

        cs = OverworldGridElement.CELL_SIZE

        for xy in self.state.get_grid().grid.indices(ignore_missing=True):
            node = self.state.get_grid().get_node(xy)
            if isinstance(node, OverworldGrid.LevelNode):
                if xy in level_nodes_to_clear:
                    level_nodes_to_clear.remove(xy)
                level_id = self.state.get_level_id_for_num(node.n)

                if xy in self.level_nodes and (self.level_nodes[xy].level_id != level_id or self.level_nodes[xy].level_num != node.n):
                    self.remove_child(self.level_nodes[xy])
                    del self.level_nodes[xy]

                if xy not in self.level_nodes:
                    self.level_nodes[xy] = LevelNodeElement.new_element(xy, level_id, node.n, self.state)
                    self.add_child(self.level_nodes[xy])

                ele = self.level_nodes[xy]
                ele.set_xy((xy[0] * cs, xy[1] * cs))
                ele.update()
            elif node.is_connector() or node.is_endpoint():
                if xy in sprites_to_clear:
                    sprites_to_clear.remove(xy)
                if xy not in self.connector_sprites:
                    self.connector_sprites[xy] = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER, depth=5)
                connections = self.state.get_grid().get_connected_directions(xy)
                spr = spriteref.overworld_sheet().get_connection_sprite(n=connections[0], e=connections[1],
                                                                        s=connections[2], w=connections[3])
                color = self.unlocked_color if self.state.is_unlocked_at(xy) else self.locked_color
                x = self.get_xy(absolute=True)[0] + xy[0] * cs
                y = self.get_xy(absolute=True)[1] + xy[1] * cs
                self.connector_sprites[xy] = self.connector_sprites[xy].update(new_model=spr, new_color=color,
                                                                               new_x=x, new_y=y)
        for xy in sprites_to_clear:
            del self.connector_sprites[xy]
        for xy in level_nodes_to_clear:
            self.remove_child(self.level_nodes[xy])
            del self.level_nodes[xy]

    def all_sprites(self):
        for xy in self.connector_sprites:
            yield self.connector_sprites[xy]

    def get_size(self):
        grid_dims = self.state.get_grid().size()
        cs = OverworldGridElement.CELL_SIZE
        return (cs * grid_dims[0], cs * grid_dims[1])

    def get_grid_pos_at(self, xy, absolute=True):
        if absolute:
            rel_xy = util.sub(xy, self.get_xy(absolute=True))
        else:
            rel_xy = xy

        cs = OverworldGridElement.CELL_SIZE
        return (rel_xy[0] // cs, rel_xy[1] // cs)


class LevelPreviewElement(ui.UiElement):

    def __init__(self):
        ui.UiElement.__init__(self)
        self._size = (188, 100)

        self.bg_border_sprite = None

        self._current_bp = None
        self._preview_sprites = []

        cs = gs.get_instance().cell_size
        self._vis_rect_in_level = [0, 0, 30 * cs, 15 * cs]

    def set_bp(self, bp: blueprints.LevelBlueprint):
        if bp != self._current_bp:
            self._current_bp = bp
            self._preview_sprites = None

    def set_size(self, size):
        self._size = size

    def update(self):
        rect = self.get_rect(absolute=True)

        border_to_use = spriteref.overworld_sheet().border_thin
        if self.bg_border_sprite is None:
            self.bg_border_sprite = sprites.BorderBoxSprite(spriteref.UI_BG_LAYER, rect, all_borders=border_to_use,
                                                            hollow_center=True)
        border_thickness = border_to_use[0].size()
        inner_rect = util.rect_expand(rect, left_expand=-border_thickness[0], right_expand=-border_thickness[0],
                                      up_expand=-border_thickness[1], down_expand=-border_thickness[1])
        self.bg_border_sprite.update(new_rect=inner_rect, new_depth=5, new_color=colors.WHITE)

        if self._preview_sprites is None:
            self._preview_sprites = []
            if self._current_bp is not None:
                for (blob, spec) in self._current_bp.all_entities():
                    self._preview_sprites.append(_EntityPreview(blob, spec))

        for preview in self._preview_sprites:
            preview.update_sprites(self._vis_rect_in_level, inner_rect)

    def get_size(self):
        return self._size

    def all_sprites(self):
        if self.bg_border_sprite is not None:
            for spr in self.bg_border_sprite.all_sprites():
                yield spr
        if self._preview_sprites is not None:
            for preview in self._preview_sprites:
                for spr in preview.all_sprites():
                    yield spr


class _EntityPreview():
    def __init__(self, blob, spec_type):
        self.blob = blob
        self.spec_type = spec_type
        self.sprites = []

    @staticmethod
    def _xform_point(xy, vis_rect_in_level, canvas_rect):
        x_new = (xy[0] - vis_rect_in_level[0]) * canvas_rect[2] / vis_rect_in_level[2] + canvas_rect[0]
        y_new = (xy[1] - vis_rect_in_level[1]) * canvas_rect[3] / vis_rect_in_level[3] + canvas_rect[1]
        x_new = min(canvas_rect[0] + canvas_rect[2], max(canvas_rect[0], x_new))
        y_new = min(canvas_rect[1] + canvas_rect[3], max(canvas_rect[1], y_new))
        return (x_new, y_new)

    @staticmethod
    def _stretch_rect_to_fit(world_rect, vis_rect_in_level, canvas_rect):
        xy1 = _EntityPreview._xform_point((world_rect[0], world_rect[1]), vis_rect_in_level, canvas_rect)
        xy2 = _EntityPreview._xform_point((world_rect[0] + world_rect[2], world_rect[1] + world_rect[3]), vis_rect_in_level, canvas_rect)
        return [xy1[0], xy1[1], xy2[0] - xy1[0], xy2[1] - xy1[1]]

    def update_sprites(self, vis_rect_in_level, canvas):
        color = blueprints.SpecUtils.get_preview_color(self.blob)
        if self.spec_type in (blueprints.SpecTypes.BLOCK, blueprints.SpecTypes.MOVING_BLOCK,
                              blueprints.SpecTypes.START_BLOCK, blueprints.SpecTypes.END_BLOCK,
                              blueprints.SpecTypes.DOOR_BLOCK):
            util.extend_or_empty_list_to_length(self.sprites, 1,
                                                creator=lambda: sprites.RectangleSprite(spriteref.POLYGON_ULTRA_OMEGA_TOP_LAYER))
            world_rect = blueprints.SpecUtils.get_rect(self.blob)

            if util.rects_intersect(world_rect, vis_rect_in_level):
                canvas_rect = _EntityPreview._stretch_rect_to_fit(world_rect, vis_rect_in_level, canvas)
                down_expand = -1 if canvas_rect[1] + canvas_rect[3] < canvas[1] + canvas[3] else 0
                right_expand = -1 if canvas_rect[0] + canvas_rect[2] < canvas[0] + canvas[2] else 0
                canvas_rect = util.rect_expand(canvas_rect, down_expand=down_expand, right_expand=right_expand)
            else:
                canvas_rect = [0, 0, 0, 0]
            self.sprites[0] = self.sprites[0].update(new_rect=canvas_rect, new_color=color)
        elif self.spec_type == blueprints.SpecTypes.SLOPE_BLOCK_QUAD:
            util.extend_or_empty_list_to_length(self.sprites, 2, creator=lambda: None)
            if self.sprites[0] is None:
                self.sprites[0] = sprites.RectangleSprite(spriteref.POLYGON_ULTRA_OMEGA_TOP_LAYER)
            if self.sprites[1] is None:
                self.sprites[1] = sprites.TriangleSprite(spriteref.POLYGON_ULTRA_OMEGA_TOP_LAYER)

            world_triangle, world_rect = self.spec_type.get_triangle_and_rect(self.blob, with_xy_offset=True)
            triangle_right = any([p[0] > world_rect[0] + world_rect[2] for p in world_triangle])
            triangle_left = any([p[0] < world_rect[0] for p in world_triangle])
            triangle_down = any([p[1] > world_rect[1] + world_rect[3] for p in world_triangle])
            triangle_up = any([p[1] < world_rect[1] for p in world_triangle])
            if util.rects_intersect(world_rect, vis_rect_in_level):
                canvas_rect = _EntityPreview._stretch_rect_to_fit(world_rect, vis_rect_in_level, canvas)
                down_expand = -1 if not triangle_down and canvas_rect[1] + canvas_rect[3] < canvas[1] + canvas[3] else 0
                right_expand = -1 if not triangle_right and canvas_rect[0] + canvas_rect[2] < canvas[0] + canvas[2] else 0
                canvas_rect = util.rect_expand(canvas_rect, down_expand=down_expand, right_expand=right_expand)
                self.sprites[0].update(new_rect=canvas_rect, new_color=color)
            if util.rect_intersects_triangle(vis_rect_in_level, world_triangle):
                canvas_triangle = [_EntityPreview._xform_point(p, vis_rect_in_level, canvas) for p in world_triangle]
                bounding_rect = util.get_rect_containing_points(canvas_triangle, inclusive=True)
                if triangle_up:
                    down_expand = 0
                else:
                    down_expand = -1 if bounding_rect[1] + bounding_rect[3] < canvas[1] + canvas[3] else 0
                if triangle_left:
                    right_expand = 0
                else:
                    right_expand = -1 if bounding_rect[0] + bounding_rect[2] < canvas[0] + canvas[2] else -1
                bounding_rect = util.rect_expand(bounding_rect, down_expand=down_expand, right_expand=right_expand)
                canvas_triangle = [util.constrain_point_to_rect(bounding_rect, p) for p in canvas_triangle]
                self.sprites[1] = self.sprites[1].update(new_points=canvas_triangle, new_color=color)

    def all_sprites(self):
        for spr in self.sprites:
            yield spr


class OverworldInfoPanelElement(ui.UiElement):

    def __init__(self, state: OverworldState):
        ui.UiElement.__init__(self)
        self.state = state

        self.title_text_sprite = None
        self.description_text_sprite = None

        self.time_text_sprite = None

        self.bg_border_sprite = None

        self.level_preview_panel_element = self.add_child(LevelPreviewElement())
        self.options_element = self.add_child(ui.OptionsList())

    def get_node_to_show(self):
        if self.state.cell_under_mouse is not None:
            node = self.state.get_grid().get_node(self.state.cell_under_mouse)
            if node is not None and node.is_level() and node.is_enabled():
                return node

        return self.state.get_selected_node()

    def get_title_text(self):
        node = self.get_node_to_show()
        if node is not None and isinstance(node, OverworldGrid.LevelNode):
            _, _, level_bp = node.get_level_info(self.state)
            level_num = node.get_pretty_level_num()
            if level_num is not None and level_bp is not None:
                world_num = self.state.get_world_num()
                return "{}-{} {}".format(world_num, level_num, level_bp.name())

        return None

    def can_play_visible_level(self) -> bool:
        node = self.get_node_to_show()
        if node is not None and isinstance(node, OverworldGrid.LevelNode):
            return node.is_selectable()
        return False

    def get_visible_level_time(self) -> sprites.TextBuilder:
        node = self.get_node_to_show()
        if node is not None and isinstance(node, OverworldGrid.LevelNode):
            _, level_id, _ = node.get_level_info(self.state)
            if level_id is not None:
                time = self.state.get_completion_time(level_id)
                if time is not None:
                    time_str = util.ticks_to_time_string(time, fps=configs.target_fps, n_decimals=2)
                    res = sprites.TextBuilder()
                    res.add(time_str, color=colors.LIGHT_GRAY)
                    return res

        res = sprites.TextBuilder()
        res.add("--:--.--", color=colors.LIGHT_GRAY)
        return res

    def get_description_text(self):
        node = self.get_node_to_show()
        if node is not None and isinstance(node, OverworldGrid.LevelNode):
            level_num, _, level_bp = node.get_level_info(self.state)
            if level_bp is not None:
                return level_bp.description()
            else:
                return None

    def update(self):
        rect = self.get_rect(absolute=True)

        border_to_use = spriteref.overworld_sheet().border_double_thin
        if self.bg_border_sprite is None:
            self.bg_border_sprite = sprites.BorderBoxSprite(spriteref.UI_BG_LAYER, rect, all_borders=border_to_use)
        border_thickness = border_to_use[0].size()
        inner_rect = util.rect_expand(rect, left_expand=-border_thickness[0], right_expand=-border_thickness[0],
                                      up_expand=-border_thickness[1], down_expand=-border_thickness[1])
        self.bg_border_sprite.update(new_rect=inner_rect, new_depth=10,
                                     new_color=colors.WHITE, new_bg_color=colors.PERFECT_BLACK)

        y_pos = rect[1] + 7

        title_text = self.get_title_text()
        if title_text is None:
            self.title_text_sprite = None
        else:
            if self.title_text_sprite is None:
                self.title_text_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, title_text, color=colors.WHITE)
            xy = (6, y_pos)
            self.title_text_sprite.update(new_x=rect[0] + xy[0], new_y=rect[1] + xy[1], new_text=title_text)
            y_pos += self.title_text_sprite.size()[1]

        self.level_preview_panel_element.set_xy((2, y_pos))
        self.level_preview_panel_element.set_size((rect[2] - 4, 90))
        y_pos += self.level_preview_panel_element.get_size()[1]

        node = self.get_node_to_show()
        if node is not None and isinstance(node, OverworldGrid.LevelNode):
            level_num, level_id, level_bp = node.get_level_info(self.state)
        else:
            level_num, level_id, level_bp = (None, None, None)

        self.level_preview_panel_element.set_bp(level_bp)

        desc_text = self.get_description_text()
        if desc_text is None:
            self.description_text_sprite = None
        else:
            font = spritesheets.get_default_font(small=True)
            if self.description_text_sprite is None:
                self.description_text_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, "test test test",
                                                                  color=colors.WHITE, font_lookup=font)
            wrapped_text_lines = sprites.TextSprite.wrap_text_to_fit(desc_text, rect[2] - 12, font_lookup=font)
            wrapped_text = "\n".join(wrapped_text_lines)
            self.description_text_sprite.update(new_x=rect[0] + 6, new_y=y_pos, new_text=wrapped_text)
            y_pos += self.description_text_sprite.size()[1]

        level_time = self.get_visible_level_time()
        if self.time_text_sprite is None:
            self.time_text_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, "abc", x_kerning=1)
        self.time_text_sprite.update(new_text=level_time.text, new_color_lookup=level_time.colors)
        time_text_x = rect[0] + rect[2] - border_thickness[0] * 2 - self.time_text_sprite.size()[0]
        time_text_y = rect[1] + rect[3] - border_thickness[1] * 2 - self.time_text_sprite.size()[1]
        self.time_text_sprite.update(new_x=time_text_x, new_y=time_text_y)

    def all_sprites(self):
        if self.bg_border_sprite is not None:
            for spr in self.bg_border_sprite.all_sprites():
                yield spr
        if self.title_text_sprite is not None:
            for spr in self.title_text_sprite.all_sprites():
                yield spr
        if self.description_text_sprite is not None:
            for spr in self.description_text_sprite.all_sprites():
                yield spr
        if self.time_text_sprite is not None:
            for spr in self.time_text_sprite.all_sprites():
                yield spr

    def get_size(self):
        return (192, renderengine.get_instance().get_game_size()[1])


class OverworldScene(scenes.Scene):

    @staticmethod
    def create_new_from_path(path):
        pack = OverworldPack.load_from_dir(path)
        state = OverworldState(pack)
        return OverworldScene(state)

    def __init__(self, state: OverworldState):
        scenes.Scene.__init__(self)
        self.state = state

        self.bg_triangle_sprites = [[] for _ in range(0, 9)]

        self.grid_ui_element = OverworldGridElement(self.state)
        self.info_panel_element = OverworldInfoPanelElement(self.state)

        self.fade_overlay = None

        self.fade_ticks = 0
        self.fade_duration = 30
        self.fading_in = None
        self.start_fading_in()

        self._overworld_after_fade_out = None
        self._entry_num_after_fade_out = None

    def start_fading_in(self):
        self.fading_in = True
        self.fade_ticks = self.fade_duration  # start at max fade, and reduce
        return self

    def fade_out_and_into(self, next_overworld, entry_num):
        self.fading_in = False
        self.fade_ticks = 0
        self._overworld_after_fade_out = next_overworld
        self._entry_num_after_fade_out = entry_num

    def _get_fade_prog(self):
        if self.fading_in is None:
            return 0
        else:
            return util.bound(self.fade_ticks / self.fade_duration, 0, 1)

    def all_sprites(self):
        for spr in self.grid_ui_element.all_sprites_from_self_and_kids():
            yield spr
        for spr in self.info_panel_element.all_sprites_from_self_and_kids():
            yield spr
        if self.fade_overlay is not None:
            yield self.fade_overlay
        for l in self.bg_triangle_sprites:
            for spr in l:
                yield spr

    def update(self):
        self._handle_mouse_inputs()
        if self.fading_in is not False:
            # lock inputs while we're fading out
            self._handle_key_inputs()

        screen_size = renderengine.get_instance().get_game_size()
        grid_size = self.grid_ui_element.get_size()
        self.grid_ui_element.set_xy((48, screen_size[1] // 2 - grid_size[1] // 2))

        self.grid_ui_element.update_self_and_kids()

        info_xy = (screen_size[0] - self.info_panel_element.get_size()[0], 0)
        self.info_panel_element.set_xy(info_xy)
        self.info_panel_element.update_self_and_kids()

        if self.fading_in is None and self.state.next_requested_overworld() is not None:
            ow, num = self.state.next_requested_overworld()
            self.fade_out_and_into(ow, num)

        fade_prog = self._get_fade_prog()
        if fade_prog == 0:
            self.fade_overlay = None
        else:
            model = spritesheets.get_instance().get_sheet(spritesheets.WhiteSquare.SHEET_ID).get_sprite(opacity=fade_prog)
            if self.fade_overlay is None:
                self.fade_overlay = sprites.ImageSprite(model, 0, 0, layer_id=spriteref.UI_FG_LAYER,
                                                        depth=-1000, color=colors.PERFECT_BLACK)
            ratio = (self.info_panel_element.get_xy(absolute=True)[0] / model.width(),
                     screen_size[1] / model.height())
            self.fade_overlay = self.fade_overlay.update(new_model=model, new_ratio=ratio)

        if self.fading_in is not None:
            if self.fading_in:
                self.fade_ticks -= 1
                if self.fade_ticks <= 0:
                    self.fading_in = None
            else:
                self.fade_ticks += 1
                if self.fade_ticks >= self.fade_duration:
                    if self._overworld_after_fade_out is not None:
                        self.state.set_current_overworld(self._overworld_after_fade_out,
                                                         entry_num=self._entry_num_after_fade_out)
                        self._overworld_after_fade_out = None
                        self._entry_num_after_fade_out = None
                        self.start_fading_in()
                    else:
                        self.fading_in = None

        self._update_bg_triangles()

    def _handle_mouse_inputs(self):
        mouse_grid_pos = None
        if inputs.get_instance().mouse_in_window():
            mouse_xy = inputs.get_instance().mouse_pos()
            mouse_grid_pos = self.grid_ui_element.get_grid_pos_at(mouse_xy, absolute=True)

        old_pos = self.state.cell_under_mouse
        if mouse_grid_pos is None:
            self.state.cell_under_mouse = None
        elif mouse_grid_pos != old_pos and inputs.get_instance().mouse_moved():
            self.state.cell_under_mouse = mouse_grid_pos

        if inputs.get_instance().mouse_was_pressed(button=1) and self.grid_ui_element.ticks_alive > 1:
            if mouse_grid_pos is not None:
                node_at_click = self.state.get_grid().get_node(mouse_grid_pos)
                if node_at_click is not None and node_at_click.is_enabled():
                    if node_at_click.is_exit():
                        # click an exit -> go to the other overworld
                        # TODO only if exit is available
                        self.state.activate_exit_node(node_at_click.get_exit_id(), instantly=False)
                    elif node_at_click.is_selectable():
                        if self.state.get_selected_node() != node_at_click:
                            # if it's not selected, select it
                            self.state.set_selected_node(node_at_click)
                        elif node_at_click.is_level():
                            # if it's already selected, activate the level
                            level_id = self.state.get_level_id_for_num(node_at_click.get_level_num())
                            self.start_level(level_id)

    def get_cursor_id_at(self, xy):
        mouse_grid_pos = self.grid_ui_element.get_grid_pos_at(xy, absolute=True)
        if mouse_grid_pos is not None:
            node_at_xy = self.state.get_grid().get_node(mouse_grid_pos)
            if node_at_xy is not None:
                if node_at_xy.is_enabled() and (node_at_xy.is_exit() or node_at_xy.is_selectable()):
                    return const.CURSOR_HAND
        return super().get_cursor_id_at(xy)

    def _handle_key_inputs(self):
        dx = 0
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_LEFT)):
            dx -= 1
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_RIGHT)):
            dx += 1

        dy = 0
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_UP)):
            dy -= 1
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_DOWN)):
            dy += 1

        # TODO tab and shift-tab to jump to the next or prev level? ..what

        if dx != 0 or dy != 0:
            orig_node = self.state.get_selected_node()
            if orig_node is not None:
                new_node = self.state.get_grid().get_connected_node_in_dir(orig_node.get_xy(), (dx, dy),
                                                                           selectable_only=True, enabled_only=True)
                if new_node is not None:
                    if new_node.is_exit():
                        self.state.activate_exit_node(new_node.get_exit_id())
                    else:
                        self.state.set_selected_node(new_node)
                        self.state.cell_under_mouse = None  # subtle QOL
                else:
                    # TODO play sound
                    pass
            else:
                # this shouldn't really happen but ehh..
                new_node = self.state.find_initial_selection()
                self.state.set_selected_node(new_node)

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_ACCEPT)):
            n = self.state.get_selected_node()
            if n is not None and n.is_enabled():
                if isinstance(n, OverworldGrid.LevelNode):
                    level_id = self.state.get_level_id_for_num(n.get_level_num())
                    self.start_level(level_id)
                else:
                    # TODO activating other node types?
                    pass
        elif inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_CANCEL)):
            import src.game.menus as menus
            self.get_manager().set_next_scene(menus.MainMenuScene())

        if configs.is_dev and inputs.get_instance().was_pressed(const.UNLOCK_ALL_DEBUG):
            debug.do_unlock_all()
            self.state.refresh_unlocked_levels()

    def start_level(self, level_id):
        level_bp = self.state.get_level_blueprint(level_id)
        state = self.state

        def _updated_scene(new_time=None, reload_levels=False):
            old_time = state.get_completion_time(level_id)
            if new_time is not None and (old_time is None or new_time < old_time):
                state.set_completed(level_id, new_time)

            if reload_levels:
                state.reload_level_blueprints_from_disk()
                state.refresh_unlocked_levels()

            new_scene = OverworldScene(state)

            nodes = new_scene.state.get_nodes_with_id(level_id)
            if len(nodes) > 0:
                new_scene.state.set_selected_node(nodes[0])

            return new_scene

        if level_bp is not None:
            import src.game.menus as menus
            if configs.is_dev and inputs.get_instance().ctrl_is_held():
                # activate edit mode
                next_scene = menus.LevelEditGameScene(level_bp,
                                                      prev_scene_provider=lambda: _updated_scene(reload_levels=True))
            else:
                # enter the level normally
                next_scene = menus.RealGameScene(level_bp,
                                                 lambda time: self.get_manager().set_next_scene(_updated_scene(new_time=time)),
                                                 lambda: self.get_manager().set_next_scene(_updated_scene()))
            self.get_manager().set_next_scene(next_scene)

    def _update_bg_triangles(self):
        size = renderengine.get_instance().get_game_size()
        size = (size[0] - self.info_panel_element.get_size()[0], size[1])

        fade_pcnt = self._get_fade_prog()

        anchors = [
            (0, 0), (size[0] // 2, 0), (size[0], 0),
            (0, size[1] // 2), (size[0] // 2, size[1] // 2), (size[0], size[1] // 2),
            (0, size[1]), (size[0] // 2, size[1]), (size[0], size[1])
        ]

        max_zoom_dist = 300
        center_pt = (size[0] // 2, size[1] // 2)
        for i in range(0, len(anchors)):
            v = util.set_length(util.sub(anchors[i], center_pt), max_zoom_dist * (fade_pcnt ** 2))
            anchors[i] = util.round_vec(util.add(anchors[i], v))

        for i in range(0, 9):
            bp_tri_list = self.state.current_overworld.bg_triangles[i]
            util.extend_or_empty_list_to_length(self.bg_triangle_sprites[i], len(bp_tri_list),
                                                lambda: sprites.TriangleSprite(spriteref.POLYGON_UI_BG_LAYER))
            for j in range(0, len(bp_tri_list)):
                p1 = util.add(anchors[i], bp_tri_list[j][0])
                p2 = util.add(anchors[i], bp_tri_list[j][1])
                p3 = util.add(anchors[i], bp_tri_list[j][2])

                color = bp_tri_list[j][3]
                self.bg_triangle_sprites[i][j] = self.bg_triangle_sprites[i][j].update(new_p1=p1, new_p2=p2, new_p3=p3,
                                                                                       new_color=color, new_depth=j)


if __name__ == "__main__":
    blueprint = OverworldBlueprint.load_from_dir("overworlds/overworld_1")
    print(blueprint)
