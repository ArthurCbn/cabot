import sys
from .features.update import update_playlists
from .features.config import initialize_config

if __name__ == '__main__' :

    initialize_config()
    
    argv = sys.argv
    if len(argv) >= 2 :
        playlists = (" ".join(argv[1:])).split(";")[1:]
        update_playlists(playlists)
    else :
        update_playlists()
    
