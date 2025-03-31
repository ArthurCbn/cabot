from pathlib import Path
from mutagen.flac import FLAC
import numpy as np
import librosa
import librosa.display


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

# region KEY COMPUTE

class TonalFragment(object):
    """
    Pretty mediocre... only 2/8 when testing it.
    The best solution would still be to access an API, if I manage to find one.
    """

    def __init__(self, waveform, sr, tstart=None, tend=None):
        self.waveform = waveform
        self.sr = sr
        self.tstart = tstart
        self.tend = tend
        
        if self.tstart is not None:
            self.tstart = librosa.time_to_samples(self.tstart, sr=self.sr)
        if self.tend is not None:
            self.tend = librosa.time_to_samples(self.tend, sr=self.sr)
        self.y_segment = self.waveform[self.tstart:self.tend]
        self.chromograph = librosa.feature.chroma_cqt(y=self.y_segment, sr=self.sr, bins_per_octave=24)
        
        # chroma_vals is the amount of each pitch class present in this time interval
        self.chroma_vals = []
        for i in range(12):
            self.chroma_vals.append(np.sum(self.chromograph[i]))
        pitches = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
        # dictionary relating pitch names to the associated intensity in the song
        self.keyfreqs = {pitches[i]: self.chroma_vals[i] for i in range(12)} 
        
        keys = [pitches[i] + ' major' for i in range(12)] + [pitches[i] + ' minor' for i in range(12)]

        # use of the Krumhansl-Schmuckler key-finding algorithm, which compares the chroma
        # data above to typical profiles of major and minor keys:
        maj_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
        min_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

        # finds correlations between the amount of each pitch class in the time interval and the above profiles,
        # starting on each of the 12 pitches. then creates dict of the musical keys (major/minor) to the correlation
        self.min_key_corrs = []
        self.maj_key_corrs = []
        for i in range(12):
            key_test = [self.keyfreqs.get(pitches[(i + m)%12]) for m in range(12)]
            # correlation coefficients (strengths of correlation for each key)
            self.maj_key_corrs.append(round(np.corrcoef(maj_profile, key_test)[1,0], 3))
            self.min_key_corrs.append(round(np.corrcoef(min_profile, key_test)[1,0], 3))

        # names of all major and minor keys
        self.key_dict = {**{keys[i]: self.maj_key_corrs[i] for i in range(12)}, 
                         **{keys[i+12]: self.min_key_corrs[i] for i in range(12)}}
        
        # this attribute represents the key determined by the algorithm
        self.key = max(self.key_dict, key=self.key_dict.get)
        self.bestcorr = max(self.key_dict.values())
        
        # this attribute represents the second-best key determined by the algorithm,
        # if the correlation is close to that of the actual key determined
        self.altkey = None
        self.altbestcorr = None

        for key, corr in self.key_dict.items():
            if corr > self.bestcorr*0.9 and corr != self.bestcorr:
                self.altkey = key
                self.altbestcorr = corr
                

    def get_key(self) -> str :
        return max(self.key_dict, key=self.key_dict.get)


def get_song_key(song: Path) -> str :

    assert song.is_file(), f"{song} n'est pas un fichier."

    y, sr = librosa.load(song)
    y_harmonic, _ = librosa.effects.hpss(y)

    tonal_analysis = TonalFragment(y_harmonic, sr)

    return tonal_analysis.get_key()

# endregion


# region TAG

def write_keys_in_flac(playlist_folder: Path, id_to_key_dict: dict[str, str]) -> None :

    if not playlist_folder.exists() :
        return

    for song_path in playlist_folder.glob("*.flac") :
        song_data = FLAC(song_path)
        song_id = song_data["COMMENT"]

        song_data["INITIALKEY"] = id_to_key_dict[song_id]
        song_data.save()
    
    return

# endregion
