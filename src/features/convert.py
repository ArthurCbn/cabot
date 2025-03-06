from ffmpeg import FFmpeg
from pathlib import Path
import os


# region Generic

def _convert_to_xxx(
        format: str,
        input_path: Path,
        output_folder: Path|None=None) -> Path :

    assert input_path.is_file(), f"{input_path} n'est pas un fichier existant."

    file_name = input_path.stem

    if output_folder :
        output_path = output_folder / f"{file_name}{format}"

        if not output_folder.is_dir() :
            os.mkdir(output_folder)
            
    else :
        output_path = input_path.parent / f"{file_name}{format}"

    ffmpeg = FFmpeg().input(input_path).output(output_path, {"write_id3v2": 1})
    
    ffmpeg.execute()
    
    return output_path 


def _convert_batch_to_xxx(
        format: str,
        input_folder: Path,
        target_formats: list[str],
        output_folder: Path|None=None) -> list[Path] :

    assert input_folder.is_dir(), f"{input_folder} n'est pas un dossier existant."

    handled_files = []
    for file in input_folder.iterdir() :

        if any(file.suffix == s for s in target_formats) :
            handled_files.append(_convert_to_xxx(format, file, output_folder))
    
    return handled_files

# endregion

# region Specific

# region |---| AIFF
def convert_to_aiff(
        input_path: Path, 
        output_folder: Path|None=None) -> Path :

    return _convert_to_xxx(".aiff", input_path, output_folder)


def convert_batch_to_aiff(
        input_folder: Path,
        target_formats: list[str],
        output_folder: Path|None=None) -> list[Path] :

    return _convert_batch_to_xxx(".aiff", input_folder, target_formats, output_folder)

# endregion 

# region |---| MP3
def convert_to_mp3(
        input_path: Path, 
        output_folder: Path|None=None) -> Path :

    return _convert_to_xxx(".mp3", input_path, output_folder)


def convert_batch_to_mp3(
        input_folder: Path,
        target_formats: list[str],
        output_folder: Path|None=None) -> list[Path] :

    return _convert_batch_to_xxx(".mp3", input_folder, target_formats, output_folder)

# endregion 

# endregion
