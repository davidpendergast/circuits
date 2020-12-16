
import math
import traceback
import os
import random
import re
from collections import deque

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

    class LevelNode(OverworldNode):

        def __init__(self, xy, n):
            OverworldGrid.OverworldNode.__init__(self, xy)
            self.n = n

        def __repr__(self):
            return str(self.n)

        def get_level_num(self):
            return self.n

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

        def __init__(self, xy, exit_id):
            OverworldGrid.OverworldNode.__init__(self, xy)
            self._exit_id = exit_id

        def is_exit(self):
            return True

        def is_endpoint(self):
            return True

        def get_exit_id(self):
            return self._exit_id

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

    class GameEndNode(OverworldNode):

        @staticmethod
        def is_valid_game_end_text(text) -> bool:
            return text == "f"

        def is_endpoint(self):
            return True

        def is_end(self):
            return True

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
        return [e for e in self.all_nodes(cond=lambda n: e.is_exit())]

    def get_exit_node(self, exit_id):
        return self.search_for_node(lambda n: n.is_exit() and n.get_exit_id() == exit_id)

    def get_all_level_nodes(self):
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

                    if node_text.isnumeric():
                        parsed.append(OverworldGrid.LevelNode(xy, int(node_text)))
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
                            if color == "light_gray":
                                color = colors.LIGHT_GRAY
                            elif color == "dark_gray":
                                color = colors.DARK_GRAY
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

            return OverworldBlueprint(ident, name, author, grid, levels, bg_triangles)

        except Exception as e:
            print("ERROR: failed to load overworld \"{}\"".format(path))
            traceback.print_exc()
            return None

    def __init__(self, ref_id, name, author, grid, level_lookup, bg_triangles):
        self.name = name
        self.ref_id = ref_id
        self.author = author
        self.grid = grid
        self.levels = level_lookup
        self.bg_triangles = bg_triangles

    def __repr__(self):
        return "\n".join([
            "OverworldBlueprint: {}".format(self.ref_id),
            "  name={}".format(self.name),
            "  author={}".format(self.author),
            "  grid=\n{}".format(self.grid),
            "  levels={}".format(self.levels)
        ])


