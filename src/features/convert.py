from ffmpeg import FFmpeg
from pathlib import Path
import os
from mutagen.flac import FLAC


def sanitize_metadata(song: Path) -> None :

    assert song.is_file(), f"{song} n'existe pas."

    if song.suffix == ".flac" :

        mutagen_audio = FLAC(song)

        for k, l in mutagen_audio.items().copy() :
            mutagen_audio[k.upper()] = [v.encode("latin-1", errors="ignore").decode("latin-1", errors="replace")
                                        for v in l]
        
        # 'description' metadata field is causing a tone of issues and is useless anyway
        if "description" in mutagen_audio :
            mutagen_audio["DESCRIPTION"] = ""
        
        mutagen_audio.save()
    
    return


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

    if output_path.exists() :
        os.remove(output_path)
    
    # Only sanitize FLAC for now, can easily add support for more format if necessary
    sanitize_metadata(input_path)
    
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
