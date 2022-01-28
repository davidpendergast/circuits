import re


_BASE_PATH = "assets/sounds/"


def _path_to(relpath, l, filename):
    res = f"assets/sounds/{relpath}/{filename}"
    l.append(res)
    return res


def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub('(.)([a-z])([0-9]+)', r'\1\2_\3', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


class ModernUI:

    _p = "Cyberleaf-ModernUISFX/Sounds"
    _a = []  # all sounds

    camera_snapshot                = _path_to(_p, _a, "CameraSnapshot.wav")
    click_and_slide                = _path_to(_p, _a, "ClickAndSlide.wav")
    clicky_button_1a               = _path_to(_p, _a, "ClickyButton1a.wav")
    clicky_button_1b               = _path_to(_p, _a, "ClickyButton1b.wav")
    clicky_button_2                = _path_to(_p, _a, "ClickyButton2.wav")
    clicky_button_3a               = _path_to(_p, _a, "ClickyButton3a.wav")
    clicky_button_3b               = _path_to(_p, _a, "ClickyButton3b.wav")
    clicky_button_4                = _path_to(_p, _a, "ClickyButton4.wav")
    clicky_button_5a               = _path_to(_p, _a, "ClickyButton5a.wav")
    clicky_button_5b               = _path_to(_p, _a, "ClickyButton5b.wav")
    clicky_button_6                = _path_to(_p, _a, "ClickyButton6.wav")
    clicky_button_7                = _path_to(_p, _a, "ClickyButton7.wav")
    clicky_button_8                = _path_to(_p, _a, "ClickyButton8.wav")
    clicky_button_9a               = _path_to(_p, _a, "ClickyButton9a.wav")
    clicky_button_9b               = _path_to(_p, _a, "ClickyButton9b.wav")
    clicky_button_10a              = _path_to(_p, _a, "ClickyButton10a.wav")
    clicky_button_10b              = _path_to(_p, _a, "ClickyButton10b.wav")
    close_or_disable_1             = _path_to(_p, _a, "CloseOrDisable1.wav")
    close_or_disable_2             = _path_to(_p, _a, "CloseOrDisable2.wav")
    close_or_disable_3             = _path_to(_p, _a, "CloseOrDisable3.wav")
    close_or_disable_4             = _path_to(_p, _a, "CloseOrDisable4.wav")
    close_or_disable_5             = _path_to(_p, _a, "CloseOrDisable5.wav")
    error_1                        = _path_to(_p, _a, "Error1.wav")
    error_2                        = _path_to(_p, _a, "Error2.wav")
    error_3                        = _path_to(_p, _a, "Error3.wav")
    error_4                        = _path_to(_p, _a, "Error4.wav")
    error_5                        = _path_to(_p, _a, "Error5.wav")
    generic_button_1               = _path_to(_p, _a, "GenericButton1.wav")
    generic_button_2               = _path_to(_p, _a, "GenericButton2.wav")
    generic_button_3               = _path_to(_p, _a, "GenericButton3.wav")
    generic_button_4               = _path_to(_p, _a, "GenericButton4.wav")
    generic_button_5               = _path_to(_p, _a, "GenericButton5.wav")
    generic_button_6               = _path_to(_p, _a, "GenericButton6.wav")
    generic_button_7               = _path_to(_p, _a, "GenericButton7.wav")
    generic_button_8               = _path_to(_p, _a, "GenericButton8.wav")
    generic_button_9               = _path_to(_p, _a, "GenericButton9.wav")
    generic_button_10              = _path_to(_p, _a, "GenericButton10.wav")
    generic_button_11              = _path_to(_p, _a, "GenericButton11.wav")
    generic_button_12              = _path_to(_p, _a, "GenericButton12.wav")
    generic_button_13              = _path_to(_p, _a, "GenericButton13.wav")
    generic_button_14              = _path_to(_p, _a, "GenericButton14.wav")
    generic_button_15              = _path_to(_p, _a, "GenericButton15.wav")
    generic_notification_1         = _path_to(_p, _a, "GenericNotification1.wav")
    generic_notification_2         = _path_to(_p, _a, "GenericNotification2.wav")
    generic_notification_3         = _path_to(_p, _a, "GenericNotification3.wav")
    generic_notification_4         = _path_to(_p, _a, "GenericNotification4.wav")
    generic_notification_5         = _path_to(_p, _a, "GenericNotification5.wav")
    generic_notification_6         = _path_to(_p, _a, "GenericNotification6.wav")
    generic_notification_7         = _path_to(_p, _a, "GenericNotification7.wav")
    generic_notification_8         = _path_to(_p, _a, "GenericNotification8.wav")
    generic_notification_9         = _path_to(_p, _a, "GenericNotification9.wav")
    generic_notification_10a       = _path_to(_p, _a, "GenericNotification10a.wav")
    generic_notification_10b       = _path_to(_p, _a, "GenericNotification10b.wav")
    generic_notification_11        = _path_to(_p, _a, "GenericNotification11.wav")
    handle_drag_tick               = _path_to(_p, _a, "HandleDragTick.wav")
    little_noise                   = _path_to(_p, _a, "LittleNoise.wav")
    little_swoosh_1a               = _path_to(_p, _a, "LittleSwoosh1a.wav")
    little_swoosh_1b               = _path_to(_p, _a, "LittleSwoosh1b.wav")
    little_swoosh_2a               = _path_to(_p, _a, "LittleSwoosh2a.wav")
    little_swoosh_2b               = _path_to(_p, _a, "LittleSwoosh2b.wav")
    little_swoosh_3                = _path_to(_p, _a, "LittleSwoosh3.wav")
    little_swoosh_4                = _path_to(_p, _a, "LittleSwoosh4.wav")
    little_swoosh_5                = _path_to(_p, _a, "LittleSwoosh5.wav")
    maximize_1                     = _path_to(_p, _a, "Maximize1.wav")
    maximize_2                     = _path_to(_p, _a, "Maximize2.wav")
    maximize_3                     = _path_to(_p, _a, "Maximize3.wav")
    maximize_4                     = _path_to(_p, _a, "Maximize4.wav")
    minimize_1                     = _path_to(_p, _a, "Minimize1.wav")
    minimize_2                     = _path_to(_p, _a, "Minimize2.wav")
    minimize_3                     = _path_to(_p, _a, "Minimize3.wav")
    minimize_4                     = _path_to(_p, _a, "Minimize4.wav")
    open_or_enable_1               = _path_to(_p, _a, "OpenOrEnable1.wav")
    open_or_enable_2               = _path_to(_p, _a, "OpenOrEnable2.wav")
    open_or_enable_3               = _path_to(_p, _a, "OpenOrEnable3.wav")
    open_or_enable_4a              = _path_to(_p, _a, "OpenOrEnable4a.wav")
    open_or_enable_4b              = _path_to(_p, _a, "OpenOrEnable4b.wav")
    open_or_enable_5               = _path_to(_p, _a, "OpenOrEnable5.wav")
    popup_1                        = _path_to(_p, _a, "Popup1.wav")
    popup_2                        = _path_to(_p, _a, "Popup2.wav")
    popup_3                        = _path_to(_p, _a, "Popup3.wav")
    popup_4a                       = _path_to(_p, _a, "Popup4a.wav")
    popup_4b                       = _path_to(_p, _a, "Popup4b.wav")
    sci_fi_notification_1          = _path_to(_p, _a, "SciFiNotification1.wav")
    sci_fi_notification_2          = _path_to(_p, _a, "SciFiNotification2.wav")
    sci_fi_notification_3          = _path_to(_p, _a, "SciFiNotification3.wav")
    snappy_button_1                = _path_to(_p, _a, "SnappyButton1.wav")
    snappy_button_2                = _path_to(_p, _a, "SnappyButton2.wav")
    snappy_button_3                = _path_to(_p, _a, "SnappyButton3.wav")
    snappy_button_4                = _path_to(_p, _a, "SnappyButton4.wav")
    snappy_button_5                = _path_to(_p, _a, "SnappyButton5.wav")
    success_1                      = _path_to(_p, _a, "Success1.wav")
    success_2                      = _path_to(_p, _a, "Success2.wav")
    success_3                      = _path_to(_p, _a, "Success3.wav")
    success_4                      = _path_to(_p, _a, "Success4.wav")
    success_5                      = _path_to(_p, _a, "Success5.wav")
    success_6                      = _path_to(_p, _a, "Success6.wav")
    success_7a                     = _path_to(_p, _a, "Success7a.wav")
    success_7b                     = _path_to(_p, _a, "Success7b.wav")
    success_9                      = _path_to(_p, _a, "Success9.wav")
    success_10                     = _path_to(_p, _a, "Success10.wav")
    success_11                     = _path_to(_p, _a, "Success11.wav")
    success_12a                    = _path_to(_p, _a, "Success12a.wav")
    success_12b                    = _path_to(_p, _a, "Success12b.wav")
    success_13                     = _path_to(_p, _a, "Success13.wav")
    swoosh_slide_1a                = _path_to(_p, _a, "SwooshSlide1a.wav")
    swoosh_slide_1b                = _path_to(_p, _a, "SwooshSlide1b.wav")
    swoosh_slide_2                 = _path_to(_p, _a, "SwooshSlide2.wav")
    swoosh_slide_3                 = _path_to(_p, _a, "SwooshSlide3.wav")
    swoosh_slide_4                 = _path_to(_p, _a, "SwooshSlide4.wav")
    swoosh_slide_5                 = _path_to(_p, _a, "SwooshSlide5.wav")

    @staticmethod
    def all_containing(include_text, exclude_text=()):
        return frozenset([p for p in ModernUI._a if (include_text in p and not any(e in p for e in exclude_text))])

    @staticmethod
    def _assets_to_code():
        """Utility method that gen's the above boilerplate code (not used at runtime).
        """

        file_to_process = "/home/david/Coding/python/circuits/assets/sounds/Cyberleaf-ModernUISFX/manifest.txt"

        with open(file_to_process) as f:
            lines = f.readlines()
            lines = [line.rstrip() for line in lines]

        tabs = 8

        for l in lines:
            refname = camel_to_snake(l.replace(".wav", ""))
            if len(refname) < tabs * 4 - 2:
                refname += (" " * ((tabs * 4 - 2) - len(refname)))
            print(f"{refname} = _path_to(_p, _a, \"{l}\")")


MENU_BLIP = ModernUI.clicky_button_3a
MENU_ACCEPT = ModernUI.clicky_button_3b
MENU_ERROR = ModernUI.error_1
MENU_BACK = ModernUI.clicky_button_10b
MENU_START = ModernUI.open_or_enable_4a
MENU_SLIDE = ModernUI.little_swoosh_3

LEVEL_START = ModernUI.open_or_enable_4b
LEVEL_QUIT = ModernUI.close_or_disable_4
LEVEL_FAILED = ModernUI.error_5
LEVEL_PARTIAL_SUCCESS = ModernUI.success_7a
LEVEL_FULL_SUCCESS = ModernUI.success_7b

BLOCK_BREAK = ModernUI.clicky_button_1b
BLOCK_PRIMED_TO_FALL = ModernUI.clicky_button_2
SWITCH_ACTIVATED = ModernUI.clicky_button_9a   # TODO different sounds for different colored switches?
SWITCH_DEACTIVATED = ModernUI.clicky_button_9b

TELEPORT = ModernUI.success_2
TELEPORT_BLOCKED = ModernUI.close_or_disable_3
TELEPORT_UNBLOCKED = ModernUI.open_or_enable_3

PLAYER_JUMP = ModernUI.generic_button_7
PLAYER_DEATH = ModernUI.all_containing("Error", exclude_text=("5",))
PLAYER_DIALOG = ModernUI.generic_notification_6
DIALOG_EXIT = ModernUI.close_or_disable_1

PLAYER_ALERT = ModernUI.sci_fi_notification_2
PLAYER_PICKUP = ModernUI.clicky_button_3a
PLAYER_PUTDOWN = ModernUI.clicky_button_3b
PLAYER_FLY = ModernUI.generic_button_4
PLAYER_DESYNC = ModernUI.close_or_disable_3
PLAYER_RESYNC = ModernUI.open_or_enable_3


if __name__ == "__main__":
    ModernUI._assets_to_code()
