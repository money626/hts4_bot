import asyncio
import os
from asyncio import Task
from datetime import (
    time,
)
from typing import (
    Dict,
    get_args,
    List,
    Optional,
)

from discord import TextChannel
from discord.ext import commands
from discord.ext.commands import (
    Bot,
    Context,
)

from cores.classes import CogBase
from cores.LeetCodeCrawler import (
    difficulty_types,
    LeetCodeDatabaseHandler,
    LeetCodeMentionChannel,
    LeetCodeQuestionCrawler,
)
from cores.ScheduleHandler import get_sleep_time


class Leetcode(CogBase):
    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.crawler = LeetCodeQuestionCrawler()
        db_url = os.environ.get("DATABASE_URL")
        self.db = LeetCodeDatabaseHandler(db_url)
        self.mention_channels: Dict[int, LeetCodeMentionChannel] = {}
        self.tasks: Dict[int, Task] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        self.mention_channels = {c.guild_id: c for c in self.db.get_mention_channels()}
        for guild_id, mention_channel in self.mention_channels.items():
            task = self.bot.loop.create_task(
                self.get_newest_data_everyday(mention_channel)
            )
            self.tasks[guild_id] = task

    async def get_newest_data_everyday(self, mention_channel: LeetCodeMentionChannel):
        sleep_time = get_sleep_time(mention_channel.target_time)
        await asyncio.sleep(sleep_time)
        await self._daily_question(mention_channel.message_channel, mention_channel.thread_channel)

        while True:
            await asyncio.sleep(86400)  # one day
            await self._daily_question(mention_channel.message_channel, mention_channel.thread_channel)

    async def _daily_question(self, message_channel: int, thread_channel: Optional[int]):
        channel: TextChannel = self.bot.get_channel(message_channel)
        embed = self.crawler.get_embed_of_question(
            await self.crawler.get_question_of_today()
        )
        message = await channel.send(embed=embed)
        if thread_channel is not None:
            thread_channel: TextChannel = self.bot.get_channel(thread_channel)
            await thread_channel.send(embed.url)
            # f"{q['questionId']}. {q['title']}"
            await message.create_thread(name=embed.title)

    @commands.command(name='qtoday', aliases=["今天題目", "qt"])
    async def _question_today(self, ctx: Context):
        """獲取今天的leetcode題目"""
        await ctx.send(embed=self.crawler.get_embed_of_question(
            await self.crawler.get_question_of_today()
        ))

    @commands.command(name='qmention', aliases=["qm"])
    @commands.guild_only()
    async def _question_mention(
            self,
            ctx: Context,
            target_time: str,
            message_channel: str,
            thread_channel: Optional[str] = None
    ):
        """設定每日題目提醒"""
        message_channel = int(message_channel[2:-1])
        thread_channel = int(thread_channel[2:-1]) if thread_channel is not None else None
        target_time = time.fromisoformat(target_time)
        mention_channel = LeetCodeMentionChannel(ctx.guild.id, target_time, message_channel, thread_channel)
        task = self.tasks.get(ctx.guild.id)
        if task is not None:
            task.cancel()

        self.db.update_notification(mention_channel)
        self.mention_channels[ctx.guild.id] = mention_channel
        self.tasks[ctx.guild.id] = self.bot.loop.create_task(
            self.get_newest_data_everyday(mention_channel)
        )
        await ctx.send("Mention set.")

    @commands.command(name='qremovemention', aliases=["qrm"])
    @commands.guild_only()
    async def _remove_mention(self, ctx: Context):
        task = self.tasks.get(ctx.guild.id)
        if task is None:
            await ctx.send("No mention in this guild")
        task.cancel()
        del self.tasks[ctx.guild.id]
        del self.mention_channels[ctx.guild.id]
        self.db.remove_notification(ctx.guild.id)
        await ctx.send("Mention removed")

    @commands.command(name='qrand', aliases=["刷題", "qr"])
    async def _random_question(self, ctx: Context, difficulty: Optional[str] = None):
        """
        Usage:
        Example: 刷題 M
        :param ctx:
        :param difficulty:
        :return:
        """
        if difficulty is not None:
            difficulty = difficulty.upper()
        valid_arguments: List[difficulty_types] = list(get_args(difficulty_types))
        if difficulty not in valid_arguments:
            await ctx.send("Difficulty: EASY(E)/MEDIUM(M)/HARD(H)/NONE(Default)")
            return
        question = await self.crawler.get_random_question(difficulty)
        await ctx.send(embed=self.crawler.get_embed_of_question(question))


def setup(bot: commands.Bot):
    bot.add_cog(Leetcode(bot))
