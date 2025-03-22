#! /bin/bash

# python requirements
python -m pip install --upgrade pip
pip install -r requirements.txt

# Initialize streamrip config file
rip config path 

# Fixing streamrip qobuz
QOBUZ_PATH=$(python -c "import streamrip.client.qobuz as qb ; print(qb.__file__)")
cp -f src/streamrip/qobuz.py $QOBUZ_PATH

# Modif of metadata track
META_TRACK_PATH=$(python -c "import streamrip.metadata.track as track ; print(track.__file__)")
cp -f src/streamrip/metadata_track.py $META_TRACK_PATH

# Initialize config
python -c "from src.features.config import set_default_config ; set_default_config()"

# Add the alias to .bashrc (for bash shell users)
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

sed -i '/cabot/d' ~/.bashrc
echo "alias cabot='bash $SCRIPT_DIR/cabot.sh'" >> ~/.bashrc
