import traceback
import pygame

import src.utils.util as util
import src.engine.inputs as inputs
import src.engine.keybinds as keybinds
import src.engine.sprites as sprites
import src.engine.globaltimer as globaltimer
import src.engine.spritesheets as spritesheets

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

        self.focus_manager = None

    def update(self):
        raise NotImplementedError()

    def get_uid(self):
        return self.uid

    def all_sprites(self):
        return []

    def get_size(self):
        raise NotImplementedError()

    def set_focus_manager(self, manager):
        self.focus_manager = manager

    def is_focused(self):
        if self.focus_manager is None:
            return True
        else:
            return self.focus_manager.is_focused(self)

    def all_sprites_from_self_and_kids(self):
        for c in self._children:
            for spr in c.all_sprites_from_self_and_kids():
                yield spr
        for spr in self.all_sprites():
            yield spr

    def update_self_and_kids(self):
        self.update()
        for c in self._children:
            c.update_self_and_kids()

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

    def has_child(self, element):
        return element in self._children

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

        # the option that'll fire when you press esc (AKA back)
        self._esc_option = None

    def add_option(self, text, do_action, is_enabled=lambda: True, esc_option=False):
        self.insert_option(len(self.options), text, do_action, is_enabled=is_enabled, esc_option=esc_option)

    def insert_option(self, idx, text, do_action, is_enabled=lambda: True, esc_option=False):
        element = SpriteElement()
        opt = (element, text, do_action, is_enabled)
        self.options.insert(idx, opt)
        self.add_child(element)
        if esc_option:
            self._esc_option = opt

    def num_options(self):
        return len(self.options)

    def update(self):
        if len(self.options) == 0:
            return  # probably not initialized yet

        # TODO - is this the place we should be doing this?
        # TODO - it's fine for now I think
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_UP)):
            self.selected_idx = (self.selected_idx - 1) % len(self.options)
        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_DOWN)):
            self.selected_idx = (self.selected_idx + 1) % len(self.options)

        did_activation = False

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_CANCEL)):
            if self._esc_option is not None:
                did_activation = self._try_to_activate_option(self._esc_option)

        if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_ACCEPT)):
            if not did_activation and 0 <= self.selected_idx < len(self.options):
                did_activation = self._try_to_activate_option(self.options[self.selected_idx])

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

    def _try_to_activate_option(self, opt):
        element, text, do_action, is_enabled = opt
        try:
            if is_enabled():
                do_action()
                return True
        except Exception:
            print("ERROR: failed to activate option: {}".format(self.options[1]))
            traceback.print_exc()
            return False
        return False


class MultiPageOptionsList(OptionsList):

    def __init__(self, opts_per_page=8, next_text="next", prev_text="prev"):
        OptionsList.__init__(self)
        self.pages = []

        self.opts_per_page = opts_per_page
        self.next_text = next_text
        self.prev_text = prev_text
        self.cur_page = 0

    def set_current_page(self, idx):
        self.cur_page = idx
        self._refresh_children()

    def _refresh_children(self):
        for i in range(0, len(self.pages)):
            if i == self.cur_page:
                if not self.has_child(self.pages[i]):
                    self.add_child(self.pages[i])
            else:
                if self.has_child(self.pages[i]):
                    self.remove_child(self.pages[i])

    def _add_new_page(self):
        if len(self.pages) == 0:
            self.pages.append(OptionsList())
        elif len(self.pages) == 1:
            first_page = self.pages[0]
            new_page = OptionsList()
            self.pages.append(new_page)

            first_page.add_option(self.next_text, lambda: self.set_current_page(1))
            new_page.add_option(self.prev_text, lambda: self.set_current_page(0))
        else:
            n = len(self.pages)
            prev_page = self.pages[n - 1]
            new_page = OptionsList()
            self.pages.append(new_page)

            prev_page.insert_option(len(prev_page.num_options()) - 1, self.next_text, lambda: self.set_current_page(n))
            new_page.add_option(self.prev_text, lambda: self.set_current_page(n - 1))

        self._refresh_children()
        return self.pages[-1]

    def add_option(self, text, do_action, is_enabled=lambda: True, esc_option=False):
        if len(self.pages) == 0:
            last_page = self._add_new_page()
        elif len(self.pages) == 1 and self.pages[0].num_options() >= self.opts_per_page:
            last_page = self._add_new_page()
        elif self.pages[-1].num_options() + 1 >= self.opts_per_page:
            last_page = self._add_new_page()
        else:
            last_page = self.pages[-1]

        idx_to_add_at = last_page.num_options() if len(self.pages) == 1 else last_page.num_options() - 1
        last_page.insert_option(idx_to_add_at, text, do_action, is_enabled=is_enabled, esc_option=esc_option)
        self._refresh_children()


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


class FocusManager:

    def __init__(self):
        self.focused_element_uid = None

    def set_focused(self, element):
        if element is not None:
            self.focused_element_uid = element.get_uid()
        else:
            self.focused_element_uid = None

    def is_focused(self, element):
        return element is not None and self.focused_element_uid == element.get_uid()


