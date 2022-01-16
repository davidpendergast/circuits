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
import src.engine.keybinds as keybinds
import src.engine.sounds as sounds
import src.game.soundref as soundref


_ALL_META_SPEAKER_IDS = set()
_ALL_NON_META_SPEAKER_IDS = set()


class SpeakerType:

    def __init__(self, speaker_id, color=colors.WHITE, sound=soundref.PLAYER_DIALOG, meta=False):
        self.speaker_id = speaker_id
        self.text_color = color
        self.sound = sound
        self.meta = meta

        if meta:
            _ALL_META_SPEAKER_IDS.add(self)
        else:
            _ALL_NON_META_SPEAKER_IDS.add(self)

    def __eq__(self, other):
        if isinstance(other, SpeakerType):
            return self.speaker_id == other.speaker_id
        else:
            return False

    def __hash__(self):
        return hash(self.speaker_id)


class Speaker:
    A = SpeakerType(const.PLAYER_FAST, color=colors.BLUE, sound=playertypes.PlayerTypes.FAST.translate_sound(soundref.PLAYER_DIALOG))
    B = SpeakerType(const.PLAYER_SMALL, color=colors.TAN, sound=playertypes.PlayerTypes.SMALL.translate_sound(soundref.PLAYER_DIALOG))
    C = SpeakerType(const.PLAYER_HEAVY, color=colors.GREEN, sound=playertypes.PlayerTypes.HEAVY.translate_sound(soundref.PLAYER_DIALOG))
    D = SpeakerType(const.PLAYER_FLYING, color=colors.PURPLE, sound=playertypes.PlayerTypes.FLYING.translate_sound(soundref.PLAYER_DIALOG))

    NONE = SpeakerType("none")
    UNKNOWN = SpeakerType("unknown")

    PLAYER = SpeakerType("player_type", meta=True)  # the type of the active player
    OTHER = SpeakerType("speaker_type", meta=True)  # the type of the thing that was interacted with

    @staticmethod
    def resolve(obj) -> SpeakerType:
        if isinstance(obj, playertypes.PlayerType):
            obj = obj.get_id()

        from src.game.entities import InfoEntityType
        if isinstance(obj, InfoEntityType):
            obj = obj.get_id()

        if isinstance(obj, str):
            for s_id in _ALL_NON_META_SPEAKER_IDS:
                if s_id.speaker_id == obj:
                    return s_id

        return Speaker.UNKNOWN


