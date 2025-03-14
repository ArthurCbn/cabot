from pathlib import Path
from mutagen.flac import FLAC
from convert import _convert_to_xxx

def apply_key(song: Path) -> str :
    pass

a = Path("test/TEST/AIFF/123.aiff")

_convert_to_xxx(".flac", a)

b = Path("test/TEST/AIFF/123.flac")

song_data = FLAC(b)
print(song_data["isrc"][0])