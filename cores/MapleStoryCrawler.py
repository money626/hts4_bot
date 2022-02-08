from typing import Any

import aiohttp
from bs4 import BeautifulSoup

from config import config
from cores.classes import DatabaseHandlerBase


class MapleStoryEventCrawler:

    def __init__(self):
        self.s = aiohttp.ClientSession(headers={
            'user-agent': config.CRAWLER_AGENT,
        })

    def __del__(self):
        self.s.close()

    async def init_csrf(self):
        req = await self.s.get("https://maplestory.beanfun.com/main?section=mBulletin")
        soup = BeautifulSoup(await req.text(), 'lxml')
        csrf = soup.find('input').get('value')
        self.s.headers.update({
            'x-csrf-token': csrf,
            'x-requested-with': 'XMLHttpRequest'
        })

    async def get_event_list(self, page: int = 1) -> list:
        if self.s.headers.get('x-csrf-token') is None:
            await self.init_csrf()
        url = "https://maplestory.beanfun.com/main?handler=BulletinProxy"
        data = {
            'Kind': 72,  # 活動
            'Page': page,
            'method': 3,
            'PageSize': 10
        }
        async with self.s.post(url, data=data) as req:
            res = await req.json()
            return res['data']['myDataSet']['table']

    async def get_event_data(self, bullentin_id: int) -> dict:
        if self.s.headers.get('x-csrf-token') is None:
            await self.init_csrf()
        url = "https://maplestory.beanfun.com/bulletin?handler=BulletinDetail"
        async with self.s.post(url, data={'Bid': bullentin_id}) as req:
            res = await req.json()
            return res['data']['myDataSet']['table']


class MapleStoryDatabaseHandler(DatabaseHandlerBase):
    _table_name = "maple_story_event"
    _create_table_sql = """
            CREATE TABLE maple_story_event (
                id serial PRIMARY KEY , 
                bullentinId int not null 
            );"""

    def __init__(self, dsn: Any):
        super(MapleStoryDatabaseHandler, self).__init__(dsn)

    def add_found_event(self, bullentin_id: int):
        """
        Adds bullentinId to the table to avoid sending duplicate messages.
        :param bullentin_id:  int Event page ID
        :return:
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """INSERT INTO maple_story_event (bullentinId) VALUES (%s);""",
                (bullentin_id,)
            )

    def is_new_event(self, bullentin_id: int) -> bool:
        """
        Gets whether this bullentinId is new event or not.
        :param bullentin_id: int
        :return: bool
        """
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT * FROM maple_story_event WHERE bullentinId=%s", (bullentin_id,))
            events = cur.fetchall()
        return len(events) == 0
