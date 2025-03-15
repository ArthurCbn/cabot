from pathlib import Path
from mutagen.flac import FLAC


PITCH_CLASS_TO_CAMELOT = {
    ("0", "0"): "5A",
    ("0", "1"): "8B",
    ("1", "0"): "12A",
    ("1", "1"): "3B",
    ("2", "0"): "7A",
    ("2", "1"): "10B",
    ("3", "0"): "2A",
    ("3", "1"): "5B",
    ("4", "0"): "9A",
    ("4", "1"): "12B",
    ("5", "0"): "4A",
    ("5", "1"): "7B",
    ("6", "0"): "11A",
    ("6", "1"): "2B",
    ("7", "0"): "6A",
    ("7", "1"): "9B",
    ("8", "0"): "1A",
    ("8", "1"): "11B",
    ("9", "0"): "8A",
    ("9", "1"): "11B",
    ("10", "0"): "3A",
    ("10", "1"): "6B",
    ("11", "0"): "10A",
    ("11", "1"): "1B",
}


def write_keys_in_flac(playlist_folder: Path, id_to_key_dict: dict[str, str]) -> None :

    if not playlist_folder.exists() :
        return

    for song_path in playlist_folder.glob("*.flac") :
        song_data = FLAC(song_path)
        song_id = song_data["COMMENT"]

        song_data["INITIALKEY"] = id_to_key_dict[song_id]
        song_data.save()
    
    return
