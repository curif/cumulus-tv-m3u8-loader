
__author__ = 'curif'

config = {
  #add your m3u8 providers here
  "providers": {
    #assign a name to each provider, example: "fromArchive", "fromURL", "fromMyProvider"
    "fromArchive": {
      "active": True,

      #from file:
      "url": "file:///home/desarrollo/desarr/cumulus-tv-m3u8-loader/src/test.m3u",

      #some m3u url providers add some extra data at end url:
      "m3u-url-endchar": "?",

      #map the group-title extinf data to android tv genres,
      # see: http://developer.android.com/reference/android/media/tv/TvContract.Programs.Genres.html
      "genres-map": {
        "news": "NEWS",
        "music": "MUSIC",
        "movies": "MOVIES",
        "entertainment": "ENTERTAINMENT",
        "adult": "MOVIES",
        "family": "FAMILY_KIDS",
        "animal": "ANIMAL_WILDLIFE"
      },
      "validation": {
        "active": False,
        "command": "avprobe \"__file__\"",
        "return-code-error": [1, 256],
        "timeout-secs": 3,
        "timeout-kill-command": "killall -9 avprobe"
      },
    },
    "MyGithubFileTest": {
      "active": True,

      #http url or file name in the form: "file:///home/<user>/blah/mifile.m3u"
      "url": "https://raw.githubusercontent.com/curif/cumulus-tv-m3u8-loader/develop/src/my.m3u",


      #filter to include m3u data (all lowercase), None for ignore.
      "filters": {
        "lang": ["english", "spanish"],
        "country": ["us", "ar", "au"],
        #group-title
        "group": [
          "entertainment",
          "news",
          "family",
          "animal"
        ]
      },
      "validation": {
        "active": False,
        "command": "avprobe \"__file__\"",
        "return-code-error": [1, 256],
        "timeout-secs": 3,
        "timeout-kill-command": "killall -9 avprobe"
      },
      #map the group-title extinf data to android tv genres,
      # see: http://developer.android.com/reference/android/media/tv/TvContract.Programs.Genres.html
      "genres-map": {
        "news": "NEWS",
        "entertainment": "ENTERTAINMENT",
        "family": "FAMILY_KIDS",
        "animal": "ANIMAL_WILDLIFE"
      }
    }
  },

  "outputs": {
    "google-drive": {
      "active": True,
      "file-name": "cumulus-tv-test.json"
    },
    "m3u-file": {
      "active": True,
      "file-name": "cumulus-tv-test.m3u"
    },
    "json-file": {
      "active": True,
      "file-name": "cumulus-tv-test.json"
    }
  },

  "log": {
    'file': "m3u_loader.log",
    'level': 10,
    'maxBytes': 500*1024,
    'backupCount': 5
  }
}
