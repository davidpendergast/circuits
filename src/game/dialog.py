import src.game.ui as ui
import src.game.const as const
import src.game.spriteref as spriteref
import src.engine.scenes as scenes


class Speaker:
    A = const.PLAYER_FAST
    B = const.PLAYER_SMALL
    C = const.PLAYER_HEAVY
    D = const.PLAYER_FLYING


class DialogFragment:

    def __init__(self, text, speaker=None):
        self.speaker_id = speaker
        self.text = text
        self.next_options = []  # (answer, DialogFragment)

    def set_next(self, dialog_frag) -> 'DialogFragment':
        self.next_options = [("...", dialog_frag)]
        return self

    def add_option(self, response, dialog_frag) -> 'DialogFragment':
        self.next_options.append((response, dialog_frag))
        return self

    def get_speaker_sprites(self):
        if self.speaker_id is None:
            return []
        else:
            return spriteref.object_sheet().get_speaker_portrait_sprites(self.speaker_id)


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

    def __init__(self, dialog):
        super().__init__()
        self.current_dialog = dialog

        self.current_dialog_ticks = 0
        self.selected_option = 0

    def update(self):
        pass

    def get_size(self):
        pass


class DialogManager:

    def __init__(self):
        self.active_dialog: DialogFragment = None
        self._ui: DialogElement = None

    def set_dialog(self, dialog_frag: DialogFragment):
        self.active_dialog = dialog_frag

    def update_sprites(self):
        pass

    def update(self):
        pass

    def get_ui(self) -> DialogElement:
        return self._ui

    def all_sprites(self):
        if self._ui is not None:
            for spr in self._ui.all_sprites():
                yield spr
        else:
            return []

    def is_active(self):
        return self.active_dialog is not None


class DialogScene(scenes.Scene):
    """The parent class for scenes that support dialog."""

    def __init__(self):
        super().__init__()
        self.dialog_manager: DialogManager = DialogManager()

    def update_sprites(self):
        if self.dialog_manager.is_active():
            self.update_sprites()

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

    def update_impl(self):
        raise NotImplementedError()

    def all_sprites(self):
        if self.is_dialog_active():
            for spr in self.dialog_manager.all_sprites():
                yield spr


def get_test_dialog():
    return link(DialogFragment("Here's some test text.", speaker=Speaker.A),
                DialogFragment("And here's a test reply.", speaker=Speaker.B),
                DialogFragment("Dialog adds a lot of life to a game, don't you think?", speaker=Speaker.C),
                DialogFragment("Life?", speaker=Speaker.D),
                DialogFragment("Err... life-mimicking CPU cycles, I mean.", speaker=Speaker.C))
