# Cumulus TV m3u8 loader/uploader

Is a m3u8 parser and conversor to cumulus-tv json file format for Google Drive, see: https://github.com/Fleker/CumulusTV 

## Goals

* Download multiple m3u8 files from your online providers.
* Use multiple m3u8 files from your filesystem as well.
* Can join/convert from your providers to one single m3u8 file or cumulus-tv json.
* Can save cumulus-tv json file format to your filesystem, you can upload to your drive manually later.
* You can automatically upload to your google drive (need app permissions, see below)

## Install

    git clone https://github.com/curif/cumulus-tv-m3u8-loader.git
    cd cumulus-tv-m3u8-loader
    sudo pip install -r requires.txt 
    cd src
    cp configToCopy.py config.py

## Configuration

Modify src/config.py. Change the configuration to point to your m3u8 online providers o files in your filesystem.
Define the outputs as needed.

## run
    
    cd cumulus-tv-m3u8-loader/src
    python ./m3u8_loader.py

### config.py structure:

``` python
{ 
 "providers": {},
 "outputs": {}
}
```
* `providers`: define the access file/url, conversion and filters for the m3u8 load and parse. Multiple providers can be processed.
* `outputs`: define file outputs and google drive saving information.

You can activate/deactivate configuration options using the `active` key (setting true or false).

#### providers section

#### Note:

Before write each `providers` section, you will need to study the m3u8 source to understand what to add and what to exclude.

``` python
"providers": {
    "fromArchive": {
      "active": True,
      "url": "file:///home/desarrollo/desarr/cumulus-tv-m3u8-loader/src/test.m3u",
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
      "url": "https://raw.githubusercontent.com/curif/cumulus-tv-m3u8-loader/develop/src/my.m3u",
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
  * `filters`: lists that filters the source EXTINF data. Only the data that cumpliments the list will be processed.
    * `lang`: language list. For example ["spanish"] will exclude others languages than spanish.
    * `country`: country list.
    * `group`: filter the `group-title` tag. For example a list `["movie", "news", "documentary"]` will exclude "adult" content.
  * `validation`: all url in the stream will be checked, for example to check if is online or accessible.
    * `active`: True or False. False to avoid validation.
    * `command`: command to execute, __file__ will be replaced with the stream url.
    * `return-code-error`: error codes array. If the command return value is one of this values, the stream is considered invalid.
    * `timeout-secs`: Timeout in secs. Time to command execution.
    * `timeout-kill-command`: a command to execute when the timeout is reached.

### outputs

The output can be a m3u8 file, a cumulus tv json file and a a cumulus tv json file in your google drive.

```python

  "outputs": {
    "google-drive": {
      "active": True,
      "file-name": "cumulus-tv-test.json",
      "auth-code": ""
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
  
### Google Drive
  
First time you run, and with `outputs/google-drive/active` in True, the program will require permission to access your google drive device. Please, cut and paste the url in the message in a browser and follow the steps. Finally cut the code and paste in `outputs/google-drive/auth-code`.
  
Example:
  
      This application have not access to your Google Drive. Yo need to obtain a access code from:
      https://accounts.google.com/o/oauth2/auth?scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive&redirect_uri=urn 
      then copy and paste the code in "auth-code" in the output/google-drive section in your config.py file


## Contributing

Ask me anything, or submit a pull request.

