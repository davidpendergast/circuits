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
        self.ticks_alive = 0

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

    def send_click_to_self_and_kids(self, xy, absolute=False, button=1) -> bool:
        """returns: whether anything consumed the click"""
        if absolute:
            xy = util.sub(xy, self.get_xy(absolute=True))

        if not util.rect_contains((0, 0, *self.get_size()), xy):
            return False

        for c in self._children:
            r = c.get_rect()
            if util.rect_contains(r, xy):
                new_xy = util.sub(xy, (r[0], r[1]))
                if c.send_click_to_self_and_kids(new_xy, absolute=False, button=button):
                    return True

        return self.handle_click(xy, button=button)

    def handle_click(self, xy, button=1) -> bool:
        """xy: position of click relative to this component
            returns: whether it consumed the click
        """
        return False

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
        self.ticks_alive += 1

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
            for element in c.depth_first_traverse(include_self=False):
                yield element
            yield c
        if include_self:
            yield self

    def __eq__(self, other):
        if isinstance(other, UiElement):
            return self.uid == other.uid
        else:
            return None

    def __hash__(self):
        return self.uid


# TODO this class is actually pretty complicated to implement right, consider deleting?
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


class OptionsList(UiElement):

    LEFT_ALIGN = 0
    CENTER_ALIGN = 1

    def __init__(self, alignment=LEFT_ALIGN, outlined=False):
        UiElement.__init__(self)
        self.selected_idx = 0
        self.options = []  # list of (rect, str: text, lambda: do_action, lambda: is_enabled)
        self.y_spacing = 4
        self.alignment = alignment
        self.outlined = outlined

        self._sprites = []

        # the option that'll fire when you press esc (AKA back)
        self._esc_option = None

    def add_option(self, text, do_action, is_enabled=lambda: True, esc_option=False):
        self.insert_option(len(self.options), text, do_action, is_enabled=is_enabled, esc_option=esc_option)

    def insert_option(self, idx, text, do_action, is_enabled=lambda: True, esc_option=False):
        opt = ([0, 0, 0, 0], text, do_action, is_enabled)
        self.options.insert(idx, opt)
        if esc_option:
            self._esc_option = opt

    def num_options(self):
        return len(self.options)

    def get_size(self):
        w = 0
        h = 0
        for opt in self.options:
            opt_rect = opt[0]
            w = max(opt_rect[0] + opt_rect[2], w)
            h = max(opt_rect[1] + opt_rect[3], h)
        return (w, h)

    def get_option_idx_at(self, xy, absolute=False):
        rel_xy = xy if not absolute else util.sub(xy, self.get_xy(absolute=True))
        for idx, opt in enumerate(self.options):
            rect = opt[0]
            if util.rect_contains(rect, rel_xy):
                return idx
        return None

    def set_selected_idx(self, idx, silent=False):
        if idx != self.selected_idx:
            self.selected_idx = 0 if len(self.options) == 0 else idx % len(self.options)
            if not silent:
                pass  # TODO play sound

    def update(self):
        if len(self.options) == 0:
            return  # probably not initialized yet

        if self.is_focused():
            if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_UP)):
                self.set_selected_idx((self.selected_idx - 1) % len(self.options))
            if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_DOWN)):
                self.set_selected_idx((self.selected_idx + 1) % len(self.options))

            opt_idx_at_mouse_xy = None
            if inputs.get_instance().mouse_in_window():
                mouse_xy = inputs.get_instance().mouse_pos()
                opt_idx_at_mouse_xy = self.get_option_idx_at(mouse_xy, absolute=True)

            if opt_idx_at_mouse_xy is not None and (inputs.get_instance().mouse_moved() or self.ticks_alive <= 1):
                self.set_selected_idx(opt_idx_at_mouse_xy)

            did_activation = False

            if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_CANCEL)):
                if self._esc_option is not None:
                    did_activation = self._try_to_activate_option(self._esc_option)

            if inputs.get_instance().was_pressed(keybinds.get_instance().get_keys(const.MENU_ACCEPT)):
                if not did_activation and 0 <= self.selected_idx < len(self.options):
                    did_activation = self._try_to_activate_option(self.options[self.selected_idx])

            if inputs.get_instance().mouse_was_pressed(button=1):
                if not did_activation and opt_idx_at_mouse_xy is not None and self.ticks_alive >= 5:
                    did_activation = self._try_to_activate_option(self.options[opt_idx_at_mouse_xy])

        self.update_sprites()

    def update_sprites(self):
        util.extend_or_empty_list_to_length(self._sprites, len(self.options),
                                            creator=lambda: sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, "abc"))
        max_w = 0
        # first build the sprites
        for i in range(0, len(self.options)):
            spr = self._sprites[i]
            rect, text, do_action, is_enabled = self.options[i]
            if not is_enabled():
                new_color = colors.DARK_GRAY
            elif i == self.selected_idx:
                new_color = colors.PERFECT_RED
            else:
                new_color = colors.PERFECT_WHITE
            spr.update(new_text=text, new_color=new_color, new_outline_thickness=1 if self.outlined else 0)
            max_w = max(spr.size()[0], max_w)

        abs_xy = self.get_xy(absolute=True)
        y = 0
        # then figure out the final positions and move the sprites
        for i in range(0, len(self.options)):
            spr = self._sprites[i]
            rect, text, do_action, is_enabled = self.options[i]
            new_rect = [
                0 if self.alignment == OptionsList.LEFT_ALIGN else int(max_w / 2 - spr.size()[0] / 2),
                y,
                spr.size()[0],
                spr.size()[1]
            ]
            self.options[i] = (new_rect, text, do_action, is_enabled)
            spr.update(new_x=abs_xy[0] + new_rect[0], new_y=abs_xy[1] + new_rect[1])

            y += new_rect[3] + self.y_spacing

    def all_sprites(self):
        for spr in self._sprites:
            yield spr

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


