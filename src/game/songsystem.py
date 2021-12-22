
import pygame

import os
import traceback
import src.game.globalstate as gs

import src.utils.util as util


_INSTANCE = None


def get_instance() -> 'LoopFader':
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = LoopFader()
    return _INSTANCE


class MultiChannelSong:

    def __init__(self, song_id, filenames, adjusted_volume=1):
        self.song_id = song_id
        self.sounds = [pygame.mixer.Sound(f) for f in filenames]

        self._master_volume = 1
        self._adjusted_volume = adjusted_volume  # some songs are intrinsically louder than others and need some EQ
        self._volumes = [1 for _ in range(0, len(self.sounds))]

        self._playing = False
        lengths = set()

        # This system won't work at all if the lengths aren't **exactly** the same.
        for s in self.sounds:
            lengths.add(s.get_length())
        if len(lengths) > 1:
            raise ValueError("song's channels have different lengths: {}".format(lengths))

    def __repr__(self):
        return f"{type(self).__name__}({self.song_id}, {self.get_volumes()})"

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
        return self._volumes  # would probably be better to return a copy but ggf

    def set_volumes(self, volumes, update_now=True):
        if volumes != self._volumes:
            self._volumes = volumes
            if update_now:
                self.update()
            return True
        else:
            return False

    def set_master_volume(self, v, update_now=True):
        if v != self._master_volume:
            self._master_volume = v
            if update_now:
                self.update()
            return True
        else:
            return False

    def update(self):
        volume_from_prefs = gs.get_instance().settings().music_volume()
        for i, v in enumerate(self._volumes):
            if i < len(self.sounds):
                self.sounds[i].set_volume(v * self._master_volume * self._adjusted_volume * volume_from_prefs)
        if len(self._volumes) < len(self.sounds):
            for i in range(len(self._volumes), len(self.sounds)):
                self.sounds[i].set_volume(0)

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
RADIATION = "radiation"
SPACE = "space"

SILENCE = "~silence~"                    # literally just silent
CONTINUE_CURRENT = "~continue_current~"  # a no-op when passed to set_song

MAIN_MENU_SONG = SPACE, [1]  # MACHINATIONS, [0.25, 0.5, 0, 0]
INSTRUCTION_MENU_SONG = MACHINATIONS, [0.1, 0.25, 0, 0]


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


def num_instruments(song_id) -> int:
    song = _get_song_lazily(song_id)
    return len(song.sounds)


class LoopFader:

    def __init__(self):
        self.song_queue = []  # list of (song, volume_levels, time) tuples
        self.last_update_time = 0

        self._master_volume = 1
        self._target_master_volume = self._master_volume
        self._master_volume_rate_of_change = 1  # per sec

        self._dirty = False  # if true, means a volume refresh is needed

    def current_song(self) -> MultiChannelSong:
        if len(self.song_queue) > 0:
            return self.song_queue[0][0]
        else:
            return None

    def set_master_volume(self, volume, rate_of_change=0.1):
        self._target_master_volume = volume
        self._master_volume_rate_of_change = rate_of_change

    def mark_dirty(self):
        self._dirty = True

    def _sort_and_refresh_queue(self, cur_time=None):
        if cur_time is None:
            cur_time = pygame.time.get_ticks()
        self.song_queue.sort(key=lambda info: info[2])
        while len(self.song_queue) >= 2 and self.song_queue[1][2] < cur_time:
            to_remove = self.song_queue.pop(0)
            if to_remove[0] != self.song_queue[0][0]:
                to_remove[0].stop()  # just in case

    def set_song(self, song_id: str, volume_levels=1, fadeout=0, fadein=0):
        """
        :param song_id: id of the next song to play, or (id, volume_levels) tuple
        :param volume_levels: sequence of volume levels, or a single number (to set all channels to the same volume).
        :param fadeout: how long (in seconds) to fade-out the current song (ignored if next song == current song).
        :param fadein: how long (in seconds) to fade-in the new song.
        """
        cur_time = pygame.time.get_ticks()

        # sometimes it's convenient to pass in the id + volume levels as a single item
        if isinstance(song_id, tuple):
            song_id, volume_levels = song_id

        if song_id == CONTINUE_CURRENT:
            return  # no-op
        elif song_id is None:
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
            cur_volumes = cur_song_state[0].get_volumes()

            # fade out what's currently playing
            self.song_queue.clear()
            self.song_queue.append((cur_song_state[0], cur_volumes, cur_time))
            self.song_queue.append((cur_song_state[0], [0] * len(cur_volumes), cur_time + int(fadeout * 1000)))

            # fade in the next song if necessary
            if fadein <= 0 or song == SILENCE:
                self.song_queue.append((song, volume_levels, cur_time + int(fadeout * 1000)))
            else:
                self.song_queue.append((song, [0] * len(song.sounds), cur_time + int(fadeout * 1000)))
                self.song_queue.append((song, volume_levels, cur_time + int((fadein + fadeout) * 1000)))

        self._sort_and_refresh_queue(cur_time)

        self.last_update_time = cur_time

    def update(self):
        cur_time = pygame.time.get_ticks()
        ellapsed_time_ms = cur_time - self.last_update_time

        self._sort_and_refresh_queue(cur_time)

        cur_song_info = self.song_queue[0] if len(self.song_queue) >= 1 else None
        if cur_song_info is None:
            return
        cur_song = cur_song_info[0]

        do_start = False
        needs_update = self._dirty

        next_song_info = self.song_queue[1] if len(self.song_queue) >= 2 else None
        if next_song_info is None or cur_time < cur_song_info[2] or cur_song != next_song_info[0]:
            # no fading is occurring, so just ensure the current song is playing
            if not cur_song.is_playing():
                needs_update |= cur_song.set_volumes(cur_song_info[1], update_now=False)
                do_start = True
        else:
            # fading between two volume levels in the same song
            fade_duration = next_song_info[2] - cur_song_info[2]
            if fade_duration == 0:
                prog = 1
            else:
                prog = (cur_time - cur_song_info[2]) / fade_duration
            cur_volume_levels = util.linear_interp(cur_song_info[1], next_song_info[1], prog)

            needs_update |= cur_song.set_volumes(cur_volume_levels, update_now=False)
            if not cur_song.is_playing():
                do_start = True

        # handle master volume fades
        if self._master_volume != self._target_master_volume:
            if self._master_volume_rate_of_change == 0:
                self._master_volume = self._target_master_volume
            else:
                change = self._master_volume_rate_of_change * ellapsed_time_ms * 1000.0
                if self._master_volume < self._target_master_volume:
                    self._master_volume = min(self._master_volume + change, self._target_master_volume)
                else:
                    self._master_volume = max(self._master_volume - change, self._target_master_volume)
            needs_update |= cur_song.set_master_volume(self._master_volume, update_now=False)

        if needs_update:
            cur_song.update()
        if do_start:
            cur_song.start()

        self._dirty = False


