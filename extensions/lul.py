import asyncio
import datetime
from typing import (
    Coroutine,
)

from dateutil import tz
from discord import Message
from discord.ext import commands
from discord.ext.commands import Context

from cores.classes import CogBase

tag_dict = {
    "<@553571704681791498>臭狗": ["侑", "又", "右", "佑", "幼", "柚"],
    "<@399209867811880961>盤子": ["毛", ],
    "<@552712246497640458>你的最愛": ["夸", "qua", "あくあ", ],
    "<@553571704681791498>": ["臭狗"],
    "<@345563871349571584>半導體之鬼": ["昌", ],
    "<@345563871349571584>": ["開會之鬼", ],
}


class LUL(CogBase):
    async def add_schedule(self, target_time: datetime.time, callback: Coroutine, continuous: bool = False):
        t1 = datetime.datetime.now(tz=tz.gettz("UTC+8"))
        t2 = datetime.datetime(
            year=t1.year, month=t1.month, day=t1.day,
            hour=target_time.hour, minute=target_time.minute,
            second=target_time.second, tzinfo=tz.gettz("UTC+8")
        )
        delta = t2 - t1
        sleep_time = delta.total_seconds() % 86400
        print(sleep_time)
        await asyncio.sleep(sleep_time)
        self.bot.loop.create_task(callback)
        while continuous:
            await asyncio.sleep(86400)  # one day
            self.bot.loop.create_task(callback)

    @commands.Cog.listener()
    async def on_message(self, msg: Message):
        if msg.guild is None:
            return
        if msg.author != self.bot.user:
            for mention in msg.mentions:
                if mention.id in [553571704681791498]:
                    await msg.channel.send("臭狗")

            for v, k in tag_dict.items():
                for i in k:
                    if i in msg.content:
                        await msg.channel.send(v)
            for i in ["lul", "lol", "笑死"]:
                if i in msg.content:
                    await msg.reply(i)

    @commands.command(name="提醒", aliases=["ro"])
    async def remind_once(self, ctx: Context, time: str, msg: str):
        """新增單次提醒 提醒 12:00 吃飯 aliases: ro"""
        try:
            target_time = datetime.time.fromisoformat(time)
            self.bot.loop.create_task(self.add_schedule(target_time, ctx.send(msg)))
            await ctx.send(f"已新增 {time} 的提醒")
        except ValueError:
            await ctx.send("格式錯誤")

    @commands.command(name="持續提醒", aliases=["remind"])
    async def remind(self, ctx: Context, time: str, msg: str):
        """新增提醒(每日) 持續提醒 20:00 風谷 aliases: remind"""
        try:
            target_time = datetime.time.fromisoformat(time)
            self.bot.loop.create_task(self.add_schedule(target_time, ctx.send(msg), True))
            await ctx.send(f"已新增 {time} 的提醒")
        except ValueError:
            await ctx.send("格式錯誤")


def setup(bot: commands.Bot):
    bot.add_cog(LUL(bot))