class OverworldState:

    def __init__(self, world_blueprint: OverworldBlueprint, level_blueprints, came_from=None):
        """level_blueprints level_id -> level_blueprint"""
        self.world_blueprint = world_blueprint
        self.level_blueprints = level_blueprints

        self.completed_levels = {}  # level_id -> completion time (in ticks)

        self.update_nodes()

        self.selected_cell = self.find_initial_selection(came_from_exit_id=came_from)

    def get_grid(self) -> OverworldGrid:
        return self.world_blueprint.grid

    def get_level_blueprint(self, level_id) -> blueprints.LevelBlueprint:
        if level_id in self.level_blueprints:
            return self.level_blueprints[level_id]
        else:
            return None

    def get_level_id_for_num(self, n) -> str:
        if n in self.world_blueprint.levels:
            return self.world_blueprint.levels[n]
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
        # TODO put this in the spec file
        return 1

    def is_complete(self, level_id):
        return level_id in self.completed_levels

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
        # TODO
        return True

    def get_completion_time(self, level_id):
        if level_id in self.completed_levels:
            return self.completed_levels[level_id]
        else:
            return None

    def set_completed(self, level_id, time):
        cur_time = self.get_completion_time(level_id)
        if cur_time is None or cur_time > time:
            self.completed_levels[level_id] = time

    def update_nodes(self):
        # TODO set nodes to locked / unlocked
        pass

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

    def __init__(self, xy, level_id, level_num, overworld_state):
        ui.UiElement.__init__(self)
        self.grid_xy = xy
        self.level_id = level_id
        self.level_num = level_num
        self.state = overworld_state

        self.icon_sprites = [None] * 9

        self.number_sprite = None

        self._cached_player_types = None

    def _get_icon_img_and_color_at(self, idx, selected, completed, unlocked, players_in_level):
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
            color = colors.PERFECT_WHITE  # XXX the sprites are drawn with off-white already
        elif unlocked:
            color = colors.LIGHT_GRAY
        else:
            color = colors.DARK_GRAY

        if idx in corners:
            player_type = corners[idx]
            if player_type in players_in_level:
                return full_sprites[idx], colors.PERFECT_WHITE
            else:
                return empty_sprites[idx], color
        else:
            return empty_sprites[idx], color

    def _get_text_color(self, selected, completed, unlocked):
        if completed:
            return colors.WHITE
        elif unlocked:
            return colors.LIGHT_GRAY
        else:
            return colors.DARK_GRAY

    def get_player_types(self):
        if self._cached_player_types is None:
            level_bp = self.state.get_level_blueprint(self.level_id)
            self._cached_player_types = level_bp.get_player_types() if level_bp is not None else []

            # TODO rm, debug
            self._cached_player_types = random.choices([t for t in playertypes.PlayerTypes.all_types()], k=3)
        return self._cached_player_types

    def update(self):
        selected = self.state.is_selected_at(self.grid_xy)
        unlocked = self.state.is_unlocked_at(self.grid_xy)

        completed = self.state.is_complete(self.level_id)
        players = self.get_player_types()

        xy = self.get_xy(absolute=True)
        i_x = 0
        i_y = 0
        for i in range(0, len(self.icon_sprites)):
            if i % 3 == 0:
                i_x = 0
            if self.icon_sprites[i] is None:
                self.icon_sprites[i] = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER, scale=1, depth=5)
            model, color = self._get_icon_img_and_color_at(i, selected, completed, unlocked, players)

            self.icon_sprites[i] = self.icon_sprites[i].update(new_model=model, new_x=xy[0] + i_x, new_y=xy[1] + i_y,
                                                               new_color=color)
            i_x += self.icon_sprites[i].width()
            if i % 3 == 2:
                i_y += self.icon_sprites[i].height()

        if self.number_sprite is None:
            self.number_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, str(self.level_num), x_kerning=0)

        size = self.get_size()
        t_xy = (xy[0] + size[0] // 2 - self.number_sprite.size()[0] // 2,
                xy[1] + size[1] // 2 - self.number_sprite.size()[1] // 2)
        t_color = self._get_text_color(selected, completed, unlocked)
        self.number_sprite = self.number_sprite.update(new_x=t_xy[0], new_y=t_xy[1],
                                                       new_color=t_color, new_depth=0, new_scale=1)

    def all_sprites(self):
        for spr in self.icon_sprites:
            if spr is not None:
                yield spr
        for spr in self.number_sprite.all_sprites():
            yield spr

    def get_size(self):
        return (24, 24)


class OverworldGridElement(ui.UiElement):

    def __init__(self, state: OverworldState):
        ui.UiElement.__init__(self)
        self.state = state
        self.level_nodes = {}        # xy -> LevelNodeElement
        self.connector_sprites = {}  # xy -> ImageSprite

        self.locked_color = colors.DARK_GRAY
        self.unlocked_color = colors.WHITE

    def update(self):
        for xy in self.state.get_grid().grid.indices(ignore_missing=True):
            node = self.state.get_grid().get_node(xy)
            if isinstance(node, OverworldGrid.LevelNode):
                if xy not in self.level_nodes:
                    level_id = self.state.get_level_id_for_num(node.n)
                    self.level_nodes[xy] = LevelNodeElement(xy, level_id, node.n, self.state)
                    self.add_child(self.level_nodes[xy])
                ele = self.level_nodes[xy]
                ele.set_xy((xy[0] * 24, xy[1] * 24))
                ele.update()
            elif node.is_connector() or node.is_endpoint():
                if xy not in self.connector_sprites:
                    self.connector_sprites[xy] = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER, depth=5)
                connections = self.state.get_grid().get_connected_directions(xy)
                spr = spriteref.overworld_sheet().get_connection_sprite(n=connections[0], e=connections[1],
                                                                        s=connections[2], w=connections[3])
                color = self.unlocked_color if self.state.is_unlocked_at(xy) else self.locked_color
                x = self.get_xy(absolute=True)[0] + xy[0] * 24
                y = self.get_xy(absolute=True)[1] + xy[1] * 24
                self.connector_sprites[xy] = self.connector_sprites[xy].update(new_model=spr, new_color=color,
                                                                               new_x=x, new_y=y)

    def all_sprites(self):
        for xy in self.connector_sprites:
            yield self.connector_sprites[xy]

    def get_size(self):
        grid_dims = self.state.get_grid().size()
        return (24 * grid_dims[0], 24 * grid_dims[1])


