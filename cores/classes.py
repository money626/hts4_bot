from abc import (
    ABC,
    abstractmethod,
)
from typing import Any

import psycopg2
from discord.ext import commands


class CogBase(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


class DatabaseHandlerBase(ABC):
    @abstractmethod
    def __init__(self, dsn: Any):
        self.conn = psycopg2.connect(dsn)
        if not self.__database_table_exists():
            print(f'Creating {self._table_name}...')
            self.__create_database_table()
            print(f'{self._table_name} created')

    @property
    @abstractmethod
    def _table_name(self):
        pass

    @property
    @abstractmethod
    def _create_table_sql(self):
        pass

    def __database_table_exists(self):
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute(f"""
                    SELECT tablename
                    FROM pg_catalog.pg_tables
                    WHERE schemaname != 'pg_catalog'
                      AND schemaname != 'information_schema'
                      AND tablename = '{self._table_name}';
                """)
                return cur.rowcount > 0

    def __create_database_table(self):
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute(self._create_table_sql)
