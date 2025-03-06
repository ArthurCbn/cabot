import os
from pathlib import Path
from pydub import AudioSegment
from tinytag import TinyTag
import numpy as np


from path import CABOT
from src.features.convert import (
    _convert_to_xxx,
    _convert_batch_to_xxx,
)

# region Utils

# Paths
DUMMY_FOLDER_PATH = CABOT / "test" / "dummy_audio"
WHITE_NOISE_ABSOLUTE_PATH = DUMMY_FOLDER_PATH / "white_noise.wav"


def clear_test_directory(directory: Path) -> None :

    for f in directory.iterdir() :

        if f.is_file() and f.resolve() != WHITE_NOISE_ABSOLUTE_PATH :
            os.remove(f)
        
        if f.is_dir() :
            clear_test_directory(f)
            os.rmdir(f)


def check_audio_equality(audio1_path: Path, audio2_path: Path) -> bool :

    # Raw data
    audio1 = AudioSegment.from_file(audio1_path)
    audio2 = AudioSegment.from_file(audio2_path)

    audio1_raw = np.array(audio1.get_array_of_samples())
    audio2_raw = np.array(audio2.get_array_of_samples())

    if not np.array_equal(audio1_raw, audio2_raw) :
        return False

    # Metadata
    audio1_metadata = TinyTag.get(audio1_path)
    audio2_metadata = TinyTag.get(audio2_path)

    if audio1_metadata.artist != audio2_metadata.artist :
        return False
    if audio1_metadata.album != audio2_metadata.album :
        return False
    if audio1_metadata.year != audio2_metadata.year :
        return False
    if audio1_metadata.comment != audio2_metadata.comment :
        return False
    if audio1_metadata.composer != audio2_metadata.composer :
        return False
    if audio1_metadata.genre != audio2_metadata.genre :
        return False

    return True

# endregion


def test_convert() :

    copied_folder = DUMMY_FOLDER_PATH / "copied"

    aiff_path = _convert_to_xxx(".aiff", WHITE_NOISE_ABSOLUTE_PATH, copied_folder)
    _ = _convert_to_xxx(".mp3", WHITE_NOISE_ABSOLUTE_PATH, copied_folder)
    reverse_path = _convert_to_xxx(".wav", aiff_path, copied_folder)

    
    try :
        assert aiff_path.is_file()
        assert reverse_path.is_file()
        assert check_audio_equality(WHITE_NOISE_ABSOLUTE_PATH, reverse_path)
    
    # Clean before killing process
    except AssertionError as e :
        clear_test_directory(DUMMY_FOLDER_PATH)
        raise e

    clear_test_directory(DUMMY_FOLDER_PATH)
