import sys
from pathlib import Path

def get_project_root() -> Path :

    current_directory = Path(__file__).resolve().parent

    while current_directory != current_directory.root :
        if (current_directory / "README.md").exists() :
            return current_directory
        current_directory = current_directory.parent
    
    return FileNotFoundError("Project root not found")


CABOT = get_project_root()
sys.path.insert(0, str(CABOT))
