import asyncio

import discord
import yt_dlp
from discord import (
    Guild,
    PCMVolumeTransformer,
    VoiceClient,
)
from discord.ext.commands import (
    Context,
)

from config import config
from cores.musicbot import (
    linkutils,
    utils,
)
from cores.musicbot.playlist import Playlist
from cores.musicbot.settings import Settings
from cores.musicbot.songInfo import Song


class AudioController(object):
    """ Controls the playback of audio and the sequential playing of the songs.

            Attributes:
                playlist: A Playlist object that stores the history and queue of songs.
                current_song: A Song object that stores details of the current song.
                guild: The guild in which the Audio controller operates.
        """

    def __init__(self, guild: Guild, settings: Settings):
        self.playlist = Playlist()
        self.current_song = None
        self.guild = guild

        self.sett = settings
        self._volume = self.sett.get('default_volume')

        self.timer = utils.Timer(self.timeout_handler)

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value):
        self._volume = value
        voice_client = self.guild.voice_client
        if not isinstance(voice_client, VoiceClient):
            raise Exception("Should be VoiceClient")
        voice_client.source = PCMVolumeTransformer(voice_client.source, float(value) / 100.0)

    def track_history(self):
        history_string = config.INFO_HISTORY_TITLE
        for track_name in self.playlist.track_name_history:
            history_string += "\n" + track_name
        return history_string

    def next_song(self, error: Exception, ctx: Context):
        """Invoked after a song is finished. Plays the next song if there is one."""
        next_song: Song = self.playlist.next(self.current_song)

        self.current_song = None

        if next_song is None:
            return

        coro = self.play_song(next_song, ctx)
        ctx.me.loop.create_task(coro)

    async def play_song(self, song: Song, ctx: Context):
        """Plays a song object"""

        if self.playlist.loop:  # let timer run through if looping
            self.timer.cancel()
            self.timer = utils.Timer(self.timeout_handler)

        if song.info.title is None:
            if song.host == linkutils.Sites.Spotify:
                conversion = utils.search_youtube(await linkutils.convert_spotify(song.info.webpage_url))
                song.info.webpage_url = conversion
            utils.get_song_info(song)

        self.playlist.add_name(song.info.title)
        self.current_song = song

        self.playlist.play_history.append(self.current_song)
        await ctx.send(embed=song.info.format_output(config.SONGINFO_NOW_PLAYING))

        voice_client = self.guild.voice_client
        if not isinstance(voice_client, VoiceClient):
            raise Exception("Should be VoiceClient")
        voice_client.play(
            discord.FFmpegPCMAudio(
                song.base_url,
                before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
            ),
            after=lambda e: self.next_song(e, ctx)
        )

        self.guild.voice_client.source = discord.PCMVolumeTransformer(
            self.guild.voice_client.source
        )
        self.guild.voice_client.source.volume = float(self.volume) / 100.0

        self.playlist.play_deque.popleft()

        for song in list(self.playlist.play_deque)[:config.MAX_SONG_PRELOAD]:
            asyncio.ensure_future(utils.preload(song))

    async def process_song(self, track: str, ctx: Context):
        """Adds the track to the playlist instance and plays it, if it is the first song"""

        host = linkutils.identify_url(track)
        is_playlist = linkutils.identify_playlist(track)
        print(track)
        print(is_playlist)

        if is_playlist != linkutils.PlaylistTypes.Unknown and is_playlist != linkutils.PlaylistTypes.YouTube_Music_Playlist:
            await ctx.send("Processing playlist...")
            await self.process_playlist(is_playlist, track)

            if self.current_song is None:
                await self.play_song(self.playlist.play_deque[0], ctx)
                print(f"Playing {track}")

            return Song(
                linkutils.Origins.Playlist,
                linkutils.Sites.Unknown
            )

        if host == linkutils.Sites.Unknown:
            if linkutils.get_url(track) is not None:
                return None

            track = utils.search_youtube(track)

        if host == linkutils.Sites.YouTube:
            track = track.split("&list=")[0]

        downloader = yt_dlp.YoutubeDL({
            'format': 'bestaudio',
            'title': True,
            "cookiefile": config.COOKIE_PATH
        })

        try:
            r = downloader.extract_info(track, download=False)
        except Exception as e:
            print(str(e))
            return None

        if r.get('thumbnails') is not None:
            thumbnail = r.get('thumbnails')[len(r.get('thumbnails')) - 1]['url']
        else:
            thumbnail = None

        song = Song(
            linkutils.Origins.Default,
            host,
            base_url=r.get('url'),
            uploader=r.get('uploader'),
            title=r.get('title'),
            duration=r.get('duration'),
            webpage_url=r.get('webpage_url'),
            thumbnail=thumbnail
        )

        self.playlist.add(song)
        if self.current_song is None:
            print(f"Playing {track}")
            await self.play_song(song, ctx)

        return song

    async def process_playlist(self, playlist_type: linkutils.PlaylistTypes, url: str):
        if playlist_type == linkutils.PlaylistTypes.YouTube_Playlist:
            options = {
                'format': 'bestaudio/best',
                'extract_flat': True,
                "cookiefile": config.COOKIE_PATH
            }

            with yt_dlp.YoutubeDL(options) as ydl:
                r = ydl.extract_info(url, download=False)

                for entry in r['entries']:
                    link = f"https://www.youtube.com/watch?v={entry['id']}"

                    song = Song(
                        linkutils.Origins.Playlist,
                        linkutils.Sites.YouTube,
                        webpage_url=link
                    )

                    self.playlist.add(song)

        for song in list(self.playlist.play_deque)[:config.MAX_SONG_PRELOAD]:
            asyncio.ensure_future(utils.preload(song))

    async def stop_player(self):
        """Stops the player and removes all songs from the queue"""

        voice_client = self.guild.voice_client
        if not isinstance(voice_client, VoiceClient):
            raise Exception("Should be VoiceClient")
        if not voice_client.is_paused() and not voice_client.is_playing():
            return

        self.playlist.loop = False
        self.playlist.next(self.current_song)
        self.clear_queue()
        voice_client.stop()

    async def prev_song(self, ctx: Context):
        """Loads the last song from the history into the queue and starts it"""

        self.timer.cancel()
        self.timer = utils.Timer(self.timeout_handler)

        if len(self.playlist.play_history) == 0:
            return

        prev_song = self.playlist.prev(self.current_song)

        voice_client = self.guild.voice_client
        if not isinstance(voice_client, VoiceClient):
            raise Exception("Should be VoiceClient")
        if not voice_client.is_playing() and not voice_client.is_paused():
            if prev_song == "Dummy":
                self.playlist.next(self.current_song)
                return None
            await self.play_song(prev_song, ctx)
        else:
            voice_client.stop()

    async def timeout_handler(self):
        voice_client = self.guild.voice_client
        if not isinstance(voice_client, VoiceClient):
            raise Exception("Should be VoiceClient")
        if len(voice_client.channel.voice_states) == 1:
            await self.disconnect()
            return

        sett = self.sett

        if not sett.get('vc_timeout'):
            self.timer = utils.Timer(self.timeout_handler)  # restart timer
            return

        if voice_client.is_playing():
            self.timer = utils.Timer(self.timeout_handler)  # restart timer
            return

        self.timer = utils.Timer(self.timeout_handler)
        await self.disconnect()

    async def is_connected(self):
        if self.guild.voice_client is not None:
            return self.guild.voice_client.channel
        return None

    async def connect(self, ctx: Context):
        if not ctx.author.voice:
            await ctx.send(config.NO_GUILD_MESSAGE)
            return False

        if self.guild.voice_client is None:
            await utils.register_voice_channel(ctx.author.voice.channel)
        else:
            await ctx.send(config.ALREADY_CONNECTED_MESSAGE)
        return True

    async def disconnect(self):
        await self.stop_player()
        await self.guild.voice_client.disconnect(force=True)

    def clear_queue(self):
        self.playlist.play_deque.clear()
