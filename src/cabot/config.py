import shutil
from pathlib import Path
import json
import toml
from streamrip.config import DEFAULT_CONFIG_PATH
from typing import Any
from importlib import resources

# region Utils

APP_NAME = "cabot"
APP_AUTHOR = "ArthurCabon"

CONFIG_DIR_PATH = Path("/app/.config")
CONFIG_DIR_PATH.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = CONFIG_DIR_PATH / "config.json"
CONFIG_CORRESPONDANCE = {
    ("qobuz", "email"): ("qobuz", "email_or_userid"),
    ("qobuz", "token"): ("qobuz", "password_or_token")
}

TMP_DOWNLOAD_PATH = Path("/app/cache/tmp_download")
CONFIG_DIR_PATH.mkdir(parents=True, exist_ok=True)

PLAYLISTS_PATH = Path("/app/data")

# endregion


# region Cabot
def get_cabot_config_value(keys: list[str]) -> Any :

    with open(CONFIG_PATH, 'r') as f :
        config_data = json.load(f)
    
    tmp_dict_or_value = config_data
    for key in keys :
        assert isinstance(tmp_dict_or_value, dict)
        assert key in tmp_dict_or_value
        tmp_dict_or_value = tmp_dict_or_value[key]

    return tmp_dict_or_value


def set_cabot_config_value(keys: list[str], value: str) -> None :

    with open(CONFIG_PATH, 'r') as f :
        config_data = json.load(f)
    
    tmp_dict = config_data

    for key in keys[:-1] :
        if key not in tmp_dict :
            tmp_dict[key] = {}
        tmp_dict = tmp_dict[key]
    
    tmp_dict[keys[-1]] = value

    with open(CONFIG_PATH, 'w') as f :
        json.dump(config_data, f, indent=4)
    
    return

# endregion

# region streamrip
def set_streamrip_config_value(region: str, key: str, value: str) -> None :

    config_data = toml.load(DEFAULT_CONFIG_PATH)
    
    if region not in config_data :
        config_data[region] = {}
    config_data[region][key] = value
    
    with open(DEFAULT_CONFIG_PATH, 'w') as f :
        toml.dump(config_data, f)
    
    return


def apply_cabot_config_to_streamrip() -> None :

    for cabot_keys, (rip_region, rip_key) in CONFIG_CORRESPONDANCE.items() :
        value = get_cabot_config_value(cabot_keys)
        set_streamrip_config_value(rip_region, rip_key, value)

    return

# endregion 


# region default

def initialize_config() -> None :
    apply_cabot_config_to_streamrip()
    set_streamrip_config_value("qobuz", "use_auth_token", "true")
    set_streamrip_config_value("downloads", "folder", str(TMP_DOWNLOAD_PATH))

def set_default_config() -> None :

    with resources.as_file(resources.files("cabot.data") / "default_config.json") as default_config_path:
        shutil.copy(default_config_path, CONFIG_PATH)

    set_cabot_config_value(["mp3_copy"], True)
    set_cabot_config_value(["disable_key_analysis"], False)

# endregion
