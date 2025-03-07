from pathlib import Path
import json

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

# endregion

def get_config_value(key: str) -> str :

    with open(CONFIG_PATH, 'r') as f :
        config_data = json.load(f)
    
    assert key in config_data, f"{key} n'est pas configuré : cabot config -{key} 'value'"

    return config_data[key]


def set_config_value(key: str, value: str) -> None :

    with open(CONFIG_PATH, 'r') as f :
        config_data = json.load(f)
    
    config_data[key] = value
    
    with open(CONFIG_PATH, 'w') as f :
        json.dump(config_data, f, indent=4)
    
    return

