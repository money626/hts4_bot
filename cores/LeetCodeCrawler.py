import os.path
from datetime import time
from pathlib import Path
from typing import (
    Any,
    List,
    Literal,
    Optional,
)

import aiohttp
from discord import Embed

from config import config
from cores.classes import DatabaseHandlerBase

BASE_DIR = Path(__file__).resolve(strict=True).parent
GQL_DIR = os.path.join(BASE_DIR, "leetcode_graphql")
with open(f"{GQL_DIR}/questionOfToday.gql", "r", encoding='utf8') as fp:
    questionOfToday_query = fp.read()
with open(f"{GQL_DIR}/problemsetQuestionList.gql", "r", encoding='utf8') as fp:
    questionList_query = fp.read()
with open(f"{GQL_DIR}/questionTotalNum.gql", "r", encoding='utf8') as fp:
    questionTotalNum_query = fp.read()
with open(f"{GQL_DIR}/randomQuestion.gql", "r", encoding='utf8') as fp:
    randomQuestion_query = fp.read()

GQL_URL = "https://leetcode.com/graphql/"
difficulty_types = Literal["EASY", "MEDIUM", "HARD", None, "E", "M", "H"]


class LeetCodeQuestionCrawler:

    def __init__(self):
        self.s = aiohttp.ClientSession(headers={
            'user-agent': config.CRAWLER_AGENT,
        })
        # await self.s.get('https://leetcode.com/problemset/all/?page=1')
        # csrf_token = self.s.cookie_jar.filter_cookies(URL('https://leetcode.com')).get('csrftoken')
        # self.s.headers.update({
        #     'x-csrftoken': csrf_token
        # })

    async def get_question_of_today(self) -> dict:
        j = {
            "query": questionOfToday_query,
            "variables": {}
        }
        async with self.s.post(GQL_URL, json=j) as req:
            res = await req.json()
        return res['data']['activeDailyCodingChallengeQuestion']['question']

    async def get_question_list(self, difficulty: difficulty_types = None, skip: int = 0, limit: int = 10) -> list:
        difficulty = shorthand_to_full(difficulty)
        j = {
            "query": questionList_query,
            "variables": {
                "categorySlug": "",
                "skip": skip,
                "limit": limit,
                "filters": {} if difficulty is None else {
                    "difficulty": difficulty
                }
            }
        }
        async with self.s.post(GQL_URL, json=j) as req:
            res = await req.json()
        return res['data']['questionList']['questions']

    async def get_length_of_questions(self, difficulty: difficulty_types = None) -> int:
        difficulty = shorthand_to_full(difficulty)
        j = {
            "query": questionTotalNum_query,
            "variables": {
                "categorySlug": "",
                "filters": {} if difficulty is None else {
                    "difficulty": difficulty
                }
            }
        }
        async with self.s.post(GQL_URL, json=j) as req:
            res = await req.json()

        return res['data']['questionList']['total']

    async def get_random_question(self, difficulty: difficulty_types = None) -> dict:
        difficulty = shorthand_to_full(difficulty)
        j = {
            "query": randomQuestion_query,
            "variables": {
                "categorySlug": "",
                "filters": {} if difficulty is None else {
                    "difficulty": difficulty
                }
            }
        }
        async with self.s.post(GQL_URL, json=j) as req:
            res = await req.json()
        return res['data']['randomQuestion']

    @staticmethod
    def get_embed_of_question(question: dict):
        embed = Embed(
            title=f"{question['questionId']}. {question['title']}",
            url=f"https://leetcode.com/problems/{question['titleSlug']}",
            color=config.EMBED_COLOR
        )
        embed.set_thumbnail(url="https://leetcode.com/static/images/LeetCode_Sharing.png")
        embed.add_field(name="Difficulty", value=question['difficulty'], inline=False)
        embed.add_field(name="Accuracy Rate", value=f"{question['acRate']:.2f}%", inline=False)
        embed.add_field(name="Tags", value=", ".join([i['name'] for i in question['topicTags']]), inline=False)
        return embed


def shorthand_to_full(difficulty: difficulty_types) -> difficulty_types:
    if difficulty is not None:
        difficulty = difficulty.upper()
    if difficulty == "E":
        difficulty = "EASY"
    elif difficulty == "M":
        difficulty = "MEDIUM"
    elif difficulty == "H":
        difficulty = "HARD"
    return difficulty


class LeetCodeMentionChannel(object):
    def __init__(
            self,
            guild_id: int,
            target_time: time,
            message_channel: int,
            thread_channel: Optional[int]
    ):
        self.guild_id = guild_id
        self.target_time = target_time
        self.message_channel = message_channel
        self.thread_channel = thread_channel

    def __iter__(self):
        yield self.guild_id
        yield self.target_time
        yield self.message_channel
        yield self.thread_channel


class LeetCodeDatabaseHandler(DatabaseHandlerBase):
    _table_name = "leetcode"
    _create_table_sql = """
        CREATE TABLE leetcode (
            guild_id bigint PRIMARY KEY,
            target_time time not null,
            message_channel bigint not null,
            thread_channel bigint
        );"""

    def __init__(self, dsn: Any):
        super(LeetCodeDatabaseHandler, self).__init__(dsn)

    def update_notification(self, mention_channel: LeetCodeMentionChannel):
        with self.conn:
            with self.conn.cursor() as cur:
                sql = """
                    INSERT INTO leetcode
                    (guild_id, target_time, message_channel, thread_channel)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (guild_id) DO UPDATE 
                    SET target_time = excluded.target_time,
                        message_channel = excluded.message_channel,
                        thread_channel = excluded.thread_channel;"""
                cur.execute(sql, tuple(mention_channel))

    def remove_notification(self, guild_id: int):
        with self.conn:
            with self.conn.cursor() as cur:
                sql = "DELETE FROM leetcode WHERE guild_id=%s;"
                cur.execute(sql, (guild_id,))

    def get_mention_channels(self) -> List[LeetCodeMentionChannel]:
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute("SELECT * FROM leetcode WHERE True;")
                mention_channels = []
                for d in cur:
                    mention_channels.append(
                        LeetCodeMentionChannel(*d)
                    )
        return mention_channels
