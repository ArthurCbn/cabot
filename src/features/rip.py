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
from streamrip.client.soundcloud import SoundcloudClient
from streamrip.config import Config
from streamrip.db import Downloads, Database, Dummy
from streamrip.config import DEFAULT_DOWNLOADS_DB_PATH
from .config import (
    get_cabot_config_value,
    TRACKS_NOT_FOUND_PATH,
)
from .convert import convert_to_flac
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from pybalt import download
from mutagen.flac import FLAC
from mutagen.aiff import AIFF


# region ID TAGGER

def tag_track_id_by_track_isrc(
        isrc_to_id_dict: dict[str, str],
        downloads_folder: Path) -> None :
    """
    Only tag FLAC tracks for now.
    """

    assert downloads_folder.is_dir(), f"{downloads_folder} n'existe pas."

    for track in downloads_folder.glob("*.flac") :
        track_data = FLAC(track)

        if "ISRC" in track_data :
        
            track_isrc = str(track_data["ISRC"][0])

            if track_isrc in isrc_to_id_dict :
                track_data["COMMENT"] = isrc_to_id_dict[track_isrc]
                track_data.save()
    
    return


def extract_track_id(song: Path) -> str | None :
    
    assert song.is_file(), f"{song} n'existe pas."

    # FLAC
    if song.suffix == ".flac" :

        song_data = FLAC(song)
        if not "COMMENT" in song_data :
            return None
        
        song_id = str(song_data["COMMENT"][0])
    
    # AIFF
    elif song.suffix == ".aiff" :

        song_data = AIFF(song)
        if not "TXXX:COMMENT" in song_data :
            return None
        
        song_id = str(song_data["TXXX:COMMENT"])

    return song_id

# endregion


# region SPOTIFY

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
        limit: int=25) -> tuple[dict[str, str],
                                list[str],
                                set[str],
                                int,
                                bool] :
    """
    Returns :
        - Found (on Qobuz) ISRC -> Searched ISRC (Spotify) corresponding dict (dict[str, str])
        - Failed tracks (list[str])
        - Memory match (set[str])
        - Next track index to process (int)
        - Is the playlist fully ripped (bool)
    """


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
            callback) -> tuple[int, str, str, str] | None:
        """
        Returns :
            - Track index in the playlist (int)
            - Qobuz's track id (str)
            - Found ISRC (Qobuz) (str)
            - Searched ISRC (Spotify) (str)
        """

        async def __get_track_from_album(
                album_id: str,
                name: str=name,
                client: Client=client) -> tuple[str, str] | None :

            status, tracklist_request = await client._api_request("album/get", {"album_id": album_id})
            assert status == 200

            tracks = tracklist_request["tracks"]["items"]
            track_id_by_name = {track["title"]: (track["id"], track["isrc"]) for track in tracks}

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
                client: Client=client) -> tuple[str, str] | None :
            
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
                    found_isrc = results[0]["isrc"]

                    if found_isrc == isrc :
                        search_status.found += 1
                        return track_idx, results[0]["id"], found_isrc, isrc
            
            # If not conclusive, tries by title - artists
            pages = await client.search("track", f"{name} {' '.join(artists)}", limit=1)
            if len(pages) > 0 :
                results = pages[0]["tracks"]["items"]
                if len(results) > 0 :
                    found_isrc = results[0]["isrc"]

                    if (results[0]["title"] == name) and any(a in results[0]["performers"] for a in artists) :
                        search_status.found += 1
                        return track_idx, results[0]["id"], found_isrc, isrc
            
            # Else, tries by album - artist
            pages = await client.search("album", f"{album} {' '.join(artists)}", limit=1)
            if len(pages) > 0 :
                results = pages[0]["albums"]["items"]
                if len(results) > 0 :

                    if results[0]["title"] == name :

                        res_from_album = await __get_track_from_album(results[0]["id"])
                        if not res_from_album is None :
                            track_id, found_isrc = res_from_album

                            search_status.found += 1
                            return track_idx, track_id, found_isrc, isrc

            # Lastly, trie by artist > album > track
            res_from_artist = await __query_by_artist_album_track()
            if not res_from_artist is None :
                track_id, found_isrc = res_from_artist

                search_status.found += 1
                return track_idx, track_id, found_isrc, isrc

            # Fail
            search_status.failed += 1
            with open(TRACKS_NOT_FOUND_PATH, "+a") as f:
                f.write(f"QOBUZ - '{name}' - {', '.join(artists)}\n")
                
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
        failed_tracks = []

        # Request by batch to prevent overloading API
        next_track = offset
        requested_tracks = 0
        while (requested_tracks < limit) and (next_track < playlist_length) :
            
            item = spotify_playlist["tracks"]["items"][next_track]
            
            title = item["track"]["name"]
            album = item["track"]["album"]["name"]
            artists = [a["name"] for a in item["track"]["artists"]]
            
            if "isrc" in item["track"]["external_ids"] : 
                isrc = item["track"]["external_ids"]["isrc"]

                if not isrc in memory :

                    # Query track in Qobuz
                    requests.append(_make_query(title, album, artists, isrc, next_track, client, s, callback))
                    requested_tracks += 1
                
                else :

                    # Memorized track in the Spotify playlist
                    memory_match |= {isrc}
                    s.found += 1

            else :
                failed_tracks.append(f"QOBUZ - {title} - {', '.join(artists)}")
                s.failed += 1
            
            next_track += 1


        results = await asyncio.gather(*requests)


    # Database
    db = Database(Downloads(DEFAULT_DOWNLOADS_DB_PATH), Dummy())


    # Build qobuz playlist
    memory_id_by_isrc = {}
    pending_tracks = []
    for res in results :
        if not res is None :
            pos, id, found_isrc, searched_isrc = res
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
            memory_id_by_isrc[found_isrc] = searched_isrc

    qobuz_playlist = Playlist(playlist_title, config, client, pending_tracks)
    

    # Rip the playlist
    await qobuz_playlist.rip()


    # Close the session
    await client.session.close()

    
    # Fetch failed tracks
    with open(TRACKS_NOT_FOUND_PATH, "r") as f:
        failed_tracks.extend(f.readlines())
        os.remove(TRACKS_NOT_FOUND_PATH)
    

    return memory_id_by_isrc, failed_tracks, memory_match, next_track, (next_track == playlist_length)

