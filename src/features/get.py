import subprocess
import os
from .config import get_cabot_config_value

def get_lastfm_playlist(playlist_url: str) -> None :
    
    subprocess.run(["rip", "--quality", "2", "lastfm", playlist_url])

    return


# TODO
def get_soundcloud_playlist(playlist_url: str) -> None :
    pass
