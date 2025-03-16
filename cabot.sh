#! /bin/bash

CWD=$(pwd) 

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
cd $SCRIPT_DIR 

playlists=""
for arg in "$@"; do
    playlists="$playlists;$arg"
done

python -m src.main $playlists

cd $CWD