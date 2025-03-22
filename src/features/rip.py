import subprocess
from dataclasses import dataclass
from rich.text import Text
from pathlib import Path
import re
import os
import asyncio
from contextlib import ExitStack
from streamrip.console import console
from streamrip.media.playlist import Playlist, PendingPlaylistTrack
from streamrip.client import Client
from streamrip.client.qobuz import QobuzClient
from streamrip.config import Config
from streamrip.db import Downloads, Database, Dummy
from streamrip.config import DEFAULT_DOWNLOADS_DB_PATH
from .config import (
    get_cabot_config_value,
    TRACKS_NOT_FOUND_PATH,
)
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials


_CACHE_SPOTIFY_PLAYLIST = {}
def fetch_spotify_playlist(url: str) -> dict :

    if url in _CACHE_SPOTIFY_PLAYLIST :
        return _CACHE_SPOTIFY_PLAYLIST[url]

    # Login
    spotify_client_id = get_cabot_config_value(["spotify", "client_id"])
    spotify_client_secret = get_cabot_config_value(["spotify", "client_secret"])
    sp = Spotify(client_credentials_manager=SpotifyClientCredentials(
        client_id=spotify_client_id, 
        client_secret=spotify_client_secret
    ))

    # Fetch
    spotify_playlist = sp.playlist(url)

    # Memoize
    _CACHE_SPOTIFY_PLAYLIST[url] = spotify_playlist


    return spotify_playlist


