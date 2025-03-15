import os
import asyncio
from pathlib import Path
import shutil
from .config import (
    get_cabot_config_value,
    DOWNLOADS_DB_PATH,
)
from streamrip.db import Downloads
from streamrip.media.playlist import PendingLastfmPlaylist
from .convert import (
    convert_batch_to_aiff,
    convert_batch_to_mp3,
)
from .get import (
    get_spotify_playlist,
    get_soundcloud_playlist,
)
from mutagen.aiff import AIFF


def scan_playlist(playlist_path: Path) -> None :
    
    def _remember_song_id(song: Path, database: Downloads) -> None :
        
        if song.suffix != ".aiff" :
            return

        song_data = AIFF(song)
        song_id = str(song_data["TXXX:COMMENTS"])
        database.add((song_id,))

        return
    

    assert playlist_path.is_dir(), f"{playlist_path} n'est pas un dossier existant."

    # Reset the DB
    if DOWNLOADS_DB_PATH.exists() :
        os.remove(DOWNLOADS_DB_PATH)
    database = Downloads(DOWNLOADS_DB_PATH)
    
    for song in playlist_path.iterdir() :
        _remember_song_id(song, database)

    return


def remove_deleted_tracks(playlist_path: Path) -> None :
    
    assert playlist_path.is_dir(), f"{playlist_path} n'est pas un dossier."

    aiff = playlist_path / "AIFF"
    database = Downloads(DOWNLOADS_DB_PATH)

    for song in aiff.iterdir() :

        song_data = AIFF(song)
        song_id = str(song_data["TXXX:COMMENTS"])
        if database.contains(id=song_id) :

            os.remove(song)
            mp3_track = playlist_path / "MP3" / f"{song.stem}.mp3"
            if mp3_track.exists() :
                os.remove(mp3_track)
    
    return
    

def update_playlists() -> None :

    duplicate_to_mp3 = bool(get_cabot_config_value(["mp3_copy"]))
    download_path = Path(get_cabot_config_value(["tmp_folder"]))
    playlists_folder = Path(get_cabot_config_value(["playlists_folder"]))

    playlists = get_cabot_config_value(["playlists"])

    if not playlists_folder.exists() :
        os.mkdir(playlists_folder)

    for playlist, sources in playlists.items() :
        
        # Init playlist folders
        playlist_path = playlists_folder / playlist
        if not playlist_path.exists() :
            os.mkdir(playlist_path)
            os.mkdir(playlist_path / "AIFF")

            if duplicate_to_mp3 :
                os.mkdir(playlist_path / "MP3")

        # Scan already downloaded tracks
        print(f"Scanning {playlist}...", end="\r")
        scan_playlist(playlist_path / "AIFF")
        print(f"{playlist} scanned.   ")
        
        # Goes through every source given for the playlist
        for source, url in sources.items() :
            
            if source == "spotify" :
                loop = asyncio.new_event_loop()
                loop.run_until_complete(get_spotify_playlist(url))
            elif source == "soundcloud" :
                get_soundcloud_playlist(url)

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
        print(f"Deleting removed tracks...", end="\r")
        remove_deleted_tracks(playlist_path)
        print(f"Removed tracks deleted.   ")


    return
