import traceback

import src.utils.util as util
import src.engine.inputs as inputs
import src.engine.keybinds as keybinds
import src.engine.sprites as sprites

import src.game.const as const
import src.game.spriteref as spriteref
import src.game.colors as colors

_ELEMENT_UID_COUNT = 0


def _get_next_uid():
    global _ELEMENT_UID_COUNT
    _ELEMENT_UID_COUNT += 1
    return _ELEMENT_UID_COUNT - 1


class UiElement:

    def __init__(self):
        self.uid = _get_next_uid()
        self._parent = None
        self._children = []

        self._rel_xy = (0, 0)  # position relative to parent

    def update(self):
        raise NotImplementedError()

    def all_sprites(self):
        return []

    def get_size(self):
        raise NotImplementedError()

    def all_sprites_from_self_and_kids(self):
        for c in self._children:
            for spr in c.all_sprites_from_self_and_kids():
                yield spr
        for spr in self.all_sprites():
            yield spr

    def update_self_and_kids(self):
        self.update()
        for c in self._children:
            c.update()

    def get_rect(self, absolute=False):
        xy = self.get_xy(absolute=absolute)
        size = self.get_size()
        return (xy[0], xy[1], size[0], size[1])

    def get_xy(self, absolute=False):
        if absolute and self._parent is not None:
            return util.add(self._parent.get_xy(absolute=True), self._rel_xy)
        else:
            return self._rel_xy

    def set_xy(self, rel_xy):
        self._rel_xy = rel_xy

    def add_child(self, element):
        element.set_parent(self)
        return element

    def add_children(self, elements):
        for e in elements:
            e.set_parent(self)

    def remove_child(self, element):
        if element in self._children:
            element.set_parent(None)
        else:
            print("WARN: tried to remove non-child: child={}".format(element))

    def remove_children(self, elements):
        for e in elements:
            self.remove_child(e)

    def get_parent(self):
        return self._parent

    def set_parent(self, element):
        if self._parent is not None:
            if self in self._parent._children:
                self._parent._children.remove(self)
            else:
                print("WARN: child element was disconnected from parent: child={}, parent={}".format(self, self._parent))
        self._parent = element
        if self._parent is not None:
            if self not in self._parent._children:
                self._parent._children.append(self)
            else:
                print("WARN: parent element already has reference to child?: child={}, parent={}".format(self, self._parent))

    def dfs(self, cond):
        for element in self.depth_first_traverse():
            if cond(element):
                return element
        return None

    def depth_first_traverse(self, include_self=True):
        for c in self._children:
            for element in c._children:
                yield element
        if include_self:
            yield self

    def __eq__(self, other):
        if isinstance(other, UiElement):
            return self.uid == other.uid
        else:
            return None

    def __hash__(self):
        return self.uid


class ElementGroup(UiElement):

    def __init__(self):
        UiElement.__init__(self)

    def get_size(self):
        my_xy = self.get_xy(absolute=True)
        x_size = 0
        y_size = 0
        for c in self.depth_first_traverse(include_self=False):
            c_xy = c.get_xy(absolute=True)
            c_size = c.get_size()
            x_size = max(x_size, c_xy[0] - my_xy[0] + c_size[0])
            y_size = max(y_size, c_xy[1] - my_xy[1] + c_size[1])
        return (x_size, y_size)

    def all_sprites(self):
        return []


class OptionsList(ElementGroup):

    def __init__(self):
        ElementGroup.__init__(self)
        self.selected_idx = 0
        self.options = []  # list of (UiElement: element, str: text, lambda: do_action, lambda: is_enabled)
        self.y_spacing = 4

    def add_option(self, text, do_action, is_enabled=lambda: True):
        element = SpriteElement()
        self.options.append((element, text, do_action, is_enabled))
        self.add_child(element)

    def update(self):

        if len(self.options) == 0:
            return  # probably not initialized yet

        # TODO - is this the place we should be doing this?
        # TODO - it's fine for now I think
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_UP)):
            self.selected_idx = (self.selected_idx - 1) % len(self.options)
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_DOWN)):
            self.selected_idx = (self.selected_idx + 1) % len(self.options)

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_ACCEPT)):
            if 0 <= self.selected_idx < len(self.options):
                action = self.options[self.selected_idx][2]
                try:
                    action()
                except Exception as e:
                    print("ERROR: failed to activate option: {}".format(self.options[1]))
                    traceback.print_exc()

        y = 0
        for i in range(0, len(self.options)):
            element, text, do_action, is_enabled = self.options[i]

            if not is_enabled():
                element.set_color(colors.DARK_GRAY)
            elif i == self.selected_idx:
                element.set_color(colors.PERFECT_RED)
            else:
                element.set_color(colors.PERFECT_WHITE)

            text_spr = element.get_sprite()
            if text_spr is None:
                text_spr = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, text)
                element.set_sprite(text_spr)

            element.set_xy((0, y))
            y += element.get_size()[1] + self.y_spacing


class SpriteElement(UiElement):

    def __init__(self, sprite=None):
        UiElement.__init__(self)
        self.sprite = None
        self.color = colors.PERFECT_WHITE
        self.set_sprite(sprite)

    def set_sprite(self, sprite):
        if sprite is None:
            self.sprite = None
        else:
            # XXX only supports sprites that can handle `update(new_x=int, new_y=int)`
            if not isinstance(sprite, sprites.ImageSprite) and not isinstance(sprite, sprites.TextSprite):
                raise ValueError("unsupported sprite type: {}".format(type(sprite).__name__))
            self.sprite = sprite

    def get_sprite(self):
        return self.sprite

    def set_color(self, color):
        self.color = color if color is not None else colors.PERFECT_WHITE

    def update(self):
        abs_xy = self.get_xy(absolute=True)
        if self.sprite is not None:
            self.sprite = self.sprite.update(new_x=abs_xy[0], new_y=abs_xy[1], new_color=self.color)

    def all_sprites(self):
        if self.sprite is not None:
            for spr in self.sprite.all_sprites():
                yield spr

    def get_size(self):
        if self.sprite is not None:
            return self.sprite.size()
        else:
            return (0, 0)