import sys
import shutil
from pathlib import Path
from .features.update import update_playlists
from .features.config import (
    initialize_config,
    get_cabot_config_value,
)

if __name__ == '__main__' :

    initialize_config()
    
    # Clear the tmp files
    tmp_folder = Path(get_cabot_config_value(["tmp_folder"]))
    if tmp_folder.exists() :
        shutil.rmtree(tmp_folder)

    argv = sys.argv
    if len(argv) >= 2 :
        playlists = (" ".join(argv[1:])).split(";")[1:]
        update_playlists(playlists)
    else :
        update_playlists()
    