# endregion


# region SOUNDCLOUD

_CACHE_SOUNDCLOUD_PLAYLIST = {}
async def fetch_soundcloud_playlist(url: str) -> dict :

    if url in _CACHE_SOUNDCLOUD_PLAYLIST :
        return _CACHE_SOUNDCLOUD_PLAYLIST[url]

    # Log in to soundcloud client
    config = Config.defaults()
    client = SoundcloudClient(config)

    await client.login()

    # Fetch playlist
    requested_playlist = await client.resolve_url(url)
    full_playlist = await client._get_playlist(requested_playlist["id"])

    # Memoize
    _CACHE_SOUNDCLOUD_PLAYLIST[url] = requested_playlist

    # Close the session
    await client.session.close()

    return full_playlist


async def rip_soundcloud_playlist(
        soundcloud_playlist: dict,
        memory: set[str],
        offset: int,
        limit: int=25) -> tuple[set[str],
                                int,
                                bool] :
    """
    Returns :
        - Memory match (set[str])
        - Next track index to process (int)
        - Is the playlist fully ripped (bool)
    """


    # Fetch config value
    download_folder = Path(get_cabot_config_value(["tmp_folder"]))

    playlist_title = soundcloud_playlist["title"]
    playlist_length = len(soundcloud_playlist["tracks"])

    # Downloads foalder
    downloaded_playlist_folder = download_folder / playlist_title

    if not download_folder.exists() :
        os.mkdir(download_folder)
    if not downloaded_playlist_folder.exists() : 
        os.mkdir(downloaded_playlist_folder)

    memory_match = set()

    print("Downloading from Soundcloud...")

    # Extract URLs and RIP
    memory_id_by_track_name = {}
    tracks_path = []
    next_track = offset
    requested_tracks = 0
    while (requested_tracks < limit) and (next_track < playlist_length) :

        track = soundcloud_playlist["tracks"][next_track]
        track_id = str(track["id"]).split("|")[0] # Trash ID management from Streamrip
        if not track_id in memory :

            path = await download(track["permalink_url"], audioFormat="wav", filenameStyle="nerdy", folder_path=str(downloaded_playlist_folder))
        
            memory_id_by_track_name[path.stem] = track_id
            
            tracks_path.append(path)
            requested_tracks += 1

        else :

            memory_match |= {track_id}
        
        next_track += 1
    
    print("Downloading from Soundcloud...Done.")


    # Convert to FLAC and tag track ID
    for track in tracks_path :
        flac_track = convert_to_flac(track)
        os.remove(track)

        song_data = FLAC(flac_track)
        song_data["COMMENT"] = str(memory_id_by_track_name[track.stem])
        song_data.save()

    return memory_match, next_track, (next_track == playlist_length)

# endregion
