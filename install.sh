#! /bin/bash

# python requirements
python -m pip install --upgrade pip
pip install -r requirements.txt

# Initialize streamrip config file
rip config path 

# Initialize config
python -c "from src.features.config import set_default_config ; set_default_config()"

# Fixing streamrip metadata artist
METADATA_TRACK_PATH=$(python -c "import streamrip.metadata.track as tr ; print(tr.__file__)")
cp -f src/streamrip/track.py $METADATA_TRACK_PATH

# Add the alias to .bashrc (for bash shell users)
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

sed -i '/cabot/d' ~/.bashrc
echo "alias cabot='bash $SCRIPT_DIR/cabot.sh'" >> ~/.bashrc
