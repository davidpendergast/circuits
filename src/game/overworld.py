
import math
import traceback
import os

import src.engine.scenes as scenes
import src.game.blueprints as blueprints
import src.game.worldview as worldview
import src.engine.inputs as inputs
import src.engine.keybinds as keybinds
import src.engine.sprites as sprites
import src.game.globalstate as gs
import src.engine.renderengine as renderengine
import src.game.const as const
import configs as configs
import src.game.debug as debug
import src.utils.util as util
import src.game.ui as ui
import src.game.spriteref as spriteref
import src.game.colors as colors


class OverworldGrid:

    class OverworldNode:

        def __init__(self):
            self._enabled = True

        def is_enabled(self):
            return self._enabled

        def set_enabled(self, val):
            self._enabled = val

    class LevelNode(OverworldNode):

        def __init__(self, n):
            OverworldGrid.OverworldNode.__init__(self)
            self.n = n

        def __repr__(self):
            return str(self.n)

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

        def __init__(self, con_type):
            OverworldGrid.OverworldNode.__init__(self)
            self.con_type = con_type

        def __repr__(self):
            return self.con_type

        def allows_connection(self, n=False, e=False, w=False, s=False):
            if self.con_type == OverworldGrid.ConnectionNode.FREE:
                return True
            elif self.con_type == OverworldGrid.ConnectionNode.VERT:
                return not e and not w
            elif self.con_type == OverworldGrid.ConnectionNode.HORZ:
                return not n and not s
            else:
                raise ValueError("unhandled connection type: {}".format(self.con_type))

    def __init__(self, w, h):
        self.grid = util.Grid(w, h)

    def size(self):
        return self.grid.size()

    def is_valid(self, xy):
        w, h = self.size()
        return 0 <= xy[0] < w and 0 <= xy[1] < h

    def get_node(self, xy):
        if self.grid.is_valid(xy):
            return self.grid.get(xy)
        else:
            return None

    def set_node(self, xy, val):
        self.grid.set(xy, val, expand_if_needed=True)

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
            for line in raw_grid:
                parsed = []
                for i in range(0, int(math.ceil(len(line) / data_stride))):
                    start = i * data_stride
                    end = min(len(line) - 1, (i + 1) * data_stride)
                    node_text = line[start:end]
                    node_text = node_text.strip()  # rm whitespace

                    if node_text.isnumeric():
                        parsed.append(OverworldGrid.LevelNode(int(node_text)))
                    elif OverworldGrid.ConnectionNode.is_valid_con_type(node_text):
                        parsed.append(OverworldGrid.ConnectionNode(node_text))
                    else:
                        # empty space, hopefully
                        parsed.append(None)
                parsed_grid.append(parsed)

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

            return OverworldBlueprint(ident, name, author, grid, levels)

        except Exception as e:
            print("ERROR: failed to load overworld \"{}\"".format(path))
            traceback.print_exc()


    def __init__(self, ref_id, name, author, grid, level_lookup):
        self.name = name
        self.ref_id = ref_id
        self.author = author
        self.grid = grid
        self.levels = level_lookup

    def __repr__(self):
        return "\n".join([
            "OverworldBlueprint: {}".format(self.ref_id),
            "  name={}".format(self.name),
            "  author={}".format(self.author),
            "  grid=\n{}".format(self.grid),
            "  levels={}".format(self.levels)
        ])


class OverworldState:

    def __init__(self, world_blueprint: OverworldBlueprint, level_blueprints):
        """level_blueprints level_id -> level_blueprint"""
        self.world_blueprint = world_blueprint
        self.level_blueprints = level_blueprints

        self.selected_cell = None

        self.completed_levels = {}  # level_id -> completion time (in ticks)

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

    def is_complete(self, level_id):
        return level_id in self.completed_levels

    def is_selected(self, level_id):
        # TODO this assumes that level ids will are unique between different cells
        if self.selected_cell is None:
            return False
        else:
            node = self.world_blueprint.grid.get(self.selected_cell)
            if node is not None and isinstance(node, LevelNodeElement):
                return node.level_id == level_id
            return False

    def is_unlocked(self, level_id):
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