class TextEditElement(UiElement):

    CURSOR_CHAR = "_"

    def __init__(self, text, scale=1, color=None, font=None, char_limit=24, outline_color=None):
        UiElement.__init__(self)

        self.text = text

        self.scale = scale
        self.color = color
        self.char_limit = char_limit
        self.font = font if font is not None else spritesheets.get_default_font(mono=True)
        self.text_sprite = None

        self.outline_color = outline_color
        self.outline_inset = 2
        self.bg_sprite = None

        self.cursor_pos = len(text)
        self._dummy_text_for_size_calc = None

    def get_text_for_display(self):
        anim_tick = (globaltimer.tick_count() // 20) % 2
        if anim_tick == 0 and self.is_focused() and len(self.text) < self.char_limit:
            if self.cursor_pos >= len(self.text):
                return self.text + TextEditElement.CURSOR_CHAR
            else:
                l = list(self.text)
                l[max(0, self.cursor_pos)] = TextEditElement.CURSOR_CHAR
                return "".join(l)
        else:
            return self.text

    def has_outline(self):
        return self.outline_color is not None

    def get_size(self):
        if self._dummy_text_for_size_calc is None:
            # hope it's monospaced~
            self._dummy_text_for_size_calc = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0,
                    "X" * self.char_limit,
                    scale=self.scale,
                    font_lookup=self.font)
        self._dummy_text_for_size_calc.update(new_text="X" * self.char_limit)
        size = self._dummy_text_for_size_calc.size()
        if self.has_outline():
            size = (size[0] + self.outline_inset * 2, size[1] + self.outline_inset * 2)

        return size

    def get_text(self):
        return self.text

    def _handle_inputs(self):
        edits = inputs.get_instance().all_pressed_ascii_keys()
        allowed_chars = "ABCDEFGHIJKLMNOPQRSTUVXYZabcdefghijklmnopqrstuvwxyz1234567890_./"

        text = self.text
        cursor_pos = self.cursor_pos

        jump_cursor = inputs.get_instance().was_pressed_two_way(pygame.K_HOME, pygame.K_END)
        if jump_cursor < 0:
            cursor_pos = 0
        elif jump_cursor > 0:
            cursor_pos = len(text)

        move_cursor = 0
        if inputs.get_instance().was_pressed_or_held_and_repeated(pygame.K_LEFT) and not inputs.get_instance().is_held(pygame.K_RIGHT):
            move_cursor = -1
        if inputs.get_instance().was_pressed_or_held_and_repeated(pygame.K_RIGHT) and not inputs.get_instance().is_held(pygame.K_LEFT):
            move_cursor = 1
        if move_cursor != 0:
            cursor_pos = util.bound(cursor_pos + move_cursor, 0, len(text))

        if inputs.get_instance().was_pressed_or_held_and_repeated(pygame.K_DELETE):
            text, cursor_pos = util.apply_ascii_edits_to_text(text, ["~delete~"], cursor_pos=cursor_pos)

        if not inputs.get_instance().was_pressed(pygame.K_BACKSPACE) and inputs.get_instance().was_pressed_or_held_and_repeated(pygame.K_BACKSPACE):
            # backspace is an ascii character, so if it was pressed this frame it'll be in edits
            text, cursor_pos = util.apply_ascii_edits_to_text(text, ["\b"], cursor_pos=cursor_pos)

        # TODO can't hold regular keys to make them repeat

        if len(edits) > 0:
            text, cursor_pos = util.apply_ascii_edits_to_text(text, edits, cursor_pos=cursor_pos,
                                                              max_len=self.char_limit, allowlist=allowed_chars)
        self.text = text
        self.cursor_pos = cursor_pos

    def _update_sprites(self):
        if self.text_sprite is None:
            self.text_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, self.get_text_for_display(),
                                                  font_lookup=self.font)
        abs_xy = self.get_xy(absolute=True)
        text_xy = abs_xy
        if self.has_outline():
            text_xy = (text_xy[0] + self.outline_inset, text_xy[1] + self.outline_inset)
        self.text_sprite.update(new_x=text_xy[0], new_y=text_xy[1], new_text=self.get_text_for_display(),
                                new_scale=self.scale, new_color=self.color)
        if self.has_outline():
            abs_size = self.get_size()
            outline_box = [abs_xy[0], abs_xy[1], abs_size[0], abs_size[1]]
            if self.bg_sprite is None:
                self.bg_sprite = sprites.BorderBoxSprite(spriteref.UI_BG_LAYER, outline_box,
                                                         color=self.outline_color,
                                                         all_borders=spriteref.overworld_sheet().border_thin)
            self.bg_sprite.update(new_rect=outline_box)

    def update(self):
        self._handle_inputs()
        self._update_sprites()

    def all_sprites(self):
        if self.text_sprite is not None:
            for spr in self.text_sprite.all_sprites():
                yield spr
        if self.bg_sprite is not None:
            for spr in self.bg_sprite.all_sprites():
                yield spr