class LevelPreviewElement(ui.UiElement):

    def __init__(self):
        ui.UiElement.__init__(self)
        self._size = (188, 92)

        self.bg_border_sprite = None

    def set_size(self, size):
        self._size = size

    def update(self):
        rect = self.get_rect(absolute=True)

        border_to_use = spriteref.overworld_sheet().border_thin
        if self.bg_border_sprite is None:
            self.bg_border_sprite = sprites.BorderBoxSprite(spriteref.UI_BG_LAYER, rect, all_borders=border_to_use)
        border_thickness = border_to_use[0].size()
        inner_rect = util.rect_expand(rect, left_expand=-border_thickness[0], right_expand=-border_thickness[0],
                                      up_expand=-border_thickness[1], down_expand=-border_thickness[1])
        self.bg_border_sprite.update(new_rect=inner_rect, new_depth=5,
                                     new_color=colors.WHITE, new_bg_color=colors.PERFECT_BLACK)

    def get_size(self):
        return self._size

    def all_sprites(self):
        if self.bg_border_sprite is not None:
            for spr in self.bg_border_sprite.all_sprites():
                yield spr


class OverworldInfoPanelElement(ui.UiElement):

    def __init__(self, state):
        ui.UiElement.__init__(self)
        self.state = state

        self.title_text_sprite = None
        self.description_text_sprite = None

        self.play_text_sprite = None
        self.time_text_sprite = None

        self.bg_border_sprite = None

        self.level_preview_panel_element = self.add_child(LevelPreviewElement())
        self.options_element = self.add_child(ui.OptionsList())

    def get_title_text(self):
        level_num, level_bp = self.state.get_selected_level()
        if level_num is not None and level_bp is not None:
            world_num = self.state.get_world_num()
            return "{}-{} {}".format(world_num, level_num, level_bp.name())
        else:
            return None

    def can_play_selected_level(self) -> bool:
        n = self.state.get_selected_node()
        if n is not None and isinstance(n, OverworldGrid.LevelNode):
            if n.is_selectable():
                return True
        return False

    def get_selected_level_time(self) -> sprites.TextBuilder:
        level_id = self.state.get_selected_level_id()
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
        level_num, level_bp = self.state.get_selected_level()
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

        play_text = sprites.TextBuilder()
        if self.can_play_selected_level():
            play_text.add("Play", color=colors.PERFECT_RED)
        else:
            play_text.add("Locked", color=colors.DARK_GRAY)

        # TODO this looks pretty bad...
        if self.play_text_sprite is None:
            self.play_text_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, play_text.text,
                                                       color_lookup=play_text.colors, scale=1)
        self.play_text_sprite.update(new_text=play_text.text, new_color_lookup=play_text.colors)
        play_text_x = rect[0] + border_thickness[0] * 2
        play_text_y = rect[1] + rect[3] - border_thickness[1] * 2 - self.play_text_sprite.size()[1]
        self.play_text_sprite.update(new_x=play_text_x, new_y=play_text_y)

        level_time = self.get_selected_level_time()
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
        if self.play_text_sprite is not None:
            for spr in self.play_text_sprite.all_sprites():
                yield spr
        if self.time_text_sprite is not None:
            for spr in self.time_text_sprite.all_sprites():
                yield spr

    def get_size(self):
        return (192, renderengine.get_instance().get_game_size()[1])


