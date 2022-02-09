import os
from typing import (
    Any,
    List,
    Literal,
    NoReturn,
    Optional,
    TypedDict,
)

import discord
from discord import (
    Guild,
)

from config import config
from cores.classes import (
    DatabaseHandlerBase,
)

dir_path = os.path.dirname(os.path.realpath(__file__))


class SettingsData(TypedDict):
    guild_id: int
    default_nickname: str
    command_channel: Optional[int]
    start_voice_channel: Optional[int]
    user_must_be_in_vc: bool
    button_emote: str
    default_volume: float
    vc_timeout: bool


SettingsFields = Literal[
    "guild_id",
    "default_nickname",
    "command_channel",
    "start_voice_channel",
    "user_must_be_in_vc",
    "button_emote",
    "default_volume",
    "vc_timeout"
]
default_settings = {
    "default_nickname": "",
    "command_channel": None,
    "start_voice_channel": None,
    "user_must_be_in_vc": True,
    "button_emote": "",
    "default_volume": 100,
    "vc_timeout": config.VC_TIMOUT_DEFAULT
}


class Settings(object):
    def __init__(self, guild: Guild, data: Optional[SettingsData] = None):
        self.guild: Guild = guild
        self.config: SettingsData = data or SettingsData(guild_id=guild.id, **default_settings)

    async def update_setting(self, setting: str, value: str) -> NoReturn:
        try:
            await self.process_setting(setting, value)
        except ValueError as e:
            raise e

    def upgrade(self):
        keys: List[SettingsFields] = list(SettingsFields)
        for key in keys:
            if key not in self.config.keys():
                self.config[key] = default_settings.get(key)

    def get(self, setting: SettingsFields):
        return self.config[setting]

    async def format(self):
        embed = discord.Embed(
            title="Settings", description=self.guild.name, color=config.EMBED_COLOR)

        embed.set_thumbnail(url=self.guild.icon.url)
        embed.set_footer(text=f"Usage: {config.BOT_PREFIX}set setting_name value")

        exclusion_keys: List[SettingsFields] = ['guild_id']
        keys: List[SettingsFields] = list(SettingsFields)
        for key in keys:
            if key in exclusion_keys:
                continue

            if self.config[key] == "" or self.config[key] is None:
                embed.add_field(name=key, value="Not Set", inline=False)
                continue

            elif key == "start_voice_channel":
                if self.config[key]:
                    for vc in self.guild.voice_channels:
                        if vc.id == self.config[key]:
                            embed.add_field(name=key, value=vc.name, inline=False)
                    else:
                        embed.add_field(name=key, value="Invalid VChannel", inline=False)
                    continue

            elif key == "command_channel":
                if self.config[key]:
                    for chan in self.guild.text_channels:
                        if chan.id == self.config[key]:
                            embed.add_field(name=key, value=chan.name, inline=False)
                    else:
                        embed.add_field(name=key, value="Invalid Channel", inline=False)
                    continue

            embed.add_field(name=key, value=self.config[key], inline=False)

        return embed

    async def process_setting(self, setting: str, value: str) -> NoReturn:
        switcher = {
            'default_nickname': lambda: self.set_default_nickname(value),
            'command_channel': lambda: self.set_command_channel(value),
            'start_voice_channel': lambda: self.set_start_voice_channel(value),
            'user_must_be_in_vc': lambda: self.set_user_must_be_in_vc(value),
            'button_emote': lambda: self.set_button_emote(value),
            'default_volume': lambda: self.set_default_volume(value),
            'vc_timeout': lambda: self.set_vc_timeout(value),
        }
        setter = switcher.get(setting)

        if setter is None:
            raise ValueError("`Error: Setting not found`")
        await setter()

    # -----setting methods-----
    async def set_default_nickname(self, value: str) -> NoReturn:
        if value.lower() == "unset":
            self.config['default_nickname'] = ""

        if len(value) > 32:
            raise ValueError((
                "`Error: Nickname exceeds character limit`"
                f"Usage: {config.BOT_PREFIX}set 'default_nickname nickname"
                "Other options: unset")
            )
        self.config['default_nickname'] = value
        await self.guild.me.edit(nick=value)

    async def set_command_channel(self, value: str) -> NoReturn:
        if value.lower() == "unset":
            self.config['command_channel'] = None
            return

        for chan in self.guild.text_channels:
            if chan.name.lower() == value.lower():
                self.config['command_channel'] = chan.id
        else:
            raise ValueError((
                "`Error: Channel name not found`"
                f"Usage: {config.BOT_PREFIX}set command_channel channel_name"
                f"Other options: unset"
            ))

    async def set_start_voice_channel(self, value: str) -> NoReturn:
        if value.lower() == "unset":
            self.config['start_voice_channel'] = None
            return

        for vc in self.guild.voice_channels:
            if vc.name.lower() == value.lower():
                self.config['start_voice_channel'] = vc.id
                self.config['vc_timeout'] = False
                break
        else:
            raise ValueError(
                "`Error: Voice channel name not found`\n"
                f"Usage: {config.BOT_PREFIX}set start_voice_channel voice_channel_name\n"
                "Other options: unset"
            )

    async def set_user_must_be_in_vc(self, value: str) -> NoReturn:
        if value.lower() == "true":
            self.config['user_must_be_in_vc'] = True
        elif value.lower() == "false":
            self.config['user_must_be_in_vc'] = False
        else:
            raise ValueError(
                "`Error: Value must be True/False`\n"
                f"Usage: {config.BOT_PREFIX}set user_must_be_in_vc True/False"
            )

    async def set_button_emote(self, value: str) -> NoReturn:
        if value.lower() == "unset":
            self.config['button_emote'] = ""
            return

        emoji = discord.utils.get(self.guild.emojis, name=value)
        if emoji is None:
            raise ValueError(
                "`Error: Emote name not found on server`\n"
                f"Usage: {config.BOT_PREFIX}set button_remote emote_name\n"
                "Other options: unset"
            )
        self.config['button_emote'] = value

    async def set_default_volume(self, value: str) -> NoReturn:
        try:
            value = int(value)
            if value > 100 or value < 0:
                raise ValueError
        except ValueError:
            raise ValueError((
                "`Error: Value must be a number`"
                f"Usage: {config.BOT_PREFIX}set default_volume 0-100"
            ))
        self.config['default_volume'] = value

    async def set_vc_timeout(self, value: str) -> NoReturn:
        if not config.ALLOW_VC_TIMEOUT_EDIT:
            raise ValueError("`Error: This value cannot be modified`")

        if value.lower() == "true":
            self.config['vc_timeout'] = True
            self.config['start_voice_channel'] = None
            return
        if value.lower() == "false":
            self.config['vc_timeout'] = False
            return

        raise ValueError((
            "`Error: Value must be True/False`"
            f"Usage: {config.BOT_PREFIX}set vc_timeout True/False"
        ))


