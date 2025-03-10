import os
import asyncio
from pathlib import Path
from .config import (
    get_cabot_config_value,
    DOWNLOADS_DB_PATH,
)
from streamrip.db import Downloads
from streamrip.client.qobuz import QobuzClient
from streamrip.config import Config
from tinytag import TinyTag
from .convert import (
    convert_batch_to_aiff,
    convert_batch_to_mp3,
)
from .get import (
    get_lastfm_playlist,
    get_soundcloud_playlist,
)

async def scan_playlist(playlist_path: Path) -> None :
    
    async def _remember_song_id(song: Path, client: QobuzClient, database: Downloads) -> None :
        
        if song.suffix != ".aiff" :
            return

        song_data = TinyTag.get(song)
        song_key = f"{song_data.title} {song_data.artist}"
        
        res = await client.search("track", song_key, limit=1)
        
        # First pages > tracks > items > first item
        song_id = res[0]["tracks"]["items"][0]["id"]
        
        database.add((song_id,))

        return
    

    assert playlist_path.is_dir(), f"{playlist_path} n'est pas un dossier existant."

    # Reset the DB
    if DOWNLOADS_DB_PATH.exists() :
        os.remove(DOWNLOADS_DB_PATH)
    database = Downloads(DOWNLOADS_DB_PATH)
    
    # Login
    email = get_cabot_config_value(["qobuz", "email"])
    token = get_cabot_config_value(["qobuz", "token"])

    config = Config.defaults()
    config.session.qobuz.use_auth_token = True
    config.session.qobuz.email_or_userid = email
    config.session.qobuz.password_or_token = token
    client = QobuzClient(config)

    await client.login()
    
    # Fetch all metadata in parallel
    tasks = [_remember_song_id(song, client, database) for song in playlist_path.iterdir()]
    await asyncio.gather(*tasks)

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
        
        loop = asyncio.new_event_loop()
        loop.run_until_complete(scan_playlist(playlist_path / "AIFF"))
        
        print(f"{playlist} scanned.")
        print(f"Initiating download...")
        
        # Goes through every source given for the playlist (only implemented lastfm and SoundCloud)
        for source, url in sources.items() :

            if source == "lastfm" :
                get_lastfm_playlist(url)
            elif source == "soundcloud" :
                get_soundcloud_playlist(url)

            # No new downloads
            if len(list(download_path.iterdir())) == 0 :
                return
            downloaded_playlist = next(download_path.iterdir()) # Goes inside playlist folder
 
            # Convert
            convert_batch_to_aiff(downloaded_playlist, [".flac"], playlist_path / "AIFF")
            if duplicate_to_mp3 :
                convert_batch_to_mp3(downloaded_playlist, [".flac"], playlist_path / "MP3")
            
            for file in downloaded_playlist.iterdir() :
                os.remove(file)
            os.rmdir(downloaded_playlist)
    
    return

update_playlists()