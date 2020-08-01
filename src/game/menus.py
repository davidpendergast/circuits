
import src.engine.scenes as scenes
import src.game.blueprints as blueprints
import src.game.worldview as worldview
import src.engine.inputs as inputs
import src.engine.keybinds as keybinds
import src.game.const as const
import configs as configs
import src.game.debug as debug
import src.utils.util as util


class OptionMenuScene(scenes.Scene):

    def __init__(self):
        scenes.Scene.__init__(self)

    def update(self):
        pass

    def all_sprites(self):
        pass


class DebugGameScene(scenes.Scene):

    def __init__(self, world_type=0):
        scenes.Scene.__init__(self)
        self._world = None
        self._world_view = None

        self._cur_test_world = world_type
        self._create_new_world(world_type=world_type)

    def update(self):
        if inputs.get_instance().mouse_was_pressed() and inputs.get_instance().mouse_in_window():  # debug
            screen_pos = inputs.get_instance().mouse_pos()
            pos_in_world = self._world_view.screen_pos_to_world_pos(screen_pos)

            cell_size = gs.get_instance().cell_size
            print("INFO: mouse pressed at ({}, {})".format(int(pos_in_world[0]) // cell_size,
                                                           int(pos_in_world[1]) // cell_size))

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.RESET)):
            self._create_new_world(world_type=self._cur_test_world)

        if configs.is_dev and inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.NEXT_LEVEL_DEBUG)):
            self._cur_test_world += 1
            self._create_new_world(world_type=self._cur_test_world)

        if configs.is_dev and inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.TOGGLE_SPRITE_MODE_DEBUG)):
            debug.toggle_debug_sprite_mode()

        if inputs.get_instance().mouse_is_dragging(button=1):
            drag_this_frame = inputs.get_instance().mouse_drag_this_frame(button=1)
            if drag_this_frame is not None:
                dxy = util.sub(drag_this_frame[1], drag_this_frame[0])
                dxy = util.mult(dxy, -1 / self._world_view.get_zoom())
                self._world_view.move_camera_in_world(dxy)
                self._world_view.set_free_camera(True)
        if self._world is not None:
            self._world.update()
        if self._world_view is not None:
            self._world_view.update()

    def all_sprites(self):
        if self._world_view is not None:
            for spr in self._world_view.all_sprites():
                yield spr
        else:
            return []

    def _create_new_world(self, world_type=0):
        types = ("moving_plat", "full_level", "floating_blocks", "start_and_end")
        type_to_use = types[world_type % len(types)]
        print("INFO: activating test world: {}".format(type_to_use))

        if type_to_use == types[0]:
            self._world = blueprints.get_test_blueprint_0().create_world()
        elif type_to_use == types[1]:
            self._world = blueprints.get_test_blueprint_1().create_world()
        elif type_to_use == types[2]:
            self._world = blueprints.get_test_blueprint_2().create_world()
        elif type_to_use == types[3]:
            self._world = blueprints.get_test_blueprint_3().create_world()
        else:
            return

        self._world_view = worldview.WorldView(self._world)


