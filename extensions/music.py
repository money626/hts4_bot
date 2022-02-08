import asyncio
import os
from typing import Dict

import discord
from discord.ext import commands
from discord.ext.commands import (
    Bot,
    Context,
)

from config import config
from cores.classes import CogBase
from cores.musicbot import (
    linkutils,
    utils,
)
from cores.musicbot.audioController import AudioController
from cores.musicbot.settings import (
    MusicSettingsDatabaseHandler,
    Settings,
)


class Music(CogBase):
    def __init__(self, bot: Bot):
        super(Music, self).__init__(bot)
        self.guild_audio_controller: Dict[int, AudioController] = {}
        db_url = os.environ.get("DATABASE_URL")
        self.db = MusicSettingsDatabaseHandler(db_url)

    @commands.Cog.listener()
    async def on_ready(self):
        for g in self.bot.guilds:
            print(g)
            # g: Guild
            g_settings = self.db.get_settings(g.id)
            s = Settings(g, g_settings)
            if g_settings is None:
                self.db.save_settings(s.config)
            self.guild_audio_controller[g.id] = AudioController(g, s)

    @commands.command(name='play', description=config.HELP_YT_LONG, help=config.HELP_YT_SHORT,
                      aliases=['p', 'yt', 'pl'])
    async def _play_song(self, ctx: Context, *, track: str):
        current_guild = utils.get_guild(ctx)
        audio_controller = self.guild_audio_controller[current_guild.id]

        if await audio_controller.is_connected() is None:
            if not await audio_controller.connect(ctx):
                return
        if track.isspace() or not track:
            return
        if not await utils.playable(ctx, current_guild, audio_controller.sett):
            return

        # reset timer
        audio_controller.timer.cancel()
        audio_controller.timer = utils.Timer(audio_controller.timeout_handler)

        if audio_controller.playlist.loop:
            await ctx.send(f"Loop is enabled! Use {config.BOT_PREFIX}loop to disable")
            return

        song = await audio_controller.process_song(track, ctx)
        print(song)
        if song is None:
            await ctx.send(config.SONGINFO_ERROR)
            return

        if song.origin == linkutils.Origins.Default:
            if audio_controller.current_song is None or len(audio_controller.playlist.play_deque) > 0:
                await ctx.send(embed=song.info.format_output(config.SONGINFO_QUEUE_ADDED))

        elif song.origin == linkutils.Origins.Playlist:
            await ctx.send(config.SONGINFO_PLAYLIST_QUEUED)

    @commands.command(name='loop', description=config.HELP_LOOP_LONG, help=config.HELP_LOOP_SHORT, aliases=['l'])
    async def _loop(self, ctx: Context):
        current_guild = utils.get_guild(ctx)
        audio_controller = self.guild_audio_controller[current_guild.id]

        if not await utils.playable(ctx, current_guild, audio_controller.sett):
            return

        if len(audio_controller.playlist.play_deque) < 1 and not current_guild.voice_client.is_playing():
            await ctx.send("No songs in queue!")
            return

        if not audio_controller.playlist.loop:
            audio_controller.playlist.loop = True
            await ctx.send("Loop enabled :arrows_counterclockwise:")
        else:
            audio_controller.playlist.loop = False
            await ctx.send("Loop disabled :x:")

    @commands.command(name='shuffle', description=config.HELP_SHUFFLE_LONG, help=config.HELP_SHUFFLE_SHORT,
                      aliases=["sh"])
    async def _shuffle(self, ctx: Context):
        current_guild = utils.get_guild(ctx)
        guild_id = current_guild.id
        audio_controller = self.guild_audio_controller[guild_id]

        if not await utils.playable(ctx, current_guild, audio_controller.sett):
            return

        if current_guild.voice_client is None or not current_guild.voice_client.is_playing():
            await ctx.send("Queue is empty :x:")
            return

        audio_controller.playlist.shuffle()
        await ctx.send("Shuffled queue :twisted_rightwards_arrows:")

        for song in list(audio_controller.playlist.play_deque)[:config.MAX_SONG_PRELOAD]:
            asyncio.ensure_future(utils.preload(song))

    @commands.command(name='pause', description=config.HELP_PAUSE_LONG, help=config.HELP_PAUSE_SHORT)
    async def _pause(self, ctx: Context):
        current_guild = utils.get_guild(ctx)
        audio_controller = self.guild_audio_controller[current_guild.id]
        if not await utils.playable(ctx, current_guild, audio_controller.sett):
            return

        if current_guild is None:
            await ctx.send(config.NO_GUILD_MESSAGE)
            return
        if current_guild.voice_client is None:
            return
        current_guild.voice_client.pause()
        await ctx.send("Playback Paused :pause_button:")

    @commands.command(name='queue', description=config.HELP_QUEUE_LONG, help=config.HELP_QUEUE_SHORT,
                      aliases=['playlist', 'q'])
    async def _queue(self, ctx: Context):
        current_guild = utils.get_guild(ctx)
        audio_controller = self.guild_audio_controller[current_guild.id]
        if not await utils.playable(ctx, current_guild, audio_controller.sett):
            return

        if current_guild.voice_client is None or not current_guild.voice_client.is_playing():
            await ctx.send("Queue is empty :x:")
            return

        playlist = audio_controller.playlist

        # Embeds are limited to 25 fields
        if config.MAX_SONG_PRELOAD > 25:
            config.MAX_SONG_PRELOAD = 25

        embed = discord.Embed(title=f":scroll: Queue [{len(playlist.play_deque)}]", color=config.EMBED_COLOR, inline=False)

        for counter, song in enumerate(list(playlist.play_deque)[:config.MAX_SONG_PRELOAD], start=1):
            if song.info.title is None:
                embed.add_field(name=f"{counter}.", value=f"[{song.info.webpage_url}]({song.info.webpage_url})", inline=False)
            else:
                embed.add_field(name=f"{counter}.", value=f"[{song.info.title}]({song.info.webpage_url})", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name='stop', description=config.HELP_STOP_LONG, help=config.HELP_STOP_SHORT, aliases=['st'])
    async def _stop(self, ctx: Context):
        current_guild = utils.get_guild(ctx)
        audio_controller = self.guild_audio_controller[current_guild.id]
        if not await utils.playable(ctx, current_guild, audio_controller.sett):
            return

        audio_controller.playlist.loop = False
        await audio_controller.stop_player()
        await ctx.send("Stopped all sessions :octagonal_sign:")

    @commands.command(name='move', description=config.HELP_MOVE_LONG, help=config.HELP_MOVE_SHORT, aliases=['mv'])
    async def _move(self, ctx: Context, old_index: int, new_index: int):
        current_guild = utils.get_guild(ctx)
        guild_id = current_guild.id
        audio_controller = self.guild_audio_controller[guild_id]
        if current_guild.voice_client is None or (
                not current_guild.voice_client.is_paused() and not current_guild.voice_client.is_playing()):
            await ctx.send("Queue is empty :x:")
            return
        try:
            audio_controller.playlist.move(old_index - 1, new_index - 1)
        except IndexError:
            await ctx.send("Wrong position")
            return
        await ctx.send("Moved")

    @commands.command(name='skip', description=config.HELP_SKIP_LONG, help=config.HELP_SKIP_SHORT, aliases=['s'])
    async def _skip(self, ctx: Context):
        current_guild = utils.get_guild(ctx)
        audio_controller = self.guild_audio_controller[current_guild.id]
        if not await utils.playable(ctx, current_guild, audio_controller.sett):
            return

        audio_controller.playlist.loop = False
        audio_controller.timer.cancel()
        audio_controller.timer = utils.Timer(audio_controller.timeout_handler)

        if current_guild.voice_client is None or (
                not current_guild.voice_client.is_paused() and not current_guild.voice_client.is_playing()):
            await ctx.send("Queue is empty :x:")
            return
        current_guild.voice_client.stop()
        await ctx.send("Skipped current song :fast_forward:")

    @commands.command(name='clear', description=config.HELP_CLEAR_LONG, help=config.HELP_CLEAR_SHORT, aliases=['cl'])
    async def _clear(self, ctx: Context):
        current_guild = utils.get_guild(ctx)
        guild_id = current_guild.id
        audio_controller = self.guild_audio_controller[guild_id]
        if not await utils.playable(ctx, current_guild, audio_controller.sett):
            return

        audio_controller.clear_queue()
        current_guild.voice_client.stop()
        audio_controller.playlist.loop = False
        await ctx.send("Cleared queue :no_entry_sign:")

    @commands.command(name='prev', description=config.HELP_PREV_LONG, help=config.HELP_PREV_SHORT, aliases=['back'])
    async def _prev(self, ctx: Context):
        current_guild = utils.get_guild(ctx)
        audio_controller = self.guild_audio_controller[current_guild.id]
        if not await utils.playable(ctx, current_guild, audio_controller.sett):
            return

        audio_controller.playlist.loop = False
        audio_controller.timer.cancel()
        audio_controller.timer = utils.Timer(audio_controller.timeout_handler)

        await audio_controller.prev_song(ctx)
        await ctx.send("Playing previous song :track_previous:")

    @commands.command(name='resume', description=config.HELP_RESUME_LONG, help=config.HELP_RESUME_SHORT)
    async def _resume(self, ctx: Context):
        current_guild = utils.get_guild(ctx)
        audio_controller = self.guild_audio_controller[current_guild.id]
        if not await utils.playable(ctx, current_guild, audio_controller.sett):
            return

        current_guild.voice_client.resume()
        await ctx.send("Resumed playback :arrow_forward:")

    @commands.command(name='songinfo', description=config.HELP_SONGINFO_LONG, help=config.HELP_SONGINFO_SHORT,
                      aliases=["np"])
    async def _song_info(self, ctx: Context):
        current_guild = utils.get_guild(ctx)
        audio_controller = self.guild_audio_controller[current_guild.id]
        if not await utils.playable(ctx, current_guild, audio_controller.sett):
            return

        song = audio_controller.current_song
        if song is None:
            return
        await ctx.send(embed=song.info.format_output(config.SONGINFO_SONGINFO))

    @commands.command(name='history', description=config.HELP_HISTORY_LONG, help=config.HELP_HISTORY_SHORT)
    async def _history(self, ctx: Context):
        current_guild = utils.get_guild(ctx)
        guild_id = current_guild.id
        audio_controller = self.guild_audio_controller[guild_id]
        if not await utils.playable(ctx, current_guild, audio_controller.sett):
            return

        await ctx.send(self.guild_audio_controller[guild_id].track_history())

    @commands.command(name='volume', aliases=["vol"], description=config.HELP_VOL_LONG, help=config.HELP_VOL_SHORT)
    async def _volume(self, ctx: Context, *args):
        current_guild = utils.get_guild(ctx)
        guild_id = current_guild.id
        audio_controller = self.guild_audio_controller[guild_id]

        if not await utils.playable(ctx, current_guild, audio_controller.sett):
            return

        if len(args) == 0:
            await ctx.send(f"Current volume: {audio_controller.volume}% :speaker:")
            return

        try:
            volume = args[0]
            volume = int(volume)
            if volume > 100 or volume < 0:
                raise ValueError
            if self.guild_audio_controller[guild_id].volume >= volume:
                await ctx.send(f'Volume set to {volume}% :sound:')
            else:
                await ctx.send(f'Volume set to {volume}% :loud_sound:')
            self.guild_audio_controller[guild_id].volume = volume
        except ValueError:
            await ctx.send("Error: Volume must be a number 1-100")


def setup(bot: Bot):
    bot.add_cog(Music(bot))
