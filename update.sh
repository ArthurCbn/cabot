#! /bin/bash

# Pull
git reset --hard origin/main

# python requirements
python -m pip install --upgrade pip
pip install -r requirements.txt

# Initialize streamrip config file
rip config path 

# Fix streamrip
bash .fix_streamrip.sh