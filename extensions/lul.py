import datetime
import os
from collections import defaultdict

from discord import Message
from discord.ext import commands
from discord.ext.commands import (
    Bot,
    Context,
)

from cores.classes import CogBase
from cores.ScheduleHandler import ScheduleHandler

tag_dict = {
    "<@553571704681791498>臭狗": ["侑", "右", "佑", "幼", "柚"],
    "<@399209867811880961>盤子 https://imgur.com/Upi8VSt": ["毛", ],
    "<@552712246497640458>你的最愛": ["夸", "qua", "あくあ", ],
    "<@553571704681791498>": ["臭狗"],
    "<@345563871349571584>半導體之鬼": ["昌", ],
    "<@345563871349571584>": ["開會之鬼", ],
}
tag_reply_dict = {
    553571704681791498: "臭狗",
    541558095827173376: "大佬",
    240874171951874049: "菜雞",
    617675891685720082: "該寫扣了",
}


class HTS4(CogBase):
    def __init__(self, bot: Bot):
        super().__init__(bot)
        db_url = os.environ.get("DATABASE_URL")
        self.schedule_handler = ScheduleHandler(self.bot, db_url)

    @commands.Cog.listener()
    async def on_ready(self):
        self.schedule_handler.load_schedule_from_database()

    @commands.Cog.listener()
    async def on_message(self, msg: Message):
        if msg.guild is None or msg.channel.id == 722431418986135582:
            return
        if msg.author != self.bot.user:
            for mention in msg.mentions:
                if reply := tag_reply_dict.get(mention.id) is not None:
                    await msg.channel.send(reply)

            for v, k in tag_dict.items():
                for i in k:
                    if i in msg.content:
                        await msg.channel.send(v)
            for i in ["lol", "笑死"]:
                if i in msg.content:
                    await msg.reply(i)

    @commands.command(name="提醒", aliases=["ro"])
    async def remind_once(self, ctx: Context, time: str, msg: str):
        """新增單次提醒 提醒 12:00 吃飯 aliases: ro"""
        try:
            target_time = datetime.time.fromisoformat(time)
            await self.schedule_handler.create_schedule(ctx.channel.id, target_time, msg)
            # self.bot.loop.create_task(self.add_schedule(target_time, ctx.send(msg)))
            await ctx.send(f"已新增 {time} 的提醒")
        except ValueError:
            await ctx.send("格式錯誤")

    @commands.command(name="持續提醒", aliases=["remind"])
    async def remind(self, ctx: Context, time: str, msg: str):
        """新增提醒(每日) 持續提醒 20:00 風谷 aliases: remind"""
        try:
            target_time = datetime.time.fromisoformat(time)
            await self.schedule_handler.create_schedule(ctx.channel.id, target_time, msg, True)
            # self.bot.loop.create_task(self.add_schedule(target_time, ctx.send(msg), True))
            await ctx.send(f"已新增 {time} 的提醒")
        except ValueError:
            await ctx.send("格式錯誤")

    @commands.command(aliases=["rr"])
    async def remove_remind(self, ctx: Context, remind_id: str):
        """移除提醒 remove_remind #remind_id aliases: rr"""
        if self.schedule_handler.remove_schedule(remind_id):
            await ctx.send("已刪除該提醒")
        else:
            await ctx.send("無此提醒")

    @commands.command(aliases=["lr"])
    async def list_remind(self, ctx: Context):
        """列出所有提醒 aliases: lr"""
        schedule_list = self.schedule_handler.list_schedule()
        await ctx.send(schedule_list or "目前無提醒")

    @commands.command(name="欠債", aliases=["debt"])
    async def debt_report(self, ctx: Context, mode=""):
        """
        統計欠債項目
        欠債 (self)
        可選 mode: (無), self/個人, full/詳細
        aliases: debt
        """
        await ctx.message.delete()
        all_debt_dict = defaultdict(lambda: defaultdict(list))
        async for msg in ctx.channel.history(oldest_first=True):
            lines = msg.content.split('\n')
            debt_name = f"{msg.created_at.strftime('%Y-%m-%d')} {lines[0]}"
            creditor = f"<@!{msg.author.id}>"
            if msg.author != self.bot.user:
                for line in lines[1:]:
                    item = [i for i in line.split(" ") if i != '']
                    if item[0].startswith("~~"):
                        continue
                    if len(item) < 2 or not item[0].startswith("<@"):
                        break
                    try:
                        debtor = f"<@!{item[0][-19:-1]}>"
                        debt = eval(item[1])
                        all_debt_dict[debtor][creditor].append((debt_name, debt))
                    except (ValueError, SyntaxError):
                        await msg.reply("格式錯誤")
                        break
            else:
                if lines[0] == "欠債紀錄":
                    if mode in ["", "full", "詳細"]:
                        await msg.delete()
                elif lines[0] == "個人欠債":
                    item = [i for i in lines[1].split(" ") if i != '']
                    print(item)
                    debtor_id = item[0][-19:-1]
                    print(debtor_id, ctx.author.id)
                    if mode in ["self", "個人"] and debtor_id == f"{ctx.author.id}":
                        await msg.delete()
                else:
                    await msg.delete()
        return_msg = []
        for debtor, data in all_debt_dict.items():
            if mode.lower() in ["self", "個人"] and debtor != f"<@!{ctx.author.id}>":
                continue

            for creditor, debt_list in data.items():
                return_msg.append(f"{debtor} 欠 {creditor}")
                total_debt = 0
                for debt_name, debt in debt_list:
                    total_debt += debt
                    if mode.lower() in ["詳細", "full"]:
                        return_msg.append(f"{debt_name}: {debt}元")
                return_msg.append(f"共**{total_debt}**元")
                return_msg.append("")

        if len(return_msg):
            if mode.lower() in ["self", "個人"]:
                return_msg = ["個人欠債"] + return_msg
            else:
                return_msg = ["欠債紀錄"] + return_msg
        if mode.lower() in ["self", "個人"]:
            await ctx.send("\n".join(return_msg) or f"個人欠債\n<@!{ctx.author.id}> 你沒欠錢")
        else:
            return_msg = "\n".join(return_msg)
            msg_length = len(return_msg)
            if msg_length < 2000:
                await ctx.send(return_msg or "欠債紀錄\n沒人欠錢或是機器人壞掉了")
            else:
                while msg_length:
                    if msg_length <= 2000:
                        await ctx.send(return_msg)
                        break
                    else:
                        i = 1999
                        while return_msg[i] != '\n':
                            i -= 1
                        await ctx.send(return_msg[:i])
                        return_msg = return_msg[i:]
                        msg_length = len(return_msg)

    @commands.command(name="我欠多少", aliases=["owe"])
    async def owe_how_much(self, ctx: Context):
        """統計該使用者欠多少 aliases: owe"""
        await self.debt_report(ctx, "self")

    @commands.command(name="清除機器人訊息", aliases=["clear_bot_msg"])
    async def pay_back(self, ctx: Context):
        async for msg in ctx.channel.history():
            if msg.author == self.bot.user:
                await msg.delete()


def setup(bot: commands.Bot):
    bot.add_cog(HTS4(bot))
