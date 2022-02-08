import asyncio
import concurrent.futures
from typing import (
    Callable,
    List,
    NoReturn,
    Optional,
)

import yt_dlp
from discord import (
    Guild,
    VoiceProtocol,
    VoiceState,
)
from discord.ext.commands import (
    Context,
)
from yarl import URL

from config import config
from cores.musicbot import linkutils
from cores.musicbot.settings import Settings
from cores.musicbot.songInfo import Song


def get_guild(ctx: Context) -> Optional[Guild]:
    """Gets the guild a command belongs to. Useful, if the command was sent via pm."""
    if ctx.guild is not None:
        return ctx.guild
    for guild in ctx.me.guilds:
        for channel in guild.voice_channels:
            if ctx.author in channel.members:
                return guild
    return None


async def playable(ctx: Context, guild: Guild, settings: Settings) -> bool:
    if guild is None:
        await ctx.send(config.NO_GUILD_MESSAGE)
        return False

    command_channel = settings.config['command_channel']
    must_in_vc = settings.config['user_must_be_in_vc']

    if command_channel is not None:
        if command_channel != ctx.channel.id:
            await ctx.send(config.WRONG_CHANNEL_MESSAGE)
            return False

    if must_in_vc:
        author_voice: Optional[VoiceState] = ctx.author.voice
        v: Optional[VoiceProtocol] = guild.voice_client
        if v is None:
            await ctx.send(config.NOT_CONNECTED_MESSAGE)
            return False
        bot_voice_channel = guild.voice_client.channel
        if author_voice is None:
            await ctx.send(config.USER_NOT_IN_VC_MESSAGE)
            return False
        elif author_voice.channel != bot_voice_channel:
            await ctx.send(config.USER_NOT_IN_VC_MESSAGE)
            return False

    return True


def play_list(url: URL) -> List[Song]:
    options = {
        'format': 'bestaudio/best',
        'extract_flat': True,
        "cookiefile": config.COOKIE_PATH
    }
    song_list = []
    with yt_dlp.YoutubeDL(options) as ydl:
        r = ydl.extract_info(url, download=False)

        for entry in r['entries']:
            link = f"https://www.youtube.com/watch?v={entry['id']}"

            song = Song(
                linkutils.Origins.Playlist,
                linkutils.Sites.YouTube,
                webpage_url=link
            )

            song_list.append(song)
    return song_list


def get_song_info(song: Song) -> NoReturn:
    options = {
        'format': 'bestaudio',
        'title': True,
        "cookiefile": config.COOKIE_PATH
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        r = ydl.extract_info(song.info.webpage_url, download=False)
        song.base_url = r.get('url')
        song.info.uploader = r.get('uploader')
        song.info.title = r.get('title')
        song.info.duration = r.get('duration')
        song.info.webpage_url = r.get('webpage_url')
        song.info.thumbnail = r.get('thumbnails')[0]['url']


def search_youtube(title: str) -> Optional[str]:
    """Searches YouTube for the video title and returns the first results video link"""

    # if title is already a link
    if linkutils.get_url(title) is not None:
        return title

    options = {
        'format': 'bestaudio/best',
        'default_search': 'auto',
        'noplaylist': True,
        "cookiefile": config.COOKIE_PATH
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        r = ydl.extract_info(title, download=False)

    if r is None:
        return None

    video_code = r['entries'][0]['id']

    return f"https://www.youtube.com/watch?v={video_code}"


async def preload(song: Song):
    if song.info.title is not None:
        return

    def down(s: Song):
        if s.host == linkutils.Sites.Spotify:
            s.info.webpage_url = search_youtube(s.info.title)

        if s.info.webpage_url is None:
            return None
        get_song_info(s)

    if song.host == linkutils.Sites.Spotify:
        song.info.title = await linkutils.convert_spotify(song.info.webpage_url)

    loop = asyncio.get_event_loop()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_SONG_PRELOAD)
    await asyncio.wait(fs={loop.run_in_executor(executor, down, song)}, return_when=asyncio.ALL_COMPLETED)


async def register_voice_channel(channel):
    await channel.connect(reconnect=True, timeout=None)


class Timer:
    def __init__(self, callback: Callable):
        self._callback = callback
        self._task = asyncio.create_task(self._job())

    async def _job(self):
        await asyncio.sleep(config.VC_TIMEOUT)
        await self._callback()

    def cancel(self):
        self._task.cancel()
