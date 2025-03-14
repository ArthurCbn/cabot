#! /bin/bash

# python requirements
python -m pip install --upgrade pip
pip install -r requirements.txt

# Fixing streamrip qobuz
QOBUZ_PATH=$(python -c "import streamrip.client.qobuz as qb ; print(qb.__file__)")
cp -f src/streamrip/qobuz.py $QOBUZ_PATH

# Modif of tagger
TAGGER_PATH=$(python -c "import streamrip.metadata.tagger as tagger ; print(tagger.__file__)")
cp -f src/streamrip/tagger.py $TAGGER_PATH

# Modif of tagger
PLAYLIST_PATH=$(python -c "import streamrip.media.playlist as playlist ; print(playlist.__file__)")
cp -f src/streamrip/playlist.py $PLAYLIST_PATH

# Modif of tagger
TRACK_PATH=$(python -c "import streamrip.media.track as track ; print(track.__file__)")
cp -f src/streamrip/track.py $TRACK_PATH

# Initialize config
python -c "from src.features.config import set_default_config ; set_default_config()"

# Add the alias to .bashrc (for bash shell users)
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
CABOT_COMMAND="CWD=\$(pwd) ; cd $SCRIPT_DIR && python -m src.main && cd \$CWD"

sed -i '/cabot/d' ~/.bashrc
echo "alias cabot='$CABOT_COMMAND'" >> ~/.bashrc
