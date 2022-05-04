import asyncio
import os
from datetime import (
    date,
    datetime,
)
from typing import NoReturn

from bs4 import BeautifulSoup
from discord import Embed
from discord.ext import commands
from discord.ext.commands import (
    Bot,
)

from config import config
from cores.classes import CogBase
from cores.MapleStoryCrawler import (
    MapleStoryDatabaseHandler,
    MapleStoryEventCrawler,
)


class MapleStory(CogBase):
    def __init__(self, bot: Bot) -> NoReturn:
        super().__init__(bot)
        self.crawler = MapleStoryEventCrawler()
        db_url = os.environ.get("DATABASE_URL")
        self.db = MapleStoryDatabaseHandler(db_url)
        self.channel = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.channel = self.bot.get_channel(907136601493217290)
        await self.get_newest_data_every10min()

    async def get_newest_data_every10min(self) -> NoReturn:
        while True:
            await self._get_newest_data()

            await asyncio.sleep(60 * 10)  # ten minutes

    async def _get_newest_data(self) -> NoReturn:
        def is_today_news(data: dict) -> bool:
            return date.today() == datetime.strptime(data['startDate'], '%Y/%m/%d').date()

        def get_img_url_from_content(content: str) -> str:
            soup = BeautifulSoup(content, 'lxml')
            img = soup.find('img')
            if img is not None:
                return img.get('src')
            else:
                return soup.prettify()

        # get data from page 1
        for event_data in await self.crawler.get_event_list():
            bullentin_id = event_data['bullentinId']
            if is_today_news(event_data) and self.db.is_new_event(bullentin_id):
                self.db.add_found_event(bullentin_id)
                if event_data['urlLink'] is None:
                    detail_event_data = await self.crawler.get_event_data(bullentin_id)
                    embed = Embed(title=event_data['title'],
                                  url=f"https://maplestory.beanfun.com/bulletin?bid={bullentin_id}",
                                  color=config.EMBED_COLOR)
                    embed.set_image(url=get_img_url_from_content(detail_event_data['content']))
                    await self.channel.send("<@&865201522317197362>", embed=embed)
                else:
                    await self.channel.send("\n".join([
                        "<@&865201522317197362>",
                        event_data['title'],
                        f"網址:{event_data['urlLink']}",
                    ]))


def setup(bot: commands.Bot) -> NoReturn:
    bot.add_cog(MapleStory(bot))