class MultiPageOptionsList(ElementGroup):

    def __init__(self, opts_per_page=8, next_text="next", prev_text="prev"):
        ElementGroup.__init__(self)
        self.pages = []

        self.opts_per_page = opts_per_page
        self.next_text = next_text
        self.prev_text = prev_text
        self.cur_page = 0

        self.requested_page = None

    def get_size(self):
        max_w = 0
        max_h = 0
        for opt_list in self.pages:
            max_w = max(max_w, opt_list.get_size()[0])
            max_h = max(max_h, opt_list.get_size()[1])
        return (max_w, max_h)

    def set_current_page(self, idx):
        self.requested_page = idx

    def _refresh_children(self):
        for i in range(0, len(self.pages)):
            if i == self.cur_page:
                if not self.has_child(self.pages[i]):
                    self.add_child(self.pages[i])
                self.pages[i].update_sprites()
            else:
                if self.has_child(self.pages[i]):
                    self.remove_child(self.pages[i])
            self.pages[i].update_sprites()

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

            prev_page.insert_option(prev_page.num_options() - 1, self.next_text, lambda: self.set_current_page(n))
            new_page.add_option(self.prev_text, lambda: self.set_current_page(n - 1))

        self._refresh_children()
        return self.pages[-1]

    def get_current_page(self) -> OptionsList:
        if 0 < self.cur_page < len(self.pages):
            return self.pages[self.cur_page]
        else:
            return None

    def update(self):
        if self.requested_page is not None:
            self.cur_page = self.requested_page
            self.requested_page = None
            self._refresh_children()

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

    ABC_CHARS_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    ABC_CHARS_LOWER = "abcdefghijklmnopqrstuvwxyz"
    ABC_CHARS = ABC_CHARS_UPPER + ABC_CHARS_LOWER
    NUM_CHARS = "0123456789"
    SPECIAL_CHARS = "`~!@#$%^&*()-_=+{}[]|:;\"'<>,.?/\\"

    SIMPLE_CHARS = ABC_CHARS + NUM_CHARS + " _"
    FILEPATH_CHARS = SIMPLE_CHARS + " _-./()"
    ASCII_CHARS = SIMPLE_CHARS + SPECIAL_CHARS

    def __init__(self, text, scale=1, color=None, font=None, char_limit=24, outline_color=None, allowed_chars=ASCII_CHARS):
        UiElement.__init__(self)

        self.text = text
        self.allowed_chars = allowed_chars

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
                                                              max_len=self.char_limit, allowlist=self.allowed_chars)
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
