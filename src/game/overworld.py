
import math
import traceback

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
        self.grid = []
        for _ in range(0, h):
            self.grid.append([None] * w)

    def size(self):
        return (len(self.grid[0]), len(self.grid))

    def is_valid(self, xy):
        w, h = self.size()
        return 0 <= xy[0] < w and 0 <= xy[1] < h

    def get_node(self, xy):
        if self.is_valid(xy):
            return self.grid[xy[0]][xy[1]]
        else:
            return None

    def set_node(self, xy, val):
        if not self.is_valid(xy):
            raise ValueError("grid cell is out of bounds for size={}: {}".format(self.size(), xy))
        else:
            self.grid[xy[1]][xy[0]] = val


class OverworldBlueprint:

    @staticmethod
    def load_from_file(filepath):
        try:
            json_blob = util.load_json_from_path(filepath)

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
                    grid.set_node((x, y), node)
                    if node is not None and isinstance(node, OverworldGrid.LevelNode):
                        levels[node.n] = util.read_string(json_blob, "lvl_{}".format(node.n), default=None)

            return OverworldBlueprint(ident, name, author, grid, levels)

        except Exception as e:
            print("ERROR: failed to load overworld \"{}\"".format(filepath))
            traceback.print_exc()

    def __init__(self, ref_id, name, author, grid, level_lookup):
        self.name = name
        self.ref_id = ref_id
        self.author = author
        self.grid = grid
        self.levels = level_lookup


class OverworldState:

    def __init__(self):
        pass


class OverworldScene(scenes.Scene):

    def __init__(self):
        pass


if __name__ == "__main__":
    blueprint = OverworldBlueprint.load_from_file("overworlds/test_overworld.json")
    print(blueprint)