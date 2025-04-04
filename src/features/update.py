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
    rip_soundcloud_playlist,
    fetch_spotify_playlist,
    fetch_soundcloud_playlist,
    tag_track_id_by_track_isrc,
    extract_track_id,
    build_soundcloud_playlist,
)
from .key import (
    write_keys_in_flac,
)

# region SCAN

def scan_playlist(playlist_path: Path) -> set[str] :
    
    def _remember_song_id(song: Path, memory: set[str]) -> set[str] :

        if song.suffix != ".aiff" :
            return memory
        
        song_id = extract_track_id(song)
        if song_id is None :
            os.remove(song)

        memory |= {song_id}

        return memory
    

    if not playlist_path.is_dir() :
        return set()

    memory = set()
    for song in playlist_path.iterdir() :
        memory = _remember_song_id(song, memory)

    return memory

# endregion


# region CLEAN

def remove_deleted_tracks(
        playlist_path: Path,
        unmatched_tracks: set[str]) -> None :
    
    assert playlist_path.is_dir(), f"{playlist_path} n'est pas un dossier."

    aiff = playlist_path / "AIFF"
    if not aiff.exists() :
        return
    
    for song in aiff.iterdir() :

        song_id = extract_track_id(song)
        if (song_id is None) or (song_id in unmatched_tracks) :

            os.remove(song)
            mp3_track = playlist_path / "MP3" / f"{song.stem}.mp3"
            if mp3_track.exists() :
                os.remove(mp3_track)
    
    return

# endregion


# region UPDATE

def update_one_playlist(
        playlist: str, 
        sources: dict[str, str],
        download_path: Path,
        playlists_folder: Path,
        duplicate_to_mp3: bool) -> None :

    # region |---| Tag and Convert

    def _tag_and_convert(
            found_searched_isrc_dict: dict[str, str],
            playlist_path: Path,
            download_path: Path=download_path,
            duplicate_to_mp3: bool=duplicate_to_mp3) -> None :

        # Check new downloads
        if not download_path.exists() :
            return
        if len(list(download_path.iterdir())) == 0 :
            return
        
        downloaded_playlist = next(download_path.iterdir()) # Goes inside playlist folder

        # Tag the ID in metadata
        tag_track_id_by_track_isrc(found_searched_isrc_dict, downloaded_playlist)

        # Convert
        print("Converting...", end="\r")
        convert_batch_to_aiff(downloaded_playlist, [".flac"], playlist_path / "AIFF")
        if duplicate_to_mp3 :
            # TODO Ensure already existing .aiff as converted in MP3 as well
            convert_batch_to_mp3(downloaded_playlist, [".flac"], playlist_path / "MP3")
        print("Converting...Done.")

        shutil.rmtree(download_path)

        return
    
    # endregion

    # region |---| Init

    print(f"-------------- UPDATING {playlist} --------------")

    # Init playlist folders
    playlist = playlist.replace("/", " ")
    playlist_path = playlists_folder / playlist
    fallback_path = playlist_path / "fallback"
    if not playlist_path.exists() :
        os.mkdir(playlist_path)
        os.mkdir(playlist_path / "AIFF")

        if duplicate_to_mp3 :
            os.mkdir(playlist_path / "MP3")
    
    # Scan already downloaded tracks
    print(f"Scanning downloads...", end="\r")

    memory_success = scan_playlist(playlist_path / "AIFF")
    memory_fallback = set()

    # Scan fallback folder as well
    if fallback_path.is_dir() :
        memory_fallback |= scan_playlist(fallback_path / "AIFF")

    print(f"Scanning downloads...Done.")
    print("")

    # Clear Downloads database
    if Path(DEFAULT_DOWNLOADS_DB_PATH).exists() :
        os.remove(DEFAULT_DOWNLOADS_DB_PATH)

    checked_memory = set()
    failed_tracks = {}
    double_failed = []

    # endregion
    
    # region |---| Ripping

    # Goes through every source given for the playlist
    for source, url in sources.items() :
        
        # Downloads by batch
        found_searched_isrc_dict = {}
        offset = 0
        batch_count = 1
        playlist_fully_downloaded = False

        while not playlist_fully_downloaded :
            
            print(f"PROCESSING BATCH {batch_count} - {source}")

            # region |---|---| Spotify
            if source == "spotify" :

                # Fetch spotify playlist
                spotify_playlist = fetch_spotify_playlist(url)

                # Rip playlist
                loop = asyncio.get_event_loop()
                (batch_found_searched_isrc_dict,
                 batch_failed_tracks, 
                 batch_memory_match, 
                 offset,
                 playlist_fully_downloaded) = loop.run_until_complete(rip_spotify_playlist(spotify_playlist, memory_success, offset))

                found_searched_isrc_dict |= batch_found_searched_isrc_dict
                checked_memory |= batch_memory_match
                failed_tracks |= batch_failed_tracks

                # Analyse it
                # TODO when I find a working API

                # Write key in FLAC metadata
                # write_keys_in_flac(download_path, key_by_id)

            # endregion

            # region |---|---| Soundcloud
            elif source == "soundcloud" :

                loop = asyncio.get_event_loop()
                
                # Fetch Soundcloud playlist 
                soundcloud_playlist = loop.run_until_complete(fetch_soundcloud_playlist(url))

                (batch_failed_tracks,
                 batch_memory_match, 
                 offset,
                 playlist_fully_downloaded) = loop.run_until_complete(rip_soundcloud_playlist(soundcloud_playlist,
                                                                                              memory_success,
                                                                                              offset))

                checked_memory |= batch_memory_match
                double_failed.extend(batch_failed_tracks)

            # endregion

            # Stop progress bar
            _p.live.stop()
            _p.started = False

            _tag_and_convert(found_searched_isrc_dict, playlist_path)
            
            batch_count+=1
            print("")


    # region |---| Failed tracks
    if failed_tracks :

        print("Fetching failed tracks on Soundcloud...", end="\r")
        loop = asyncio.get_event_loop()
        (failed_playlist,
         not_found) = loop.run_until_complete(build_soundcloud_playlist(failed_tracks, playlist))
        
        double_failed.extend(not_found)

        print("Fetching failed tracks on Soundcloud...Done.")
        print("")

        if not fallback_path.exists() :
            os.mkdir(fallback_path)

        # Download by batch
        offset = 0
        playlist_fully_downloaded = False
        batch_count = 1
        while not playlist_fully_downloaded :
            
            print(f"PROCESSING BATCH {batch_count} - fallback to soundcloud")
            loop = asyncio.get_event_loop()
            (batch_double_failed,
             batch_memory_match,
             offset,
             playlist_fully_downloaded) = loop.run_until_complete(rip_soundcloud_playlist(failed_playlist,
                                                                                          memory_fallback,
                                                                                          offset))

            double_failed.extend(batch_double_failed)
            checked_memory |= batch_memory_match

            _tag_and_convert({}, fallback_path)
            
            batch_count += 1
            print("")

    # endregion

    # region |---| Double failed tracks
    if double_failed :
        print("The following tracks could not be downloaded, neither from Qobuz nor from Soundcloud :")
        for t in double_failed :
            print(f"   -> {t}")
        print("")

    # endregion


    # region |---| Clean
    print(f"Cleaning playlist folder...", end="\r")
    remove_deleted_tracks(playlist_path, memory_success - checked_memory)
    if fallback_path.exists() :
        remove_deleted_tracks(fallback_path, memory_fallback - checked_memory)
    print(f"Cleaning playlist folder...Done.")
    
    print("-------------- END --------------")
    print("")

    # endregion

    return 

# endregion

# endregion


# region RUN

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

# endregion
