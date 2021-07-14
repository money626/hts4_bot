from discord.ext import commands


class CogBase(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

