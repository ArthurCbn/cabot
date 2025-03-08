from pathlib import Path
import json
import toml
from streamrip.config import DEFAULT_CONFIG_PATH
from typing import Any

# region Utils
def get_project_root() -> Path :

    current_directory = Path(__file__).resolve().parent

    while current_directory != current_directory.root :
        if (current_directory / "README.md").exists() :
            return current_directory
        current_directory = current_directory.parent
    
    return FileNotFoundError("Project root not found")


CABOT = get_project_root()
CONFIG_PATH = CABOT / "config.json"
DOWNLOADS_DB_PATH = CABOT / "downloads.db"
CONFIG_CORRESPONDANCE = {
    ("qobuz", "email"): ("qobuz", "email_or_userid"),
    ("qobuz", "token"): ("qobuz", "password_or_token"),
    ("tmp_folder",): ("downloads", "folder")
}

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
    set_streamrip_config_value("database", "downloads_path", str(DOWNLOADS_DB_PATH))

def set_default_config() -> None :
    set_cabot_config_value(["tmp_folder"], str(CABOT / "tmp_download"))
    set_cabot_config_value(["mp3_copy"], "True")
    initialize_config()

# endregion