async def rip_spotify_playlist(
        spotify_playlist: dict,
        memory: set[str],
        offset: int,
        limit: int=25) -> tuple[list[str],
                                set[str],
                                int,
                                bool] :
    
    @dataclass(slots=True)
    class Status:
        found: int
        failed: int
        total: int

        def text(self) -> Text:
            return Text.assemble(
                "Searching for Spotify tracks (",
                (f"{self.found} found", "bold green"),
                ", ",
                (f"{self.failed} failed", "bold red"),
                ", ",
                (f"{self.total} total", "bold"),
                ")",
            )


    async def _make_query(
            name: str,
            album: str,
            artists: list[str],
            isrc: str,
            track_idx: int,
            client: Client,
            search_status: Status,
            callback) -> tuple[int, str] | None:

        async def __get_track_from_album(
                album_id: str,
                name: str=name,
                client: Client=client) -> str | None :

            status, tracklist_request = await client._api_request("album/get", {"album_id": album_id})
            assert status == 200

            tracks = tracklist_request["tracks"]["items"]
            track_id_by_name = {track["title"]: track["id"] for track in tracks}

            if name in track_id_by_name :
                return track_id_by_name[name]

            # Remove the (feat. ...)
            track_id_by_name = {re.sub(r"\(feat.[a-zA-Z0-9 ]*\)", "", name): id for name, id in track_id_by_name.items()}
            if name in track_id_by_name :
                return track_id_by_name[name]

            return None


        async def __query_by_artist_album_track(
                name: str=name,
                album: str=album,
                artist: str=artists[0],
                client: Client=client) -> str | None :
            
            #
            # Query artist
            #
            status, artist_request = await client._api_request("artist/search", {"query": artist, "limit": 1})
            assert status == 200

            results = artist_request["artists"]["items"]
            if len(results) == 0 :
                return None
            
            artist_id = results[0]["id"]

            #
            # Fetch artist discography
            #
            status, albums_request = await client._api_request("artist/page", {"artist_id": artist_id})
            assert status == 200

            albums = []
            releases_by_types = albums_request["releases"]
            for releases in releases_by_types :
                if releases["type"] == "album" :
                    albums = releases["items"]
                    break
            
            if len(albums) == 0 :
                return None
            
            #
            # Select album
            #
            album_id = None
            album_id_by_name = {album["title"]: album["id"] for album in albums}

            # Full album name match
            if album in album_id_by_name :
                album_id = album_id_by_name[album]
            else :

                # Album name + (Extended) for instance
                for potential_album, album_id in album_id_by_name.items() :
                    if album in potential_album :
                        break
                else :

                    # Album name without potential extensions
                    for potential_album, album_id in album_id_by_name.items() :
                        if potential_album in album :
                            break
            
            if album_id is None :
                return None
    

            #
            # Select track
            #
            return await __get_track_from_album(album_id)


        with ExitStack() as stack:

            stack.callback(callback)

            # Search by ISRC first
            pages = await client.search("track", isrc, limit=1)
            if len(pages) > 0:
                
                results = pages[0]["tracks"]["items"]
                if len(results) > 0 :

                    if results[0]["isrc"] == isrc :
                        search_status.found += 1
                        return track_idx, results[0]["id"]
            
            # If not conclusive, tries by title - artists
            pages = await client.search("track", f"{name} {' '.join(artists)}", limit=1)
            if len(pages) > 0 :
                results = pages[0]["tracks"]["items"]
                if len(results) > 0 :

                    if (results[0]["title"] == name) and any(a in results[0]["performers"] for a in artists) :
                        search_status.found += 1
                        return track_idx, results[0]["id"]
            
            # Else, tries by album - artist
            pages = await client.search("album", f"{album} {' '.join(artists)}", limit=1)
            if len(pages) > 0 :
                results = pages[0]["albums"]["items"]
                if len(results) > 0 :

                    if results[0]["title"] == name :
                        track_id = await __get_track_from_album(results[0]["id"])
                        if not track_id is None :
                            search_status.found += 1
                            return track_idx, track_id

            # Lastly, trie by artist > album > track
            track_id = await __query_by_artist_album_track()
            if not track_id is None :
                search_status.found += 1
                return track_idx, track_id

            # Fail
            search_status.failed += 1
            with open(TRACKS_NOT_FOUND_PATH, "+a") as f:
                f.write(f"'{name}' - {', '.join(artists)}\n")
                
            return None


    # Fetch config values
    download_folder = Path(get_cabot_config_value(["tmp_folder"]))
    qobuz_email = get_cabot_config_value(["qobuz", "email"])
    qobuz_token = get_cabot_config_value(["qobuz", "token"])
    quality = get_cabot_config_value(["qobuz", "quality"])

    playlist_title = spotify_playlist["name"]
    playlist_length = len(spotify_playlist["tracks"]["items"])

    # Log in to qobuz client
    config = Config.defaults()
    config.session.qobuz.email_or_userid = qobuz_email
    config.session.qobuz.password_or_token = qobuz_token
    config.session.qobuz.use_auth_token = True
    config.session.qobuz.quality = quality
    client = QobuzClient(config)

    await client.login()


    # Fetch qobuz ids
    with open(TRACKS_NOT_FOUND_PATH, "w") as f:
        f.write("")

    s = Status(0, 0, playlist_length)
    with console.status(s.text(), spinner="moon") as status:
        
        def callback():
            status.update(s.text())

        requests = []
        memory_match = set()


        # Request by batch to prevent overloading API
        next_track = offset
        requested_tracks = 0
        while (requested_tracks < limit) and (next_track < playlist_length) :
            
            item = spotify_playlist["tracks"]["items"][next_track]
            
            title = item["track"]["name"]
            album = item["track"]["album"]["name"]
            artists = [a["name"] for a in item["track"]["artists"]]
            isrc = item["track"]["external_ids"]["isrc"]

            if not isrc in memory : # find universal id...

                # Query track in Qobuz
                requests.append(_make_query(title, album, artists, isrc, next_track, client, s, callback))
                requested_tracks += 1
            
            else :

                # Memorized track in the Spotify playlist
                memory_match |= {isrc}
                s.found += 1
            
            next_track += 1


        results = await asyncio.gather(*requests)


    # Database
    db = Database(Downloads(DEFAULT_DOWNLOADS_DB_PATH), Dummy())


    # Build qobuz playlist
    pending_tracks = []
    for res in results :
        if not res is None :
            pos, id = res
            pending_tracks.append(
                    PendingPlaylistTrack(
                        id,
                        client,
                        config,
                        download_folder / playlist_title.replace("/", " "),
                        playlist_title,
                        pos+1,
                        db,
                    ))

    qobuz_playlist = Playlist(playlist_title, config, client, pending_tracks)
    

    # Rip the playlist
    await qobuz_playlist.rip()


    # Close the session
    await client.session.close()

    
    # Fetch failed tracks
    with open(TRACKS_NOT_FOUND_PATH, "r") as f:
        failed_tracks = f.readlines()
        os.remove(TRACKS_NOT_FOUND_PATH)
    

    return failed_tracks, memory_match, next_track, (next_track == playlist_length)



# TODO
def get_soundcloud_playlist(playlist_url: str) -> None :
    pass
