from typing import Any

import psycopg2
import requests
from bs4 import BeautifulSoup


class MapleStoryEventCrawler:

    def __init__(self):
        self.s = requests.Session()
        req = self.s.get('https://maplestory.beanfun.com/main?section=mBulletin')
        soup = BeautifulSoup(req.text, 'lxml')
        self.csrf = soup.find('input').get('value')
        self.s.headers.update({
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'x-csrf-token': self.csrf,
            'x-requested-with': 'XMLHttpRequest'
        })

    def get_event_list(self, page: int) -> list:
        req = self.s.post(
            'https://maplestory.beanfun.com/main?handler=BulletinProxy',
            data={
                'Kind': 72,  # 活動
                'Page': page,
                'method': 3,
                'PageSize': 10
            })
        return req.json()['data']['myDataSet']['table']

    def get_event_data(self, bullentinId: int) -> dict:
        req = self.s.post(
            'https://maplestory.beanfun.com/bulletin?handler=BulletinDetail',
            data={
                'Bid': bullentinId
            })
        return req.json()['data']['myDataSet']['table']


class MapleStoryDatabaseHandler:
    def __init__(self, dsn: Any):
        self.conn = psycopg2.connect(dsn)
        if not self.__database_table_exists():
            self.__create_database_table()

    def __database_table_exists(self):
        with self.conn as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT tablename
                    FROM pg_catalog.pg_tables
                    WHERE schemaname != 'pg_catalog' AND
                          schemaname != 'information_schema';
                """)
                for data in cur:
                    if data[0] == 'maple_story_event':
                        return True
                else:
                    return False

    def __create_database_table(self):
        with self.conn as conn:
            with conn.cursor() as cur:
                cur.execute("""
                CREATE TABLE maple_story_event (
                    id serial PRIMARY KEY , 
                    bullentinId int not null 
                     );
                """)

    def add_found_event(self, bullentinId: int):
        """
        Adds bullentinId to the table to avoid sending duplicate messages.
        :param bullentinId:  int Event page ID
        :return:
        """
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO maple_story_event (bullentinId) VALUES (%s);""",
                    (bullentinId,)
                )

    def is_new_event(self, bullentinId: int) -> bool:
        """
        Gets whether this bullentinId is new event or not.
        :param bullentinId: int
        :return: bool
        """
        with self.conn as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT * FROM maple_story_event WHERE bullentinId=%s", (bullentinId,))
                events = cur.fetchall()
        return len(events) == 0
