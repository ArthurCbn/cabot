import os
import asyncio
from pathlib import Path
import shutil
from .config import (
    get_cabot_config_value,
)
from streamrip.db import Downloads
from streamrip.config import DEFAULT_DOWNLOADS_DB_PATH
from streamrip.progress import (
    _p,
    ProgressManager,
    clear_progress,
    add_title,
)
from .convert import (
    convert_batch_to_aiff,
    convert_batch_to_mp3,
)
from .rip import (
    rip_spotify_playlist,
    get_soundcloud_playlist,
)
from .key import (
    write_keys_in_flac,
)
from mutagen.aiff import AIFF
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from mutagen._iff import EmptyChunk


def scan_playlist(playlist_path: Path) -> set[str] :
    
    def _remember_song_id(song: Path, memory: set[str]) -> set[str] :

        if song.suffix != ".aiff" :
            return memory
        
        try :
            song_data = AIFF(song)
        except EmptyChunk:
            os.remove(song)
            return memory
        
        song_id = str(song_data["TXXX:COMMENTS"])
        memory |= {song_id}

        return memory
    

    assert playlist_path.is_dir(), f"{playlist_path} n'est pas un dossier existant."

    memory = set()
    for song in playlist_path.iterdir() :
        memory = _remember_song_id(song, memory)

    return memory


def remove_deleted_tracks(
        playlist_path: Path, 
        unmatched_tracks: set[str]) -> None :
    
    assert playlist_path.is_dir(), f"{playlist_path} n'est pas un dossier."

    aiff = playlist_path / "AIFF"

    for song in aiff.iterdir() :

        song_data = AIFF(song)
        song_id = str(song_data["TXXX:COMMENTS"])
        if song_id in unmatched_tracks :

            os.remove(song)
            mp3_track = playlist_path / "MP3" / f"{song.stem}.mp3"
            if mp3_track.exists() :
                os.remove(mp3_track)
    
    return


def update_one_playlist(
        playlist: str, 
        sources: dict[str, str],
        download_path: Path,
        playlists_folder: Path,
        duplicate_to_mp3: bool) -> None :

    # Init playlist folders
    playlist = playlist.replace("/", " ")
    playlist_path = playlists_folder / playlist
    if not playlist_path.exists() :
        os.mkdir(playlist_path)
        os.mkdir(playlist_path / "AIFF")

        if duplicate_to_mp3 :
            os.mkdir(playlist_path / "MP3")


    # Scan already downloaded tracks
    print(f"Scanning {playlist}...", end="\r")
    memory = scan_playlist(playlist_path / "AIFF")
    print(f"{playlist} scanned.   ")

    # Clear Downloads database
    if Path(DEFAULT_DOWNLOADS_DB_PATH).exists() :
        os.remove(DEFAULT_DOWNLOADS_DB_PATH)

    checked_memory = set()

    # Goes through every source given for the playlist
    for source, url in sources.items() :

        if source == "spotify" :

            # Fetch spotify playlist
            print("Fetching Spotify playlist...", end="\r")
            spotify_client_id = get_cabot_config_value(["spotify", "client_id"])
            spotify_client_secret = get_cabot_config_value(["spotify", "client_secret"])
            sp = Spotify(client_credentials_manager=SpotifyClientCredentials(
                client_id=spotify_client_id, 
                client_secret=spotify_client_secret
            ))
            spotify_playlist = sp.playlist(url)
            print("Spotify playlist fetched.   ")


            # Rip playlist
            loop = asyncio.get_event_loop()
            failed_tracks, memory_match = loop.run_until_complete(rip_spotify_playlist(spotify_playlist, memory))

            checked_memory |= memory_match

            # Analyse it
            # TODO when I find a working API

            # Write key in FLAC metadata
            # write_keys_in_flac(download_path, key_by_id)

        # TODO
        elif source == "soundcloud" :
            get_soundcloud_playlist(url)


        # Stop progress bar
        _p.live.stop()
        _p.started = False


        # Failed tracks
        if failed_tracks :
            print("The following tracks do not exist on Qobuz : ")
            for t in failed_tracks :
                print(f"   -> {t.replace("\n", "")}")
            print("")


        # New downloads
        if download_path.exists() and len(list(download_path.iterdir())) > 0 :
            
            downloaded_playlist = next(download_path.iterdir()) # Goes inside playlist folder

            # Convert
            print("Converting...", end="\r")
            convert_batch_to_aiff(downloaded_playlist, [".flac"], playlist_path / "AIFF")
            if duplicate_to_mp3 :
                convert_batch_to_mp3(downloaded_playlist, [".flac"], playlist_path / "MP3")
            print("Converted.   ")

            shutil.rmtree(download_path)


    # Remove deleted tracks
    print(f"Cleaning playlist folder...", end="\r")
    remove_deleted_tracks(playlist_path, memory - memory_match)
    print(f"Playlist folder cleaned.   ")
    print("")

    return 


def update_playlists(playlists_to_update: list[str]|None=None) -> None :

    duplicate_to_mp3 = bool(get_cabot_config_value(["mp3_copy"]))
    download_path = Path(get_cabot_config_value(["tmp_folder"]))
    playlists_folder = Path(get_cabot_config_value(["playlists_folder"]))

    playlists = get_cabot_config_value(["playlists"])

    if not playlists_folder.exists() :
        os.mkdir(playlists_folder)

    playlists_to_update = playlists_to_update or list(playlists.keys())

    for playlist in playlists_to_update :

        assert playlist in playlists, f"{playlist} is not configured, please fill `config.json` correctly."

        sources = playlists[playlist]

        update_one_playlist(playlist,
                            sources,
                            download_path,
                            playlists_folder,
                            duplicate_to_mp3)

    return