class MusicSettingsDatabaseHandler(DatabaseHandlerBase):
    _table_name = 'music_settings'
    _create_table_sql = """
        CREATE TABLE music_settings (
            guild_id bigint PRIMARY KEY ,
            default_nickname char(32) not null,
            command_channel  int null,
            start_voice_channel int null,
            user_must_be_in_vc bool not null,
            button_emote char(32) not null,
            default_volume smallint not null,
            vc_timeout bool not null
        );"""

    def __init__(self, dsn: Any):
        super(MusicSettingsDatabaseHandler, self).__init__(dsn)

    def save_settings(self, settings: SettingsData):
        with self.conn:
            with self.conn.cursor() as cur:
                sql = """
                    INSERT INTO music_settings
                    (guild_id, default_nickname, command_channel, start_voice_channel,
                    user_must_be_in_vc, button_emote, default_volume, vc_timeout)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (guild_id) DO UPDATE
                    SET default_nickname = excluded.default_nickname,
                        command_channel = excluded.command_channel,
                        start_voice_channel = excluded.start_voice_channel,
                        user_must_be_in_vc = excluded.user_must_be_in_vc,
                        button_emote = excluded.button_emote,
                        default_volume = excluded.default_volume,
                        vc_timeout = excluded.vc_timeout;"""
                cur.execute(
                    sql, (
                        settings['guild_id'],
                        settings['default_nickname'],
                        settings['command_channel'],
                        settings['start_voice_channel'],
                        settings['user_must_be_in_vc'],
                        settings['button_emote'],
                        settings['default_volume'],
                        settings['vc_timeout'],
                    )
                )

    def get_settings(self, guild_id: int) -> Optional[SettingsData]:
        with self.conn.cursor() as cur:
            cur.execute("""
            SELECT guild_id, default_nickname, command_channel, start_voice_channel,
                    user_must_be_in_vc, button_emote, default_volume, vc_timeout
            FROM music_settings
            WHERE guild_id = %s;
        """, (guild_id,))
            s = cur.fetchone()
            if s is None:
                return None
            return SettingsData(
                guild_id=s[0],
                default_nickname=s[1],
                command_channel=s[2],
                start_voice_channel=s[3],
                user_must_be_in_vc=s[4],
                button_emote=s[5],
                default_volume=s[6],
                vc_timeout=s[7]
            )
