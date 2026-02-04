import sys
import shutil
from pathlib import Path
from cabot.update import update_playlists
from cabot.config import (
    initialize_config,
    get_cabot_config_value,
    set_default_config,
    CONFIG_PATH,
    TMP_DOWNLOAD_PATH,
)
from cabot.key import get_and_tag_keys
from queue import Queue
import threading

def main() :
    
    if not CONFIG_PATH.exists() :
        set_default_config()

    initialize_config()

    # Clear the tmp files
    if TMP_DOWNLOAD_PATH.exists() :
        shutil.rmtree(TMP_DOWNLOAD_PATH)

    # User input
    argv = sys.argv
    if len(argv) >= 2 :
        playlists = argv[1:]
    else :
        playlists = None # All playlists
    
    disable_key_analysis = bool(get_cabot_config_value(["disable_key_analysis"]))
    if disable_key_analysis :
        update_playlists(playlists_to_update=playlists)

    else :

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
    
