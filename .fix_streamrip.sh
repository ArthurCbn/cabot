#! /bin/bash

# Fixing streamrip metadata artist
METADATA_TRACK_PATH=$(python -c "import streamrip.metadata.track as tr ; print(tr.__file__)")
cp -f src/streamrip/track.py $METADATA_TRACK_PATH