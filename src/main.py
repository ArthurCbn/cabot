from .features.update import update_playlists
from .features.config import initialize_config

if __name__ == '__main__' :
    initialize_config()
    update_playlists()
