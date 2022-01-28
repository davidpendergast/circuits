import datetime
import os
import traceback

_BONUS_RUNTIME_INFO = {}  # key: str -> value: str


def add_runtime_info(key, value):
    """Call this from anywhere in the program to include some bonus info in the crash report.
        For example, key="OpenGL Version", value="4.6.0 NVIDIA 451.48" would be reported as:
        OpenGL Version: 4.6.0 NVIDIA 451.48
    """
    _BONUS_RUNTIME_INFO[str(key)] = str(value)


def _get_crash_report_file_name():
    now = datetime.datetime.now()
    date_str = now.strftime("--%Y-%m-%d--%H-%M-%S")
    return "crash_report" + date_str + ".txt"


def write_crash_file(name_of_game, version_of_game, dest_dir="logs",
                     include_sys_info=True,
                     include_python_info=True,
                     include_runtime_info=True):
    crash_file_name = _get_crash_report_file_name()
    crash_file_path = os.path.normpath(os.path.join(dest_dir, crash_file_name))
    print("INFO: generating crash file at: {}".format(crash_file_path))

    try:
        directory = os.path.dirname(crash_file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(crash_file_path, 'w') as f:
            print("o--{}---------------o".format("-" * len(name_of_game)), file=f)
            print("|  {} Crash Report  |".format(name_of_game), file=f)
            print("o--{}---------------o".format("-" * len(name_of_game)), file=f)

            print("\nGame Version: {}".format(version_of_game), file=f)

            if include_sys_info:
                try:
                    import platform
                    print(f"\nSystem: {platform.platform()} {platform.machine()}", file=f)
                    print(f"Processor: {platform.processor()}", file=f)
                except Exception:
                    print("ERROR: failed to include system info in crash report")
                    traceback.print_exc()

            if include_python_info:
                try:
                    import sys
                    print(f"\nPython: {sys.version}", file=f)
                    import pygame
                    print(f"Pygame: {pygame.version.ver}", file=f)
                except Exception:
                    print("ERROR: failed to include python info in crash report")
                    traceback.print_exc()

            if include_runtime_info:
                try:
                    if len(_BONUS_RUNTIME_INFO) > 0:
                        print("", file=f)
                        for key in _BONUS_RUNTIME_INFO:
                            print(f"{key}: {_BONUS_RUNTIME_INFO[key]}", file=f)
                except Exception:
                    print("ERROR: failed to include rendering info in crash report")
                    traceback.print_exc()

            # add fatal traceback
            print("", file=f)
            traceback.print_exc(file=f)

    except Exception:
        # awkward situation. probably means the directory is protected.
        # not much we can really do about that, besides writing it to %AppData%
        # instead, where the user would never find it.
        print("ERROR: threw error while writing crash file")
        traceback.print_exc()
