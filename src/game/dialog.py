import src.game.ui as ui
import src.game.const as const
import src.game.spriteref as spriteref
import src.engine.scenes as scenes
import src.engine.sprites as sprites
import src.engine.spritesheets as spritesheets
import src.engine.renderengine as renderengine
import src.game.colors as colors
import src.engine.inputs as inputs
import src.utils.util as util
import src.game.globalstate as gs
import configs
import src.game.playertypes as playertypes


_ALL_META_SPEAKER_IDS = []
_ALL_NON_META_SPEAKER_IDS = []


def _speaker_id(val, meta=False):
    if meta:
        _ALL_META_SPEAKER_IDS.append(val)
    else:
        _ALL_NON_META_SPEAKER_IDS.append(val)
    return val


class Speaker:
    A = _speaker_id(const.PLAYER_FAST)
    B = _speaker_id(const.PLAYER_SMALL)
    C = _speaker_id(const.PLAYER_HEAVY)
    D = _speaker_id(const.PLAYER_FLYING)

    NONE = _speaker_id("none")
    UNKNOWN = _speaker_id("unknown")

    PLAYER = _speaker_id("player_type", meta=True)  # the type of the active player
    OTHER = _speaker_id("speaker_type", meta=True)  # the type of the thing that was interacted with

    @staticmethod
    def resolve(obj):
        if isinstance(obj, playertypes.PlayerType):
            obj = obj.get_id()

        from src.game.entities import InfoEntityType
        if isinstance(obj, InfoEntityType):
            obj = obj.get_id()

        if isinstance(obj, str):
            for s_id in _ALL_NON_META_SPEAKER_IDS:
                if s_id == obj:
                    return s_id


class DialogFragment:

    def __init__(self, text, speaker=None, id_resolver={}):
        self.speaker_id = speaker
        self.id_resolver = id_resolver
        self.text = text
        self.next_options = []  # (answer, DialogFragment)

    def set_next(self, dialog_frag) -> 'DialogFragment':
        self.next_options = [("...", dialog_frag)]
        return self

    def add_option(self, response, dialog_frag) -> 'DialogFragment':
        self.next_options.append((response, dialog_frag))
        return self

    def get_next(self, answer):
        for item in self.next_options:
            if item[0] == answer:
                return item[1]
        return None

    def get_next_by_idx(self, idx):
        if 0 <= idx < len(self.next_options):
            return self.next_options[idx][1]
        else:
            return None

    def get_speaker_sprites(self):
        speaker_id = self.speaker_id
        if speaker_id in self.id_resolver:
            speaker_id = self.id_resolver[speaker_id]

        if speaker_id is None:
            return []
        else:
            return spriteref.object_sheet().get_speaker_portrait_sprites(speaker_id)


def link(*frags):
    first = None
    last = None
    for f in frags:
        if first is None:
            first = f
        if last is not None:
            last.set_next(f)
        last = f
    return first


