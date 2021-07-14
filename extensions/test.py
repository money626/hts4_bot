import discord
from discord import (
    Permissions,
)
from discord.ext import commands
from discord.ext.commands import Context
from discord.utils import get

from cores.classes import CogBase


class Test(CogBase):
    @commands.command()
    async def repeat(self, ctx: Context, *, msg):
        """Echo"""
        await ctx.message.delete()
        await ctx.send(msg)

    @commands.command()
    async def ping(self, ctx: Context):
        """Bot ping"""
        await ctx.send(f"{self.bot.latency / 1000} ms")

    @commands.command()
    @commands.is_owner()
    async def check_permissions(self, ctx: Context):
        """Check permissions"""
        bot_user = ctx.guild.get_member(self.bot.user.id)
        for channel in self.bot.get_all_channels():
            print(channel.permissions_for(bot_user).is_superset(Permissions(8)))

    @commands.command()
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: Context, amount=5):
        """刪除舊訊息 clear <amount of message>"""
        await ctx.channel.purge(limit=amount)

    @commands.command(aliases=["新身分組", "nr"])
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def new_role(self, ctx: Context, role_name: str, colour: str):
        """建立身分組 new_role 身分組名稱 色碼(FFFFFF) aliases: 新身分組, nr"""
        author = ctx.author
        try:
            role_colour = int(colour, 16)
            if not 0 <= role_colour <= 16777215:
                await ctx.send("顏色格式錯誤")
                return
        except ValueError:
            await ctx.send("顏色格式錯誤")
            return

        check_for_duplicate = get(ctx.guild.roles, name=role_name)
        if check_for_duplicate is None:  # if the role doesn't exist
            # create the role
            guild = ctx.guild
            await guild.create_role(name=role_name, colour=discord.Colour(role_colour))
            await ctx.send(f"已建立身分組{role_name}")

    @commands.command(aliases=["給身分", "ar"])
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def add_role(self, ctx: Context, role_name: str):
        """給予身分組 add_role 身分組 @A @B... aliases: 給身分, ar"""
        role = get(ctx.guild.roles, name=role_name)
        if role is None:
            await ctx.send("沒有此身分組")
        else:
            mention_list = []
            for mention in ctx.message.mentions:
                await mention.add_roles(role)
                mention_list.append(mention.name)
            mention_list = " ,".join(mention_list)
            await ctx.send(f"已給予 {mention_list} {role_name}身分組")

    @commands.command(aliases=["dr"])
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def delete_role(self, ctx: Context, role_name: str):
        """刪除身分組 delete_role 身分組 aliases: dr"""
        role = get(ctx.guild.roles, name=role_name)
        if role is None:
            await ctx.send("沒有此身分組")
        else:
            await role.delete()
            await ctx.send(f"已刪除身分組: {role_name}")


def setup(bot: commands.Bot):
    bot.add_cog(Test(bot))
