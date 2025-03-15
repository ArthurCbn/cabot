# Cabot

One command for one feature : updating all your playlists (download in lossless, convert, analyse key) .

## Dependencies

```
ffmpeg
```

## Installation

### Linux - using bash
```
git clone https://ArthurCbn:**key**@github.com/ArthurCbn/cabot.git
cd cabot
bash installation.sh
source ~/.bashrc
```

## Setup

Set-up your playlists' urls directly in `config.json` like so :

```json
{
    "playlists_folder": "your/playlists/folder",
    "mp3_copy": "True",
    "playlists": {
        "your_1st_playlist": {
            "spotify": "url_to_1st_spotify_playlist"
        },
        "your_2nd_playlist": {
            "spotify": "url_to_2nd_spotify_playlist"
        }
    }
}
```

`mp3_copy` is useful if you want to have a copy of every downloaded tracks in mp3 320kbps.


### Qobuz credentials

Set-up your qobuz credentials directly in `config.json` like so :

```json
{
    "qobuz": {
        "email": "your_email",
        "token": "your_token",
        "quality": 2
    }
}
```

Note that `quality: 2` corresponds to CD quality (lossless 44.1kHz).
You are free to configure higher quality (see [streamrip](https://github.com/nathom/streamrip)).

>You might want to check out [this telegram channel](https://t.me/firehawk52official/126460).


### Spotify credentials

You need to get your own Spotify API credentials. This is 100% safe since no ripping is done directly from Spotify.
To do so, go [here](https://developer.spotify.com/) and follow these steps :
1. Log in on your Spotify account
2. Click on your profile (top right corner), then "Dashboard"
3. Click "Create app"
4. Fill in the form with bullshit info (this won't change anything)
   For "Redirects URls", you can enter 'https://example.org/callback'
6. Click "Save"
7. Go to "Settings" on the new 'app' you just created

There you will find your Client ID and Client Secret, you can then copy-paste them into `config.json` :

```json
{
    "spotify": {
        "client_id": "your_client_id",
        "client_secret": "your_client_secret"
    }
}
```

## Usage

Just type `cabot` in your terminal.

## Future features

- Analyse key and automatically add it to the metadata
- Rip from soundcloud
