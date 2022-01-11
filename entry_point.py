import traceback
import datetime
import os
import pathlib

import configs
import src.game.circuits


"""
The main entry point.
"""

game_class = src.game.circuits.CircuitsGame  # <--- change this to your actual game class


def _get_crash_report_file_name():
    now = datetime.datetime.now()
    date_str = now.strftime("--%Y-%m-%d--%H-%M-%S")
    return "crash_report" + date_str + ".txt"


def _dismiss_splash_screen():
    try:
        import pyi_splash  # special pyinstaller thing - import will not resolve in dev
        pyi_splash.close()
    except Exception:
        pass  # this is expected to throw an exception in non-splash launch contexts.


if __name__ == "__main__":
    version_string = configs.version
    name_of_game = configs.name_of_game

    _dismiss_splash_screen()

    try:
        import src.engine.gameloop as gameloop
        loop = gameloop.create_instance(game_class())
        loop.run()

    except Exception as e:
        if configs.do_crash_reporting:
            crash_file_name = _get_crash_report_file_name()
            print("INFO: generating crash file {}".format(crash_file_name))

            directory = os.path.dirname("logs/")
            if not os.path.exists(directory):
                os.makedirs(directory)

            crash_file_path = pathlib.Path("logs/" + crash_file_name)
            with open(crash_file_path, 'w') as f:
                print("o--{}---------------o".format("-" * len(name_of_game)), file=f)
                print("|  {} Crash Report  |".format(name_of_game), file=f)
                print("o--{}---------------o".format("-" * len(name_of_game)), file=f)
                print("\nVersion: {}\n".format(version_string), file=f)

                traceback.print_exc(file=f)

        raise e