class LevelNodeElement(ui.UiElement):

    def __init__(self, level_id, level_num, overworld_state):
        ui.UiElement.__init__(self)
        self.level_id = level_id
        self.level_num = level_num
        self.state = overworld_state

        self.icon_sprites = [None] * 9

        self.number_sprite = None

    def _get_icon_img_and_color_at(self, idx, selected, completed, unlocked, players_in_level):
        corners = {
            0: const.PLAYER_FAST,
            2: const.PLAYER_SMALL,
            6: const.PLAYER_HEAVY,
            8: const.PLAYER_FLYING
        }
        if unlocked:
            full_sprites = spriteref.overworld_sheet().level_icon_full_pieces
            empty_sprites = spriteref.overworld_sheet().level_icon_empty_pieces
        else:
            full_sprites = spriteref.overworld_sheet().level_icon_full_gray_pieces
            empty_sprites = spriteref.overworld_sheet().level_icon_empty_gray_pieces

        color = colors.PERFECT_RED if selected else colors.PERFECT_WHITE

        if idx in corners:
            player_type = corners[idx]
            if player_type in players_in_level:
                return full_sprites[idx], colors.PERFECT_WHITE
            else:
                return empty_sprites[idx], color
        else:
            return empty_sprites[idx], color

    def _get_text_color(self, selected, completed, unlocked):
        if not unlocked:
            return colors.DARK_GRAY
        else:
            return colors.WHITE

    def update(self):
        completed = self.state.is_complete(self.level_id)
        selected = self.state.is_selected(self.level_id)
        unlocked = self.state.is_unlocked(self.level_id)
        level_bp = self.state.get_level_blueprint(self.level_id)
        players = level_bp.get_player_types() if level_bp is not None else []

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

        #if self.number_sprite is None:
        #    self.number_sprite = sprites.TextSprite(spr)

    def all_sprites(self):
        for spr in self.icon_sprites:
            if spr is not None:
                yield spr

    def get_size(self):
        return (24, 24)


class OverworldGridElement(ui.UiElement):

    def __init__(self, state: OverworldState):
        ui.UiElement.__init__(self)
        self.state = state
        self.level_nodes = {}        # xy -> LevelNodeElement
        self.connector_sprites = {}  # xy -> ImageSprite

    def update(self):
        for xy in self.state.get_grid().grid.indices(ignore_missing=True):
            node = self.state.get_grid().get_node(xy)
            if isinstance(node, OverworldGrid.LevelNode):
                if xy not in self.level_nodes:
                    level_id = self.state.get_level_id_for_num(node.n)
                    self.level_nodes[xy] = LevelNodeElement(level_id, node.n, self.state)
                    self.add_child(self.level_nodes[xy])
                ele = self.level_nodes[xy]
                ele.set_xy((xy[0] * 24, xy[1] * 24))
                ele.update()
            elif isinstance(node, OverworldGrid.ConnectionNode):
                pass

    def all_sprites(self):
        return []

    def get_size(self):
        grid_dims = self.state.get_grid().size()
        return (24 * grid_dims[0], 24 * grid_dims[1])


class OverworldScene(scenes.Scene):

    def __init__(self, path):
        scenes.Scene.__init__(self)
        blueprint = OverworldBlueprint.load_from_dir(path)
        levels = blueprints.load_all_levels_from_dir(os.path.join(path, "levels"))

        self.state = OverworldState(blueprint, levels)

        self.bg_sprite = None

        self.grid_ui_element = OverworldGridElement(self.state)
        self.info_panel_element = None

    def all_sprites(self):
        for spr in self.grid_ui_element.all_sprites_from_self_and_kids():
            yield spr

    def update(self):
        self.handle_inputs()

        self.grid_ui_element.update_self_and_kids()

    def handle_inputs(self):
        pass


if __name__ == "__main__":
    blueprint = OverworldBlueprint.load_from_dir("overworlds/test_overworld")
    print(blueprint)
