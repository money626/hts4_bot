from discord import Message

from cores.classes import CogBase

from discord.ext import commands


class LUL(CogBase):
    @commands.Cog.listener()
    async def on_message(self, msg: Message):
        if msg.guild is None:
            return
        if msg.author != self.bot.user:
            for mention in msg.mentions:
                if mention.id in [553571704681791498]:
                    await msg.channel.send("臭狗")
            for i in ["yo", "侑"]:
                if i in msg.content:
                    await msg.channel.send(f"<@553571704681791498>臭狗")
            for i in ["lul", "lol", "笑死"]:
                if i in msg.content:
                    await msg.reply(i)


def setup(bot: commands.Bot):
    bot.add_cog(LUL(bot))
