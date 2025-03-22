import os
import asyncio
from pathlib import Path
import shutil
from .config import (
    get_cabot_config_value,
)
from streamrip.config import DEFAULT_DOWNLOADS_DB_PATH
from streamrip.progress import (
    _p,
)
from .convert import (
    convert_batch_to_aiff,
    convert_batch_to_mp3,
)
from .rip import (
    rip_spotify_playlist,
    get_soundcloud_playlist,
    fetch_spotify_playlist,
)
from .key import (
    write_keys_in_flac,
)
from mutagen.aiff import AIFF
from mutagen.flac import FLAC
from mutagen._iff import EmptyChunk


# TODO : when ripping a track that is not match by its ISRC, return searched ISRC AND found ISRC
# Then after ripping, modify the ISRC metadata field with the original searched ISRC (the one from Spotify)
# Therefore, when updating the playlist, we will keep in memory the Spotify corresponding ISRC of the track, 
# and not delete it by error 
# Maybe write this in the COMMENTS field to not loose the info that we did not find the original track...
# In case someday I developp something to highlight these "uncertain" tracks

def extract_song_id(song: Path) -> str :
    
    assert song.is_file(), f"{song} n'existe pas."

    if song.suffix == ".flac" :
        song_data = FLAC(song)
        song_id = str(song_data["ISRC"][0])
    
    elif song.suffix == ".aiff" :
        song_data = AIFF(song)
        song_id = str(song_data["TXXX:ISRC"])

    return song_id


def scan_playlist(playlist_path: Path) -> set[str] :
    
    def _remember_song_id(song: Path, memory: set[str]) -> set[str] :

        if song.suffix != ".aiff" :
            return memory
        
        song_id = extract_song_id(song)
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

        song_id = extract_song_id(song)
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

    print(f"-------------- UPDATING {playlist} --------------")

    # Init playlist folders
    playlist = playlist.replace("/", " ")
    playlist_path = playlists_folder / playlist
    if not playlist_path.exists() :
        os.mkdir(playlist_path)
        os.mkdir(playlist_path / "AIFF")

        if duplicate_to_mp3 :
            os.mkdir(playlist_path / "MP3")


    # Scan already downloaded tracks
    print(f"Scanning downloads...", end="\r")
    memory = scan_playlist(playlist_path / "AIFF")
    print(f"Scanning downloads...Done.")


    # Clear Downloads database
    if Path(DEFAULT_DOWNLOADS_DB_PATH).exists() :
        os.remove(DEFAULT_DOWNLOADS_DB_PATH)

    checked_memory = set()
    failed_tracks = []

    # Goes through every source given for the playlist
    for source, url in sources.items() :
        
        # Downloads by batch
        offset = 0
        batch_count = 1
        playlist_fully_downloaded = False
        while not playlist_fully_downloaded :
            
            print(f"PROCESSING BATCH {batch_count}")

            if source == "spotify" :

                # Fetch spotify playlist
                spotify_playlist = fetch_spotify_playlist(url)

                # Rip playlist
                loop = asyncio.get_event_loop()
                (batch_failed_tracks, 
                 batch_memory_match, 
                 offset,
                 playlist_fully_downloaded) = loop.run_until_complete(rip_spotify_playlist(spotify_playlist, memory, offset))

                checked_memory |= batch_memory_match
                failed_tracks.extend(batch_failed_tracks)

                # Analyse it
                # TODO when I find a working API

                # Write key in FLAC metadata
                # write_keys_in_flac(download_path, key_by_id)

            # TODO
            elif source == "soundcloud" :
                get_soundcloud_playlist(url) # handle offset and playlist_fully_downloaded


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
                    # TODO Ensure already existing .aiff as converted in MP3 as well
                    convert_batch_to_mp3(downloaded_playlist, [".flac"], playlist_path / "MP3")
                print("Converting...Done.")

                shutil.rmtree(download_path)
            
            batch_count+=1
            print("")


    # Remove deleted tracks
    print(f"Cleaning playlist folder...", end="\r")
    remove_deleted_tracks(playlist_path, memory - checked_memory)
    print(f"Cleaning playlist folder...Done.")
    
    print("-------------- END --------------")
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
