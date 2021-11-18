
import pygame

import os
import traceback

import src.utils.util as util


_INSTANCE = None


def get_instance() -> 'LoopFader':
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = LoopFader()
    return _INSTANCE


class MultiChannelSong:

    def __init__(self, song_id, filenames):
        self.song_id = song_id
        self.sounds = [pygame.mixer.Sound(f) for f in filenames]
        self._playing = False
        lengths = set()

        # This system won't work at all if the lengths aren't **exactly** the same.
        for s in self.sounds:
            lengths.add(s.get_length())
        if len(lengths) > 1:
            raise ValueError("song's channels have different lengths: {}".format(lengths))

    def __eq__(self, other):
        return isinstance(other, MultiChannelSong) and self.song_id == other.song_id

    @staticmethod
    def load_from_disk(song_id, relpath="assets/songs/"):
        base_dir = util.resource_path(os.path.join(relpath, song_id))
        sound_paths = []
        for fname in os.listdir(base_dir):
            if fname.endswith((".mp3", ".wav", ".ogg")):
                sound_paths.append(os.path.join(base_dir, fname))
        sound_paths.sort()
        return MultiChannelSong(song_id, sound_paths)

    def get_volumes(self):
        return [s.get_volume() for s in self.sounds]

    def set_volumes(self, volumes):
        for i, v in enumerate(volumes):
            if i < len(self.sounds):
                self.sounds[i].set_volume(v)

    def is_playing(self):
        return self._playing

    def stop(self):
        print("INFO: stopping song: {}".format(self.song_id))
        for s in self.sounds:
            s.stop()
        self._playing = False

    def start(self):
        print("INFO: starting song: {}".format(self.song_id))
        for s in self.sounds:
            s.play(loops=-1)
        self._playing = True


# Songs
MACHINATIONS = "machinations"
SILENCE = "silence"  # literally just silent


_LOADED_SONGS = {}


def _get_song_lazily(song_id) -> MultiChannelSong:
    if song_id not in _LOADED_SONGS:
        if song_id == SILENCE:
            _LOADED_SONGS[song_id] = MultiChannelSong(song_id, [])
        else:
            try:
                _LOADED_SONGS[song_id] = MultiChannelSong.load_from_disk(song_id)
            except Exception:
                print("ERROR: failed to load multi-track song with ID: {}".format(song_id))
                traceback.print_exc()

                # swap in a silent song
                _LOADED_SONGS[song_id] = MultiChannelSong(song_id, [])

    return _LOADED_SONGS[song_id]


class LoopFader:

    def __init__(self):
        self.song_queue = []  # list of (song, volume_levels, time) tuples

    def current_song(self) -> MultiChannelSong:
        if len(self.song_queue) > 0:
            return self.song_queue[0][0]
        else:
            return None

    def _sort_and_refresh_queue(self, cur_time=None):
        if cur_time is None:
            cur_time = pygame.time.get_ticks()
        self.song_queue.sort(key=lambda info: info[2])
        while len(self.song_queue) >= 2 and self.song_queue[1][2] < cur_time:
            to_remove = self.song_queue.pop(0)
            if to_remove[0] != self.song_queue[0][0]:
                to_remove.stop()  # just in case

    def set_song(self, song_id: str, volume_levels=1, fadeout=0, fadein=0):
        """
        :param song_id: id of the next song to play.
        :param volume_levels: sequence of volume levels, or a single number (to set all channels to the same volume).
        :param fadeout: how long (in seconds) to fade-out the current song (ignored if next song == current song).
        :param fadein: how long (in seconds) to fade-in the new song.
        """
        cur_time = pygame.time.get_ticks()
        if song_id is None:
            song_id = SILENCE

        song = _get_song_lazily(song_id)

        if isinstance(volume_levels, int) or isinstance(volume_levels, float):
            volume_levels = [volume_levels] * len(song.sounds)

        if len(self.song_queue) == 0 or (fadeout <= 0 and self.song_queue[0][0] != song):
            # nuke the existing queue and play the new song
            for s in self.song_queue:
                s[0].stop()
            self.song_queue.clear()
            if fadein <= 0 or song == SILENCE:
                self.song_queue.append((song, volume_levels, cur_time))
            else:
                self.song_queue.append((song, [0] * len(song.sounds), cur_time))
                self.song_queue.append((song, volume_levels, cur_time + int(fadein * 1000)))
        elif self.song_queue[0][0] == song:
            # song isn't changing, just fade volume
            self.song_queue.clear()
            self.song_queue.append((song, song.get_volumes(), cur_time))
            self.song_queue.append((song, volume_levels, cur_time + int(fadein * 1000)))
        else:
            cur_song_state = self.song_queue[0]

            # fade out what's currently playing
            self.song_queue.clear()
            self.song_queue.append((cur_song_state[0], cur_song_state[0].get_volumes(), cur_time))
            self.song_queue.append((cur_song_state[0], [0] * len(song.sounds), cur_time + int(fadeout * 1000)))

            # fade in the next song if necessary
            if fadein <= 0 or song == SILENCE:
                self.song_queue.append((song, volume_levels, cur_time + int(fadeout * 1000)))
            else:
                self.song_queue.append((song, [0] * len(song.sounds), cur_time + int(fadeout * 1000)))
                self.song_queue.append((song, volume_levels, cur_time + int((fadein + fadeout) * 1000)))

        self._sort_and_refresh_queue(cur_time)

    def update(self):
        cur_time = pygame.time.get_ticks()
        self._sort_and_refresh_queue(cur_time)

        cur_song_info = self.song_queue[0] if len(self.song_queue) >= 1 else None
        if cur_song_info is None:
            return
        cur_song = cur_song_info[0]

        next_song_info = self.song_queue[1] if len(self.song_queue) >= 2 else None
        if next_song_info is None or cur_time < cur_song_info[2] or cur_song != next_song_info[0]:
            # no fading is occurring, so just ensure the current song is playing
            if not cur_song.is_playing():
                cur_song.set_volumes(cur_song_info[1])
                cur_song.start()
        else:
            # fading between two volume levels in the same song
            fade_duration = next_song_info[2] - cur_song_info[2]
            if fade_duration == 0:
                prog = 1
            else:
                prog = (cur_time - cur_song_info[2]) / fade_duration
            cur_volume_levels = util.linear_interp(cur_song_info[1], next_song_info[1], prog)

            cur_song.set_volumes(cur_volume_levels)
            if not cur_song.is_playing():
                cur_song.start()


