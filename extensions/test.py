import discord
import json
from discord import (
    Permissions,
)
from discord.ext.commands import Context
from discord.utils import get

from cores.classes import CogBase
from discord.ext import commands

with open("settings1.json", "r", encoding="utf-8") as fp:
    data = json.load(fp)


class Test(CogBase):
    @commands.command()
    async def repeat(self, ctx: Context, *, msg):
        await ctx.message.delete()
        await ctx.send(msg)

    @commands.command()
    async def ping(self, ctx: Context):
        await ctx.send(f"{self.bot.latency / 1000} ms")

    @commands.command()
    async def check_permissions(self, ctx: Context):
        bot_user = ctx.guild.get_member(self.bot.user.id)
        for channel in self.bot.get_all_channels():
            print(channel.permissions_for(bot_user).is_superset(Permissions(8)))

    @commands.command()
    @commands.bot_has_permissions()
    @commands.has_permissions()
    async def add_group(self, ctx: Context, msg):
        author = ctx.author
        role_name = msg
        check_for_duplicate = get(ctx.guild.roles, name=role_name)
        print(f"Message: {msg}")
        print(f"Duplicate: {check_for_duplicate}")
        if check_for_duplicate is None:  # if the role doesn't exist
            # create the role
            guild = ctx.guild
            role = await guild.create_role(name=role_name, colour=discord.Colour(0x0000FF))
            await author.add_roles(role)

    @commands.command()
    async def enter_voice(self, ctx: Context):
        await ctx.send(self.bot.private_channels)
        await ctx.send(self.bot.voice_clients)


def setup(bot: commands.Bot):
    bot.add_cog(Test(bot))
