import asyncio

import discord
from discord import (
    PartialEmoji,
    RawReactionActionEvent,
)
from discord.ext import commands
from discord.ext.commands import (
    Context,
)
from discord.ext.commands.errors import (
    CheckAnyFailure,
    CommandInvokeError,
    CommandNotFound,
    MissingRequiredArgument,
    NotOwner,
)
from discord.member import User

from cores.classes import CogBase


class Main(CogBase):

    # event listeners
    @commands.Cog.listener()
    async def on_ready(self):
        print("bot is on")
        self.bot.loop.create_task(self.status())

    @commands.Cog.listener()
    async def on_member_join(self, member: User):
        print(f"{member.id}")
        print(f"{member} joined!")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        print(payload.message_id)
        print(str(payload.emoji))
        print(payload.emoji == "<:sword:720231511655186534>")
        print(payload.emoji.name)

        def print_emoji(emoji: PartialEmoji):
            pass

        print(payload.emoji)
        for i in str(payload.emoji):
            print(i, end='')
        print()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error):
        print(error)
        print(type(error))

        if isinstance(error, CommandNotFound):
            await ctx.send("無此指令")
        elif isinstance(error, MissingRequiredArgument):
            await ctx.send("缺少參數")
        elif isinstance(error, CommandInvokeError):
            if str(ctx.command) == 'unload' or str(ctx.command) == 'reload':
                await ctx.send("此模組尚未被加載")
            elif str(ctx.command) == 'load':
                print(str(error).find("ExtensionAlreadyLoaded"))
                if str(error).find("ExtensionAlreadyLoaded") >= 0:
                    await ctx.send("此模組已經加載過了")
                else:
                    await ctx.send("無此模組")
            print(ctx.command)
            print(ctx.kwargs)
        elif isinstance(error, CheckAnyFailure):
            await ctx.send("你沒有權限執行這項指令")
        elif isinstance(error, NotOwner):
            await ctx.send("只有機器人擁有者可以使用這個指令")

    async def status(self):
        while True:
            await self.update('幫我撐10秒')
            await asyncio.sleep(10)
            await self.update('Switch')
            await asyncio.sleep(3)
            await self.update('スターバース・トストーリム')
            await asyncio.sleep(5)

    async def update(self, text):
        await self.bot.change_presence(activity=discord.Game(name=text))

    # extension commands
    @commands.command()
    @commands.is_owner()
    async def r(self, ctx: Context):
        """Reload main Cog"""
        self.bot.reload_extension("extensions.main")
        await ctx.send(f"main reloaded!")

    @commands.command()
    @commands.is_owner()
    async def load(self, ctx: Context, msg: str):
        """Load 指定 Cog"""
        extension = f"extensions.{msg}"
        self.bot.load_extension(extension)
        await ctx.send(f"{msg} loaded!")

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx: Context, msg: str):
        """Reload 指定 Cog"""
        self.bot.reload_extension(f"extensions.{msg}")
        await ctx.send(f"{msg} reloaded!")

    @commands.command()
    @commands.is_owner()
    async def unload(self, ctx: Context, msg: str):
        """Unload 指定 Cog"""
        if msg == 'main':
            await ctx.send("main should never be unloaded")
        else:
            self.bot.unload_extension(f"extensions.{msg}")
            await ctx.send(f"{msg} unloaded!")

    @commands.command()
    @commands.is_owner()
    async def list(self, ctx: Context):
        """列出所有Cog"""
        msg = "\n".join(i[11:] for i in self.bot.extensions.keys())
        await ctx.send(f"``{msg}``")


def setup(bot: commands.Bot):
    bot.add_cog(Main(bot))
