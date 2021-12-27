import os
import platform
import pathlib
import datetime
import tempfile
import shutil
import stat
import struct

NAME_OF_GAME = "RESYNC"
NAME_OF_GAME_SIMPLE = "resync"

_WINDOWS = "Windows"
_LINUX = "Linux"
_MAC = "Darwin"


ICON_PATH_KEY = "~ICON_PATH~"


SPEC_CONTENTS = f"""
# -*- mode: python -*-
# WARNING: This file is auto-generated (see make_exe.py)

block_cipher = None

a = Analysis(['entry_point.py'],
             pathex=[''],
             binaries=[],
             datas=[('assets', 'assets'), ('overworlds', 'overworlds')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
             
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='{NAME_OF_GAME}',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True,
          icon='{ICON_PATH_KEY}')
          
app = BUNDLE(exe,
         name='{NAME_OF_GAME}.app',
         icon='{ICON_PATH_KEY}',
         bundle_identifier=None)
"""


def _ask_yes_or_no_question(question):
    print("")  # newline to make it a little less claustrophobic
    answer = None
    while answer is None:
        txt = input("  " + question + " (y/n): ")
        if txt == "y" or txt == "Y":
            answer = True
        elif txt == "n" or txt == "N":
            answer = False
    print("")
    return answer


def _calc_bit_count_str():
    return "{}bit".format(struct.calcsize("P") * 8)


def _get_icon_path(os_version_str):
    if os_version_str == _MAC:
        return str(pathlib.Path('assets/icons/icon.icns'))
    else:
        return str(pathlib.Path('assets/icons/icon.ico'))


def do_it():
    os_system_str = platform.system()
    if os_system_str not in (_WINDOWS, _LINUX, _MAC):
        raise ValueError("Unrecognized operating system: {}".format(os_system_str))

    if os_system_str == _MAC:
        pretty_os_str = "Mac"  # darwin is weird
    else:
        pretty_os_str = os_system_str

    os_bit_count_str = _calc_bit_count_str()

    spec_filename = pathlib.Path("output.spec")
    print("INFO: creating spec file {}".format(spec_filename))

    icon_path = _get_icon_path(os_system_str)

    with open(spec_filename, "w") as f:
        f.write(SPEC_CONTENTS.replace(ICON_PATH_KEY, icon_path))
    dist_dir = pathlib.Path("dist/{}_{}_{}".format(
        NAME_OF_GAME_SIMPLE,
        pretty_os_str.lower(),
        os_bit_count_str.lower()))

    if os.path.exists(str(dist_dir)):
        ans = _ask_yes_or_no_question("Overwrite {}?".format(dist_dir))
        if ans:
            print("INFO: deleting pre-existing build {}".format(dist_dir))
            shutil.rmtree(str(dist_dir), ignore_errors=True)
        else:
            print("INFO: user opted to not overwrite pre-existing build, exiting")
            return

    dist_dir_subdir = pathlib.Path("{}/{}".format(dist_dir, NAME_OF_GAME_SIMPLE))

    with tempfile.TemporaryDirectory() as temp_dir:
        print("INFO: created temp directory: {}".format(temp_dir))
        print("INFO: launching pyinstaller...\n")

        # note that this call blocks until the process is finished
        os.system("pyinstaller {} --distpath {} --workpath {}".format(
            spec_filename, dist_dir_subdir, temp_dir))

        print("\nINFO: cleaning up {}".format(temp_dir))

    print("INFO: cleaning up {}".format(spec_filename))
    if os.path.exists(str(spec_filename)):
        os.remove(str(spec_filename))

    if os_system_str == _LINUX:
        print("INFO: chmod'ing execution permissions to all users (linux)")
        exe_path = pathlib.Path("{}/{}".format(dist_dir_subdir, NAME_OF_GAME_SIMPLE))
        if not os.path.exists(str(exe_path)):
            raise ValueError("couldn't find exe to apply exec permissions: {}".format(exe_path))
        else:
            st = os.stat(str(exe_path))
            os.chmod(str(exe_path), st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print("\nINFO: make_exe.py has finished")


if __name__ == "__main__":
    do_it()




