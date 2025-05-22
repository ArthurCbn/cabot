import sys
import shutil
from pathlib import Path
from .features.update import update_playlists
from .features.config import (
    initialize_config,
    get_cabot_config_value,
)
from .features.key import get_and_tag_keys
from queue import Queue
import threading

if __name__ == '__main__' :

    initialize_config()

    # Clear the tmp files
    tmp_folder = Path(get_cabot_config_value(["tmp_folder"]))
    if tmp_folder.exists() :
        shutil.rmtree(tmp_folder)

    # User input
    argv = sys.argv
    if len(argv) >= 2 :
        playlists = (" ".join(argv[1:])).split(";")[1:]
    else :
        playlists = None # All playlists
    
    # Dual thread : key tagging is done parallel to ripping due to the time it takes to scrape data
    # This works as a producer-consumer duo :
    # - The ripping thread produce the queries needed to scrape the keys and the locations of the corresponding files
    # - The key tagging thread process every job sent by the other thread

    # This is a thread-safe queue (allow for communication between the two threads)
    key_tag_queue = Queue()

    ripping_thread = threading.Thread(target=lambda: update_playlists(key_tag_queue=key_tag_queue,
                                                                      playlists_to_update=playlists))
    key_tagging_thread = threading.Thread(target=lambda: get_and_tag_keys(key_tag_queue=key_tag_queue))

    ripping_thread.start()
    key_tagging_thread.start()

    ripping_thread.join()
    key_tagging_thread.join()
    
