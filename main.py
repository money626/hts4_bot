import json
import os

from discord.ext import commands

print("機器人登入中 ...")
bot = commands.Bot(command_prefix="87")

for extension in os.listdir('extensions'):
    if extension.endswith('.py'):
        extension_name = f'extensions.{extension[:-3]}'
        bot.load_extension(extension_name)
        print(f"{extension_name} loaded")

token = os.environ.get("TOKEN")
if token is None:
    exit(2)

bot.run(token)