class DialogElement(ui.UiElement):

    def __init__(self, dialog: DialogFragment):
        super().__init__()

        self.current_dialog = dialog

        self.current_dialog_ticks = 0
        self.selected_option = 0

        self.bg_opacity = 0.85
        self.bg_sprite = None

        self.speaker_sprite = None
        self.text_sprite = None

        self.inset = 4

    def _get_visible_text(self):
        # TODO scrolling?
        return self.current_dialog.text

    def is_scrolling(self):
        return False

    def get_font(self):
        return spritesheets.get_instance().get_sheet(spritesheets.DefaultFont.SHEET_ID)

    def update_sprites(self):
        xy = self.get_xy(absolute=True)
        screen_size = renderengine.get_instance().get_game_size()
        size = self.get_size()

        if self.bg_sprite is None:
            self.bg_sprite = sprites.ImageSprite.new_sprite(spriteref.UI_BG_LAYER, depth=10)
        bg_model = spritesheets.get_instance().get_sheet(spritesheets.WhiteSquare.SHEET_ID).get_sprite(opacity=self.bg_opacity)
        self.bg_sprite = self.bg_sprite.update(new_model=bg_model, new_x=xy[0], new_y=xy[1],
                                               new_ratio=(size[0] / bg_model.width(), size[1] / bg_model.height()),
                                               new_color=colors.PERFECT_BLACK)

        if self.speaker_sprite is None:
            self.speaker_sprite = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER)
        all_sprites = self.current_dialog.get_speaker_sprites()
        if len(all_sprites) > 0:
            speaker_img = all_sprites[gs.get_instance().anim_tick() // 8 % len(all_sprites)]
        else:
            speaker_img = spritesheets.get_white_square_img(0)

        speaker_sc = 3
        speaker_size = speaker_img.size(scale=speaker_sc)
        self.speaker_sprite = self.speaker_sprite.update(new_model=speaker_img, new_x=xy[0] + self.inset,
                                                         new_y=screen_size[1] - speaker_size[1],
                                                         new_scale=speaker_sc)

        text_xy = (xy[0] + speaker_size[0] + 2 * self.inset, xy[1] + self.inset)
        text_size = ((xy[0] + size[0]) - text_xy[0] - self.inset, size[1] - 2 * self.inset)
        visible_text = "\n".join(sprites.TextSprite.wrap_text_to_fit(self._get_visible_text(), text_size[0],
                                                                     scale=1, font_lookup=self.get_font()))
        if self.text_sprite is None:
            self.text_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, "blah", font_lookup=self.get_font())
        self.text_sprite.update(new_x=text_xy[0], new_y=text_xy[1], new_text=visible_text)

    def update(self):
        if inputs.get_instance().was_pressed((const.MENU_ACCEPT, const.JUMP, const.MENU_CANCEL)):
            if self.is_scrolling():
                if self.current_dialog_ticks > 5:
                    self.current_dialog_ticks = 10000  # scroll to end
            else:
                self.go_to_next_dialog()

    def go_to_next_dialog(self):
        next = self.current_dialog.get_next_by_idx(self.selected_option)  # could be None
        self.selected_option = 0
        self.current_dialog_ticks = 0
        self.current_dialog = next

    def get_xy(self, absolute=False):
        size = self.get_size()
        screen_size = renderengine.get_instance().get_game_size()
        return [0, screen_size[1] - size[1]]

    def get_size(self):
        screen_size = renderengine.get_instance().get_game_size()
        return [screen_size[0], screen_size[1] // 3]

    def all_sprites(self):
        yield self.bg_sprite
        yield self.speaker_sprite
        yield self.text_sprite


class DialogManager:

    def __init__(self):
        self._ui: DialogElement = None

    def set_dialog(self, dialog_frag: DialogFragment):
        print("INFO: starting dialog {}".format(dialog_frag))
        if dialog_frag is not None:
            self._ui = DialogElement(dialog_frag)
        else:
            self._ui = None

    def update_sprites(self):
        if self._ui is not None:
            self._ui.update_sprites()

    def update(self):
        if self._ui is not None:
            self._ui.update_self_and_kids()

        if self._ui is not None and self._ui.current_dialog is None:
            self._ui = None

    def get_ui(self) -> DialogElement:
        return self._ui

    def all_sprites(self):
        if self._ui is not None:
            for spr in self._ui.all_sprites():
                yield spr
        else:
            return []

    def is_active(self):
        return self._ui is not None


class DialogScene(scenes.Scene):
    """The parent class for scenes that support dialog."""

    def __init__(self):
        super().__init__()
        self.dialog_manager: DialogManager = DialogManager()

    def update_sprites(self):
        if self.dialog_manager.is_active():
            self.dialog_manager.update_sprites()

    def start_dialog(self, dialog_frag: DialogFragment):
        self.dialog_manager.set_dialog(dialog_frag)

    def is_dialog_active(self):
        return self.dialog_manager.is_active()

    def on_dialog_end(self):
        """Called when dialog ends."""
        pass

    def update(self):
        if self.is_dialog_active():
            self.dialog_manager.update()
            if not self.is_dialog_active():
                self.on_dialog_end()

        if not self.is_dialog_active():
            # only update the underlying scene if dialog is inactive.
            self.update_impl()

        if configs.is_dev:
            import pygame
            if inputs.get_instance().was_pressed(pygame.K_F6):
                self.dialog_manager.set_dialog(get_test_dialog())  # XXX no id lookups here

    def update_impl(self):
        raise NotImplementedError()

    def all_sprites(self):
        if self.is_dialog_active():
            for spr in self.dialog_manager.all_sprites():
                yield spr


def get_test_dialog(lookup={}):
    return link(DialogFragment("Here's some test dialog.", speaker=Speaker.OTHER, id_resolver=lookup),
                DialogFragment("And here's a test reply.", speaker=Speaker.PLAYER, id_resolver=lookup))

def get_multi_char_test_dialog():
    return link(DialogFragment("Here's some test text.", speaker=Speaker.A),
                DialogFragment("And here's a test reply.", speaker=Speaker.B),
                DialogFragment("Dialog adds a lot of life to a game, don't you think? I'm just going to add a bit more "
                               "text here to extend the length to make it wrap. The Glitch Mob is a great band don't you think?", speaker=Speaker.C),
                DialogFragment("Life?", speaker=Speaker.D),
                DialogFragment("Err... life-mimicking CPU cycles, I mean.", speaker=Speaker.C))


def get_dialog(dialog_id, player_type, other_type):
    lookup = {
        Speaker.PLAYER: Speaker.resolve(player_type),
        Speaker.OTHER: Speaker.resolve(other_type)
    }

    return get_test_dialog(lookup=lookup)
