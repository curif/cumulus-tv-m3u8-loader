# Cumulus TV - IPTV Simple - m3u loader/uploader

IPTV m3u list parser, conversor and uploader for Cumulus-tv and Kodi IPTV simple, see: https://github.com/Fleker/CumulusTV & https://github.com/kodi-pvr/pvr.iptvsimple

## Goals

* Download multiple m3u files from online providers.
* Use multiple m3u files from your filesystem as well.
* Filter channels, collect only required channels.
* Validate online streams.
* Group channels by configured criteria.
* Save cumulus-tv json file format to your filesystem, you can upload to your drive manually later.
* Output to m3u file.
* Upload cumulust tv json file to google drive (need app permissions, see below)

## Install

    git clone https://github.com/curif/cumulus-tv-m3u8-loader.git
    cd cumulus-tv-m3u8-loader
    sudo pip install -r requires.txt 
    cd src
    cp configToCopy.py config.py

## Configuration

Modify src/config.py. Change the configuration to point to your m3u8 online providers or files in your filesystem.
Define the outputs as needed.

## run
    
    cd cumulus-tv-m3u8-loader/src
    python ./m3u8_loader.py

### config.py structure:

``` python
config = {
 "providers": {},
 "outputs": {},
 "log": {}
}
```

* `providers`: define the access file/url to m3u playlists. Define conversion and filters channels. Multiple providers can be processed.
* `outputs`: define file outputs and google drive saving information.
* `log`: logging configuration.

You can activate/deactivate configuration options using the `active` key (setting `True` or `False`).

#### providers section

### Note:

Before write each `providers` section, you will need to study the m3u source to decide what to add and what to exclude.

Example:

``` python
"providers": {
    "fromArchive": {
      "active": True,
      "url": "file:///home/myuser/desarr/cumulus-tv-m3u8-loader/src/test.m3u",
      "m3u-url-endchar": "?",
      "genres-map": {
        "news": "NEWS",
        "music": "MUSIC",
        "movies": "MOVIES",
        "entertainment": "ENTERTAINMENT",
        "adult": "MOVIES",
        "family": "FAMILY_KIDS",
        "animal": "ANIMAL_WILDLIFE"
      },
      "genres-map-by-name": {
        "FOX": "MOVIES",
        "FX": "MOVIES",
        "CNN": "NEWS",
        "C5N": "NEWS",
       },
      "validation": {
        "active": False,
        "command": "avprobe \"__file__\"",
        "return-code-error": [1, 256],
        "timeout-secs": 3,
        "timeout-kill-command": "killall -9 avprobe"
      },
      "filters": {
        "names": {
            "include": ["food", "horror", "home", "movies"],
            "exclude": ["DE", "FR", "it", "sport", "tr"]
        }
      }
    },
    "MyGithubFileTest": {
      "active": True,
      "url": "https://raw.githubusercontent.com/curif/cumulus-tv-m3u8-loader/develop/src/test.m3u",
      "filters": {
        "lang": ["english", "spanish"],
        "country": ["us", "ar", "au"],
        "group": [
          "entertainment",
          "news",
          "family",
          "animal"
        ]
      },
      "genres-map": {
        "news": "NEWS",
        "entertainment": "ENTERTAINMENT",
        "family": "FAMILY_KIDS",
        "animal": "ANIMAL_WILDLIFE"
      }
    }
  },
```

providers keys:

* `fromArchive` name it as you wish, is a reference name.
  * `url`: url/file to download/access the m3u8 data.
  * `m3u-url-endchar` some providers add extra information to stream url.
  * `genres-map`: dictionary that map the genres in the `group-title` EXTINF tag to a genre that android TV can understand. Please see http://developer.android.com/reference/android/media/tv/TvContract.Programs.Genres.html for a genres list.
  * `genres-map-by-name`: assign a genre based on name substring, Example: {"GREAT": "MOVIES"}, assign the "MOVIES" genre to a channel named "the great channel".
  * `filters`: filters by the source EXTINF channel information tags.
    * `lang`: language list. For example ["spanish"] will exclude others languages than spanish.
    * `country`: country list.
    * `group`: filter the `group-title` tag. For example a list `["movie", "news", "documentary"]` will exclude "adult" content.
    * `names`: filter channel names
      * `include`: array of string to verify, example ["horror", "home"] will match with "The horror channel" and with "home and health", those channels will be included.
      * `exclude`: inverse of include.
  * `validation`: all url in the stream will be checked, for example to check if is online or accessible.
    * `active`: True or False. False to avoid validation.
    * `command`: command to execute, `__file__` will be replaced with the stream url.
    * `return-code-error`: error codes array. If the command return value is one of this values, the stream is considered invalid.
    * `timeout-secs`: Timeout in secs. Time to wait the command execution end.
    * `timeout-kill-command`: a command to execute when the timeout is reached.

### outputs

The output can be a m3u8 file, a cumulus tv json file and a a cumulus tv json file in your google drive.

```python

  "outputs": {
    "google-drive": {
      "active": True,
      "file-name": "cumulus-tv-test.json",
    },
    "m3u-file": {
      "active": True,
      "file-name": "cumulus-tv-test.m3u"
    },
    "json-file": {
      "active": True,
      "file-name": "cumulus-tv-test.json"
    }
  }
  ```
  
Please configure the `outputs` section as needed. The names are self explanatory.

### logging

```python
  "log": {
    'file': "m3u_loader.log",
    'level': 10,
    'maxBytes': 500*1024,
    'backupCount': 5
  }
```

Establish logging file:

  * `file`: file name
  * `level`: python log level number
  * `maxBytes`: max bytes per log
  * `backupCount`: log rotation max file count.

### Google Drive

When `outputs/google-drive/active` is True, the program will try to upload the json file to your google drive account.
Please, cut and paste the url in the message in a browser and follow the steps. Finally cut the response code in your browser and paste it in the command prompt.

This program have not GUI, is designed to work in a remote CLI (may be in a ssh session), then is not possible to follow the methods usually used for user validation.

In Cumulus TV the only way to obtain the json configuration file is via google drive.

## Contributing

Ask me anything, or submit a pull request.