class OverworldScene(scenes.Scene):

    def __init__(self, path, state=None):
        scenes.Scene.__init__(self)
        self._path_loaded_from = path

        if state is None:
            bp = OverworldBlueprint.load_from_dir(path)
            levels = blueprints.load_all_levels_from_dir(os.path.join(path, "levels"))
            self.state = OverworldState(bp, levels)
        else:
            self.state = state

        self.bg_triangle_sprites = [[] for _ in range(0, 9)]

        self.grid_ui_element = OverworldGridElement(self.state)
        self.info_panel_element = OverworldInfoPanelElement(self.state)

    def all_sprites(self):
        for spr in self.grid_ui_element.all_sprites_from_self_and_kids():
            yield spr
        for spr in self.info_panel_element.all_sprites_from_self_and_kids():
            yield spr
        for l in self.bg_triangle_sprites:
            for spr in l:
                yield spr

    def update(self):
        self.handle_inputs()

        screen_size = renderengine.get_instance().get_game_size()
        grid_size = self.grid_ui_element.get_size()
        self.grid_ui_element.set_xy((48, screen_size[1] // 2 - grid_size[1] // 2))

        self.grid_ui_element.update_self_and_kids()

        info_xy = (screen_size[0] - self.info_panel_element.get_size()[0], 0)
        self.info_panel_element.set_xy(info_xy)
        self.info_panel_element.update_self_and_kids()

        self._update_bg_triangles()

    def handle_inputs(self):
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

        # TODO tab and shift-tab to jump to the next or prev level?

        if dx != 0 or dy != 0:
            orig_node = self.state.get_selected_node()
            if orig_node is not None:
                new_node = self.state.get_grid().get_connected_node_in_dir(orig_node.get_xy(), (dx, dy),
                                                                           selectable_only=True, enabled_only=True)
                if new_node is not None:
                    # TODO if it's an exit node, do exit sequence?
                    # TODO or maybe it would be better to show some info about where it goes?
                    self.state.set_selected_node(new_node)
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

    def start_level(self, level_id):
        level_bp = self.state.get_level_blueprint(level_id)
        menu_manager = self.get_manager()
        state = self.state
        path = self._path_loaded_from

        def _return_to_overworld(time):
            old_time = state.get_completion_time(level_id)
            if time is not None and old_time is None or time < old_time:
                state.set_completed(level_id, time)
            new_scene = OverworldScene(path, state=state)

            nodes = new_scene.state.get_nodes_with_id(level_id)
            if len(nodes) > 0:
                new_scene.state.set_selected_node(nodes[0])

            menu_manager.set_next_scene(new_scene)

        if level_bp is not None:
            import src.game.menus as menus
            self.get_manager().set_next_scene(menus.RealGameScene(level_bp,
                                                                  lambda time: _return_to_overworld(time),
                                                                  lambda: _return_to_overworld(None)))

    def _update_bg_triangles(self):
        size = renderengine.get_instance().get_game_size()
        size = (size[0] - self.info_panel_element.get_size()[0], size[1])

        anchors = [
            (0, 0), (size[0] // 2, 0), (size[0], 0),
            (0, size[1] // 2), (size[0] // 2, size[1] // 2), (size[0], size[1] // 2),
            (0, size[1]), (size[0] // 2, size[1]), (size[0], size[1])
        ]

        for i in range(0, 9):
            bp_tri_list = self.state.world_blueprint.bg_triangles[i]
            util.extend_or_empty_list_to_length(self.bg_triangle_sprites[i], len(bp_tri_list),
                                                lambda: sprites.TriangleSprite(spriteref.POLYGON_LAYER))
            for j in range(0, len(bp_tri_list)):
                p1 = util.add(anchors[i], bp_tri_list[j][0])
                p2 = util.add(anchors[i], bp_tri_list[j][1])
                p3 = util.add(anchors[i], bp_tri_list[j][2])

                color = bp_tri_list[j][3]
                self.bg_triangle_sprites[i][j] = self.bg_triangle_sprites[i][j].update(new_p1=p1, new_p2=p2, new_p3=p3,
                                                                                       new_color=color, new_depth=j)


if __name__ == "__main__":
    blueprint = OverworldBlueprint.load_from_dir("overworlds/test_overworld")
    print(blueprint)