class DialogFragment:

    def __init__(self, text, speaker: SpeakerType = Speaker.NONE, right_side=False, id_resolver={}, color="auto", sound="auto"):
        self.text = text
        self.speaker_type = speaker
        self._color = color
        self._sound = sound
        self.right_side = right_side

        self.id_resolver = id_resolver
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

    def get_resolved_speaker_type(self):
        speaker_type = self.speaker_type
        if speaker_type in self.id_resolver:
            speaker_type = self.id_resolver[speaker_type]
        return speaker_type

    def get_speaker_sprites(self):
        speaker_type = self.get_resolved_speaker_type()
        if speaker_type is None:
            return []
        else:
            return spriteref.object_sheet().get_speaker_portrait_sprites(speaker_type.speaker_id)

    def put_speaker_sprite_on_right_side(self):
        return self.right_side

    def get_text_color(self):
        if self._color == "auto":
            return self.get_resolved_speaker_type().text_color
        else:
            return self._color

    def get_sound(self):
        if self._sound == "auto":
            return self.get_resolved_speaker_type().sound
        else:
            return self._sound


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

        self._has_played_sound = False
        self._was_clicked_this_frame = False

        self.inset = 8

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
        bg_model = spritesheets.get_white_square_img(self.bg_opacity)
        self.bg_sprite = self.bg_sprite.update(new_model=bg_model, new_x=xy[0], new_y=xy[1],
                                               new_ratio=(size[0] / bg_model.width(), size[1] / bg_model.height()),
                                               new_color=colors.PERFECT_BLACK)

        text_rect = [xy[0] + self.inset, xy[1] + self.inset, size[0] - self.inset * 2, size[1] - self.inset * 2]

        all_sprites = self.current_dialog.get_speaker_sprites()
        if len(all_sprites) > 0:
            speaker_img = all_sprites[gs.get_instance().anim_tick() // 8 % len(all_sprites)]
        else:
            speaker_img = None

        if speaker_img is not None:
            speaker_sc = 3
            speaker_size = speaker_img.size(scale=speaker_sc)
            speaker_on_right_side = self.current_dialog.put_speaker_sprite_on_right_side()
            if speaker_on_right_side:
                speaker_x = xy[0] + size[0] - speaker_size[0] - self.inset
                text_rect = [xy[0] + self.inset, xy[1] + self.inset,
                             size[0] - self.inset * 2 - speaker_size[0], size[1] - self.inset * 2]
            else:
                speaker_x = xy[0] + self.inset
                text_rect = [speaker_x + speaker_size[0] + self.inset, xy[1] + self.inset,
                             size[0] - self.inset * 2 - speaker_size[0], size[1] - self.inset * 2]

            if self.speaker_sprite is None:
                self.speaker_sprite = sprites.ImageSprite.new_sprite(spriteref.UI_FG_LAYER)
            self.speaker_sprite = self.speaker_sprite.update(new_model=speaker_img, new_x=speaker_x,
                                                             new_y=screen_size[1] - speaker_size[1],
                                                             new_xflip=speaker_on_right_side,
                                                             new_scale=speaker_sc)
        else:
            self.speaker_sprite = None

        text_color = self.current_dialog.get_text_color()
        visible_text = "\n".join(sprites.TextSprite.wrap_text_to_fit(self._get_visible_text(), text_rect[2],
                                                                     scale=1, font_lookup=self.get_font()))
        if self.text_sprite is None:
            self.text_sprite = sprites.TextSprite(spriteref.UI_FG_LAYER, 0, 0, "blah", font_lookup=self.get_font())
        self.text_sprite.update(new_x=text_rect[0], new_y=text_rect[1], new_text=visible_text, new_color=text_color)

    def update(self):
        if not self._has_played_sound:
            self._has_played_sound = True
            sound_to_play = self.current_dialog.get_sound()
            sounds.play_sound(sound_to_play)

        if self._was_clicked_this_frame or inputs.get_instance().was_pressed((const.ACTION, const.MENU_ACCEPT, const.MENU_CANCEL)):
            self.handle_dialog_interact()

            if self.current_dialog is None:
                sounds.play_sound(soundref.DIALOG_EXIT)

        self._was_clicked_this_frame = False
        self.current_dialog_ticks += 1

    def handle_click(self, xy, button=1) -> bool:
        self._was_clicked_this_frame = True
        return True

    def get_cursor_id_at(self, xy):
        return const.CURSOR_HAND

    def handle_dialog_interact(self):
        if self.current_dialog_ticks > 5:
            if self.is_scrolling():
                self.current_dialog_ticks = 10000  # scroll to end
            else:
                self.go_to_next_dialog()

    def go_to_next_dialog(self):
        self.current_dialog = self.current_dialog.get_next_by_idx(self.selected_option)  # could be None
        self.selected_option = 0
        self.current_dialog_ticks = 0
        self._has_played_sound = False

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
            if inputs.get_instance().mouse_in_window() and inputs.get_instance().mouse_was_pressed(button=1):
                mouse_xy = inputs.get_instance().mouse_pos()
                self._ui.send_click_to_self_and_kids(mouse_xy, absolute=True, button=1)

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

    def get_cursor_id_at(self, xy) -> str:
        if self.is_dialog_active():
            cursor_from_dialog = self.dialog_manager.get_ui().get_cursor_id_from_self_and_kids(xy, absolute=True)
            if cursor_from_dialog is not None:
                return cursor_from_dialog
        return super().get_cursor_id_at(xy)

    def update_impl(self):
        raise NotImplementedError()

    def all_sprites(self):
        if self.is_dialog_active():
            for spr in self.dialog_manager.all_sprites():
                yield spr


def get_test_dialog(lookup={}):
    return link(DialogFragment("Here's some test dialog.", speaker=Speaker.OTHER, id_resolver=lookup, right_side=True),
                DialogFragment("And here's a test reply.", speaker=Speaker.PLAYER, id_resolver=lookup))


def get_multi_char_test_dialog():
    return link(DialogFragment("Here's some test text.", speaker=Speaker.A),
                DialogFragment("And here's a test reply.", speaker=Speaker.B),
                DialogFragment("Dialog adds a lot of life to a game, don't you think? I'm just going to add a bit more "
                               "text here to extend the length to make it wrap. The Glitch Mob is a great band don't you think?", speaker=Speaker.C),
                DialogFragment("Life?", speaker=Speaker.D),
                DialogFragment("Err... life-mimicking CPU cycles, I mean.", speaker=Speaker.C))


_ALL_DIALOG = {}


def init_dialog():
    _ALL_DIALOG["nothing_to_say"] = link(DialogFragment("I have nothing to say.", speaker=Speaker.OTHER))


def get_dialog(dialog_id, player_type, other_type):
    if dialog_id is None or len(dialog_id) == 0:
        return None
    else:
        lookup = {
            Speaker.PLAYER: Speaker.resolve(player_type),
            Speaker.OTHER: Speaker.resolve(other_type)
        }

        if dialog_id == "c_introduction":
            return link(DialogFragment("It's good to 'C' you in one piece, C!", speaker=Speaker.PLAYER, id_resolver=lookup),
                        DialogFragment("Always 'A' pleasure. Will you two 'B' staying a while?", speaker=Speaker.C, right_side=True),
                        DialogFragment("Absolutely. Right up until we the fix the ship and refuel, and then we're blasting out of this hellhole.", speaker=Speaker.PLAYER, id_resolver=lookup),
                        DialogFragment("What is this place? It was dismantling the ship when we powered on. It was like it had a mind of its own.", speaker=Speaker.PLAYER, id_resolver=lookup),
                        DialogFragment("It's some kind of factory. These blocks all around us - that's what it's making.", speaker=Speaker.C, id_resolver=lookup, right_side=True),
                        DialogFragment("That's what happened to my portion of the ship - it pulled it into pieces and reforged it into these blocks, like it was scrap metal.", speaker=Speaker.C, id_resolver=lookup, right_side=True),
                        DialogFragment("Sounds like we might be here a while...", speaker=Speaker.B, id_resolver=lookup),
                        DialogFragment("And what about D? Have you seen them?", speaker=Speaker.PLAYER, id_resolver=lookup),
                        DialogFragment("I haven't seen them, or their section of the ship. I'm sure they're buzzing around somehwere.", speaker=Speaker.C, id_resolver=lookup, right_side=True),
                        DialogFragment("Alright, well. Let's stick together. This place is dangerous.", speaker=Speaker.PLAYER, id_resolver=lookup)
                    )
        else:
            return DialogFragment("I have nothing to say.", speaker=Speaker.OTHER, id_resolver=lookup)


REPLACEMENTS = {
    "{MOVEMENT_KEYS}": lambda: gs.get_instance().get_user_friendly_movement_keys(),
    "{INTERACT_KEYS}": lambda: keybinds.get_instance().get_keys(const.ACTION).get_pretty_names(),
    "{JUMP_KEYS}": lambda: keybinds.get_instance().get_keys(const.JUMP).get_pretty_names()
}


def replace_placeholders(raw_text: str) -> sprites.TextBuilder:
    raw_colors = [None] * len(raw_text)

    while "{" in raw_text and "}" in raw_text:
        start_idx = raw_text.index("{")
        end_idx = raw_text.index("}") + 1
        raw_text, raw_colors = _handle_replacement(start_idx, end_idx, raw_text, raw_colors)

    if len(raw_text) != len(raw_colors):
        raise ValueError(f"bad raw_text={raw_text}, raw_colors={raw_colors} were computed")

    tb = sprites.TextBuilder()
    for idx, c in enumerate(raw_text):
        tb.add(c, raw_colors[idx])

    return tb


def _handle_replacement(start, end, raw_text, raw_colors):
    if end <= start:
        # just slice off the unmatched closing brace I guess
        return raw_text[0: end] + raw_text[end + 1:], raw_colors[0: end] + raw_colors[end + 1:]
    else:
        to_replace = raw_text[start: end]
        if to_replace not in REPLACEMENTS:
            # unrecognized replacement, just remove it
            new_text = "ERROR"
            new_colors = [colors.PERFECT_RED] * len(new_text)
        elif "KEYS" in to_replace:
            mapped_keys = REPLACEMENTS[to_replace]()
            if len(mapped_keys) == 0:
                new_text = " "
                new_colors = [None]
            else:
                tb = sprites.TextBuilder()
                for i, k in enumerate(mapped_keys):
                    if i > 0:
                        if i == len(mapped_keys) - 1:
                            tb.add(", or ")
                        else:
                            tb.add(", ")
                    tb.add(k, color=colors.KEYBIND_COLOR)
                new_text = tb.text
                new_colors = [tb.get_color_at(i) for i in range(len(tb.text))]
        else:
            raise NotImplementedError()

    return raw_text[0: start] + new_text + raw_text[end:], raw_colors[0: start] + new_colors + raw_colors[end:]
