import random
from collections import deque

from config import config
from cores.musicbot.songInfo import Song


class Playlist:
    """Stores the YouTube links of songs to be played and already played and offers basic operation on the queues"""

    def __init__(self):
        # Stores the links of the songs in queue and the ones already played
        self.play_deque = deque()
        self.play_history = deque()

        # A separate history that remembers the names of the tracks that were played
        self.track_name_history = deque()

        self.loop = False

    def __len__(self):
        return len(self.play_deque)

    def add_name(self, track_name: str):
        self.track_name_history.append(track_name)
        if len(self.track_name_history) > config.MAX_TRACKNAME_HISTORY_LENGTH:
            self.track_name_history.popleft()

    def add(self, track: Song):
        self.play_deque.append(track)

    def next(self, song_played: Song) -> Song or None:
        if self.loop:
            self.play_deque.appendleft(self.play_history[-1])

        if len(self.play_deque) == 0:
            return None

        if song_played != "Dummy":
            if len(self.play_history) > config.MAX_HISTORY_LENGTH:
                self.play_history.popleft()

        return self.play_deque[0]

    def prev(self, current_song: Song):
        if current_song is None:
            self.play_deque.appendleft(self.play_history[-1])
            return self.play_deque[0]

        ind = self.play_history.index(current_song)
        self.play_deque.appendleft(self.play_history[ind - 1])
        if current_song is not None:
            self.play_deque.insert(1, current_song)

    def shuffle(self):
        random.shuffle(self.play_deque)

    def move(self, old_index: int, new_index: int):
        temp = self.play_deque[old_index]
        del self.play_deque[old_index]
        self.play_deque.insert(new_index, temp)

    def empty(self):
        self.play_deque.clear()
        self.play_history.clear()
