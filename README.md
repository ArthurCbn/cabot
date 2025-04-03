# Cabot

One command for one feature : updating all your playlists from Spotify and SoundCloud (download in lossless, convert, ~analyse key~).
This keeps your downloaded tracks up-tp-date with your Spotify and Soundcloud playlists so that :
- If you add a track to your Spotify or Soundcloud playlist, it will be downloaded and added to the right folder,
- If you remove a track, it will also removed from your downloaded tracks.

Cabot first tries to download **from Qobuz in lossless quality**, if the track doesn't exist there, it will search for it on Soundcloud.
Tracks that are downloaded from Soundcloud instead of Qobuz are kept apart in the "fallback" subfolder of your playlist. Keep in mind that searching for a track in Soundcloud isn't always perfect, so **double-check every tracks in your "fallback" folders**.

> The download quality from Soundcloud isn't true lossless (I think), but still better than mp3.

>[!Tip]
>When selecting your Qobuz credentials, try several countries as the library isn't the same everywhere on earth. To my experience, the best countries for Qobuz ripping are France, Germany.


## Dependencies

```
Python
ffmpeg
```

> Get ffmpeg [here](https://www.ffmpeg.org/download.html).

## Installation

### Mac / Linux - using bash
```
git clone git@github.com:ArthurCbn/cabot.git
cd cabot
bash installation.sh
source ~/.bashrc
```

### Windows - using Gitbash
1. Install [git bash](https://git-scm.com/downloads/win)
2. See above for installation using bash

## Update
When inside cabot directory :
```
bash update.sh
```

## Setup

Set-up your playlists' urls directly in `config.json` like so :

```json
{
    "playlists_folder": "your/playlists/folder",
    "mp3_copy": "True",
    "playlists": {
        "your_1st_playlist": {
            "spotify": "url_to_1st_spotify_playlist",
            "soundcloud": "url_to_1st_soundcloud_playlist"
        },
        "your_2nd_playlist": {
            "spotify": "url_to_2nd_spotify_playlist"
        },
        "your_3rd_playlist": {
            "soundcloud": "url_to_3rd_soundcloud_playlist"
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
   For "Redirects URls", you can put 'https://example.org/callback'
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

Just type `cabot` in your terminal to update all configurated playlists.
You can also specify certain playlists as arguments : `cabot playlist1 "another playlist with multiple words"`.

## Future features

- Analyse key and automatically add it to the metadata
