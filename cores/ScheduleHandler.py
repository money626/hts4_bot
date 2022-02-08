import asyncio
import datetime
from datetime import time
from typing import (
    Any,
    Coroutine,
    List,
    Optional,
    Tuple,
)
from uuid import uuid4

import psycopg2
from dateutil import tz
from discord.ext.commands import Bot

Schedule = Tuple[str, int, time, str, bool]


class ScheduleHandler:
    def __init__(self, bot: Bot, dsn: Any):
        self.bot = bot
        self.schedule_db_handler = ScheduleDatabaseHandler(dsn)

    async def _run_schedule(self, target_time: datetime.time, callback: Coroutine, repeat: bool = False):
        t1 = datetime.datetime.now(tz=tz.gettz("UTC+8"))
        t2 = datetime.datetime(
            year=t1.year, month=t1.month, day=t1.day,
            hour=target_time.hour, minute=target_time.minute,
            second=target_time.second, tzinfo=tz.gettz("UTC+8")
        )
        delta = t2 - t1
        sleep_time = delta.total_seconds() % 86400
        # print(sleep_time)
        await asyncio.sleep(sleep_time)
        await callback

        while repeat:
            await asyncio.sleep(86400)  # one day
            await callback
        else:
            current_task = asyncio.tasks.current_task(self.bot.loop)
            schedule_id = current_task.get_name()
            success = self.schedule_db_handler.remove_schedule(schedule_id)

    async def create_schedule(self, channel_id: int, target_time: time, msg: str, repeat: bool = False) -> bool:
        channel = self.bot.get_channel(channel_id)
        schedule_id = self.schedule_db_handler.create_schedule(channel_id, target_time, msg, repeat)
        if schedule_id is None:
            return False
        else:
            self.bot.loop.create_task(
                self._run_schedule(target_time, channel.send(msg), repeat),
                name=schedule_id
            )
            return True

    def remove_schedule(self, schedule_id: str) -> bool:
        for task in asyncio.tasks.all_tasks(self.bot.loop):
            if task.get_name() == schedule_id:
                task.cancel()
                self.schedule_db_handler.remove_schedule(schedule_id)
                return True
        else:
            return False

    def list_schedule(self) -> str:
        data_msg = "\n".join([
            f"Schedule_id: {schedule[0]}\tTime: {schedule[2]}\tmsg: {schedule[3]}"
            for schedule in self.schedule_db_handler.list_schedules()
        ])
        return data_msg

    def load_schedule_from_database(self):
        for schedule in self.schedule_db_handler.list_schedules():
            channel = self.bot.get_channel(schedule[1])

            self.bot.loop.create_task(
                self._run_schedule(
                    schedule[2],
                    channel.send(schedule[3]),
                    schedule[4]
                ),
                name=schedule[0]
            )


class ScheduleDatabaseHandler:
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
                    if data[0] == 'schedules':
                        return True
                else:
                    return False

    def __create_database_table(self):
        with self.conn as conn:
            with conn.cursor() as cur:
                cur.execute("""
                CREATE TABLE schedules (
                    id uuid PRIMARY KEY, 
                    channel_id bigint not null , 
                    target_time time not null , 
                    msg varchar not null ,
                    repeat bool not null );
                """)

    def create_schedule(self, channel_id: int, target_time: time, msg: str, repeat: bool) -> Optional[str]:
        """
        Creates a schedule data in the database
        :param channel_id: int (use to send message)
        :param target_time: time
        :param msg: str
        :param repeat: bool
        :return:
        """
        schedule_id = uuid4().hex

        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO schedules (id, channel_id, target_time, msg, repeat) VALUES (%s, %s, %s, %s, %s);""",
                    (schedule_id, channel_id, target_time, msg, repeat)
                )
        return schedule_id

    def remove_schedule(self, schedule_id: str) -> bool:
        """
        Removes the schedule with schedule_id
        :param schedule_id: str
        :return: bool
        """
        with self.conn as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH deleted AS 
                            (DELETE FROM schedules WHERE id=%s RETURNING *) 
                    SELECT count(*) 
                    FROM deleted;""",
                    (schedule_id,)
                )
                success = cur.fetchall()[0][0] == 1
        return success

    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """
        Gets a schedule with schedule_id
        :param schedule_id:
        :return: Optional[Schedule]
        """
        with self.conn as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT * FROM schedules WHERE id=%s", (schedule_id,))
                schedule = cur.fetchall()
        if len(schedule) == 0:
            return None
        else:
            return schedule[0]

    def list_schedules(self) -> List[Schedule]:
        """
        List all schedule in database
        :return: List[Schedule]
        """
        with self.conn as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT * FROM schedules WHERE True")
                schedule = cur.fetchall()
        return schedule
