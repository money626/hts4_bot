import re
from enum import Enum
from typing import (
    Optional,
    Union,
)

import aiohttp
from bs4 import BeautifulSoup

from config import config

url_regex = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|%[0-9a-fA-F][0-9a-fA-F])+")

session = aiohttp.ClientSession(
    headers={'User-Agent': config.CRAWLER_AGENT})


def clean_sclink(track: str) -> str:
    if track.startswith("https://m."):
        track = track.replace("https://m.", "https://")
    if track.startswith("http://m."):
        track = track.replace("http://m.", "https://")
    return track


async def convert_spotify(url: str) -> str:
    if result := url_regex.search(url):
        if "?si=" in url:
            url = result.group(0) + "&nd=1"

    async with session.get(url) as response:
        page = await response.text()
        soup = BeautifulSoup(page, 'html.parser')

        title = soup.find('title')
        title = title.string
        title = title.replace('- song by', '')
        title = title.replace('| Spotify', '')

        return title


def get_url(content: str) -> Optional[str]:
    if result := url_regex.search(content):
        url = result.group(0)
        return url
    else:
        return None


class Sites(Enum):
    Spotify = "Spotify"
    Spotify_Playlist = "Spotify Playlist"
    YouTube = "YouTube"
    Twitter = "Twitter"
    SoundCloud = "SoundCloud"
    Bandcamp = "Bandcamp"
    Custom = "Custom"
    Unknown = "Unknown"


class PlaylistTypes(Enum):
    Spotify_Playlist = "Spotify Playlist"
    YouTube_Playlist = "YouTube Playlist"
    YouTube_Music_Playlist = "YouTube Music Playlist"
    BandCamp_Playlist = "BandCamp Playlist"
    Unknown = "Unknown"


class Origins(Enum):
    Default = "Default"
    Playlist = "Playlist"


def identify_url(url: Optional[str]) -> Sites:
    if url is None:
        return Sites.Unknown

    if "https://www.youtu" in url or "https://youtu.be" in url or "https://music.youtube" in url:
        return Sites.YouTube

    if "https://open.spotify.com/track" in url:
        return Sites.Spotify

    if "https://open.spotify.com/playlist" in url or "https://open.spotify.com/album" in url:
        return Sites.Spotify_Playlist

    if "bandcamp.com/track/" in url:
        return Sites.Bandcamp

    if "https://twitter.com/" in url:
        return Sites.Twitter

    if url.lower().endswith(config.SUPPORTED_EXTENSIONS):
        return Sites.Custom

    if "soundcloud.com/" in url:
        return Sites.SoundCloud

    # If no match
    return Sites.Unknown


def identify_playlist(url: str) -> Union[Sites, PlaylistTypes]:
    if "https://music.youtube.com" in url and "list=" in url:
        return PlaylistTypes.YouTube_Music_Playlist

    if "list=" in url:
        return PlaylistTypes.YouTube_Playlist

    if "https://open.spotify.com/playlist" in url or "https://open.spotify.com/album" in url:
        return PlaylistTypes.Spotify_Playlist

    if "bandcamp.com/album/" in url:
        return PlaylistTypes.BandCamp_Playlist

    return PlaylistTypes.Unknown
