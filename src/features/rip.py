import subprocess
from dataclasses import dataclass
from rich.text import Text
from pathlib import Path
import os
import asyncio
from contextlib import ExitStack
from streamrip.console import console
from streamrip.metadata import SearchResults
from streamrip.media.playlist import Playlist, PendingPlaylistTrack
from streamrip.client import Client
from streamrip.client.qobuz import QobuzClient
from streamrip.config import Config
from streamrip.db import Downloads, Database, Dummy
from .config import get_cabot_config_value, DOWNLOADS_DB_PATH


async def rip_spotify_playlist(spotify_playlist: dict) -> dict[str, str] :
    
    @dataclass(slots=True)
    class Status:
        found: int
        failed: int
        total: int

        def text(self) -> Text:
            return Text.assemble(
                "Searching for last.fm tracks (",
                (f"{self.found} found", "bold green"),
                ", ",
                (f"{self.failed} failed", "bold red"),
                ", ",
                (f"{self.total} total", "bold"),
                ")",
            )


    async def _make_query(
            query: str,
            uri: str,
            client: Client,
            search_status: Status,
            callback) -> tuple[str, str] | None:

        with ExitStack() as stack:

            stack.callback(callback)

            pages = await client.search("track", query, limit=1)
            if len(pages) > 0:
                search_status.found += 1
                return (
                    SearchResults.from_pages(client.source, "track", pages)
                    .results[0]
                    .id
                ), uri

            search_status.failed += 1
            print(f"No result found for {query}")

            return None


    # Fetch config values
    download_folder = Path(get_cabot_config_value(["tmp_folder"]))
    qobuz_email = get_cabot_config_value(["qobuz", "email"])
    qobuz_token = get_cabot_config_value(["qobuz", "token"])
    quality = get_cabot_config_value(["qobuz", "quality"])


    # Log in to qobuz client
    config = Config.defaults()
    config.session.qobuz.email_or_userid = qobuz_email
    config.session.qobuz.password_or_token = qobuz_token
    config.session.qobuz.use_auth_token = True
    config.session.qobuz.quality = quality
    client = QobuzClient(config)

    await client.login()


    # Fetch qobuz ids
    s = Status(0, 0, len(spotify_playlist["tracks"]["items"]))
    with console.status(s.text(), spinner="moon") as status:
        
        def callback():
            status.update(s.text())

        requests = []
        for item in spotify_playlist["tracks"]["items"] :
            title = item["track"]["name"]
            artists = item["track"]["artists"]
            uri = item["track"]["uri"]
            requests.append(_make_query(f"{title} {', '.join(a['name'] for a in artists)}", uri, client, s, callback))
        
        results = await asyncio.gather(*requests)


    # Database
    db = Database(Downloads(DOWNLOADS_DB_PATH), Dummy())


    # Build qobuz playlist
    playlist_title = spotify_playlist["name"]
    id_to_uri_dict = {}
    pending_tracks = []
    for pos, (id, uri) in enumerate(results, start=1) :
        pending_tracks.append(
                PendingPlaylistTrack(
                    id,
                    client,
                    config,
                    download_folder / playlist_title,
                    playlist_title,
                    pos,
                    db,
                ))
        id_to_uri_dict[id] = uri
        
    
    qobuz_playlist = Playlist(playlist_title, config, client, pending_tracks)
    

    # Rip the playlist
    await qobuz_playlist.rip()


    # Close the session
    await client.session.close()

    return id_to_uri_dict


# TODO
def get_soundcloud_playlist(playlist_url: str) -> None :
    pass
