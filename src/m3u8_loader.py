
import sys
import urllib2
import re
import time
import pprint
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import json
import os
import subprocess, threading

try:
  import config as config
except ImportError:
  print "config.py file not found! to create one copy the configToCopy.py over config.py and modify."
  sys.exit(-1)

"""
Parser for Cumulus TV
https://github.com/Fleker/CumulusTV
"""

"""
m3u8 examples:

#EXTINF:0 tvg-name="Important Channel" tvg-language="English" tvg-country="US" tvg-id="imp-001" tvg-logo="http://pathlogo/logo.jpg" group-title="Top10", Discovery Channel cCloudTV.ORG (Top10) (US) (English)
http://167.114.102.27/live/Eem9fNZQ8r_FTl9CXevikA/1461268502/a490ae75a3ec2acf16c9f592e889eb4c.m3u8|User-Agent=Mozilla%2F5.0%20(Windows%20NT%206.1%3B%20WOW64)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F47.0.2526.106%20Safari%2F537.36

"""

pp = pprint.PrettyPrinter(indent=2)

__author__ = 'curif'

m3u_regex = '#(.+?),(.+)\s*(.+)\s*'
name_regex = '.*?tvg-name=[\'"](.*?)[\'"]'
group_regex = '.*?group-title=[\'"](.*?)[\'"]'
logo_regex = '.*?tvg-logo=[\'"](.*?)[\'"]'
lang_regex = '.*?tvg-language=[\'"](.*?)[\'"]'
country_regex = '.*?tvg-country=[\'"](.*?)[\'"]'
id_regex = '.*?tvg-id=[\'"](.*?)[\'"]'

m3uRe = re.compile(m3u_regex)
nameRe = re.compile(name_regex)
logoRe = re.compile(logo_regex)
langRe = re.compile(lang_regex)
countryRe = re.compile(country_regex)
idRe = re.compile(id_regex)
groupRe = re.compile(group_regex)


class Command(object):
  """
  Thanks: http://stackoverflow.com/questions/1191374/using-module-subprocess-with-timeout
  """
  def __init__(self, cmd):
    self.cmd = cmd
    self.process = None

  def run(self, timeout):
    ret = 0
    def target():
      print "RUN:" + self.cmd
      self.process = subprocess.Popen(self.cmd, shell=True)
      self.process.communicate()

    thread = threading.Thread(target=target)
    thread.start()

    thread.join(timeout)
    if thread.is_alive():
      self.process.terminate()
      thread.join()
      print "TIMEOUT"
      ret = 256
    else:
      ret = self.process.returncode
    print "RETURN: " + str(ret)
    return ret

def loadm3u(url):
  hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
         'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
         'Accept-Encoding': 'none',
         'Accept-Language': 'en-US,en;q=0.8',
         'Connection': 'keep-alive'}

  req = urllib2.Request(url, headers=hdr)
  response = urllib2.urlopen(req)
  data = response.read()

  if not '#EXTM3U' in data:
    raise Exception(url + " is not a m3u8 file.")

  return data.encode('utf-8')


def regParse(parser, data):
  foundString = parser.search(data)
  if foundString:
    #print "regParse result", x.group(1)
    return foundString.group(1).strip()
  return None


def mapGenres(genre, provider):
  ret = ""
  if genre:
    genre = genre.lower()
    genres = config.config["providers"][provider].get("genres-map", None)
    if genres:
      if genre in genres:
        ret = genres[genre]
  return ret


def possibleGenres(cumulustv):
  """
  all genres in channels
  :param cumulustv:
  :return: genres array
  """
  retGenres = []
  for channel in cumulustv["channels"]:
    if "genres" in channel:
      genres = channel["genres"].split(",")
      for genre in genres:
        if genre not in retGenres:
          retGenres.append((genre))
  return retGenres


def validate(validation, url):
  cmd = Command(str.replace(validation["command"], "__file__", url))
  ret = cmd.run(timeout=validation.get("timeout-secs", 3))
  return ret in validation["return-code-error"]


def process(m3u, provider, cumulustv, contStart=None):

  match = m3uRe.findall(m3u)
  urlEndChar = config.config["providers"][provider].get("m3u-url-endchar", "")
  filters = config.config["providers"][provider].get("filters", None)
  validation = config.config["providers"][provider].get("validation", None)

  if contStart is None:
    contStart=0

  for extInfData, name, url in match:

    id = regParse(idRe, extInfData)
    logo = regParse(logoRe, extInfData)
    country = regParse(countryRe, extInfData)
    group = regParse(groupRe, extInfData)
    lang = regParse(langRe, extInfData)

    if name is None or name == "":
      name = regParse(nameRe, extInfData)

    if filters is None or \
        (filters.get("country", None) is not None and country.lower() in filters["country"] and \
         filters.get("lang", None) is not None and lang.lower() in filters["lang"] and \
         filters.get("group", None) is not None and group.lower() in filters["group"]):

      if urlEndChar and urlEndChar != "":
        url = url.split(urlEndChar)[0]

      valid = True
      if validation and "active" and validation.get("active", False):
        try:
          valid = validate(validation, url)
        except Exception as e:
          valid = False
          print "Validation error:" + str(e)
          pass

      if valid:
        contStart += 1

        genres = mapGenres(group, provider)

        cumulusData = {
          "number": str(contStart),
          "name": name,
          "logo": logo,
          "url": url,
          "genres": genres,
          "lang": lang, #extra data not defined in cumulus tv
          "country": country #extra data not defined in cumulus tv
        }
        cumulustv["channels"].append(cumulusData)

  return contStart


def write2File(fd, cumulustv):
  channels = cumulustv["channels"]
  channelDataMap = [
    ("number", "tvg-id"),
    ("name", "tvg-name"),
    ("logo", "tvg-logo"),
    ("genres", "group-title"),
    ("country", "tvg-country"),
    ("lang", "tvg-language")
  ]
  fd.write("#EXTM3U\n")
  for channel in channels:
    fd.write("#EXTINF:0 ")
    for dataId, extinfId in channelDataMap:
      if channel[dataId] is not None and channel[dataId] != "":
        fd.write(" " + extinfId + "=\"" + channel[dataId].strip() + "\" ")
    fd.write(", " + channel["name"].strip() + "\n")
    fd.write(channel["url"] + "\n")

  return

#-------------------------------------------------------------------------------
# process
#-------------------------------------------------------------------------------

cumulustv = {"channels": [],
             "timestamp": time.time()}
startAt = 0  #first channel number - 1

for provider, providerData in config.config["providers"].iteritems():
  if providerData.get("active", False):
    print "Provider: " + provider
    try:
      m3uContent = loadm3u(providerData["url"])
    except Exception as e:
      print str(e)
    else:
      startAt = int(providerData.get("first-channel-number", startAt))
      startAt += process(m3uContent, provider, cumulustv, startAt)

      genres = possibleGenres(cumulustv)
      if len(genres) > 0:
        cumulustv.update({"possibleGenres": genres})

      #pp.pprint(cumulustv)

print "Channels: " + str(startAt)

#write to file
m3uFile = config.config["outputs"].get("m3u-file", None)
if m3uFile:
  if m3uFile.get("active", False):
    try:
      fileName = m3uFile["file-name"]
      with open(fileName, "w") as fd:
        write2File(fd, cumulustv)
      print "Output file: " + fileName
    except Exception as e:
      print "can't open/write file: " + str(e)
      sys.exit(-1)

#send to DRIVE
driveConfig = config.config["outputs"].get("google-drive", None)
if driveConfig:
  if driveConfig.get("active", False):
    gauth = GoogleAuth()
    #gauth.LocalWebserverAuth() # Creates local webserver and auto handles authentication
    authCode = driveConfig.get("auth-code", "")
    if authCode is None or authCode == "":
      url = gauth.GetAuthUrl()
      print "This application have not access to your Google Drive. Yo need an access code from:"
      print url
      print "then copy and paste the code in \"auth-code\" in the outputs/google-drive section in your config.py file"
      sys.exit(0)

    try:
      gauth.Auth(authCode)
      drive = GoogleDrive(gauth)
    except Exception as e:
      print "Exception: " + str(e)
      print "If you have problems with the application permissions try to use this url:"
      print gauth.GetAuthUrl()
      print "then copy and paste the code in the outputs/google-drive/auth-code section in your config.py file"
      sys.exit(-1)

    fileName = driveConfig.get("file-name", "cumulustv.json")
    jsonContent = json.dumps(cumulustv, ensure_ascii=False)

    try:
      cumulusTVFile = drive.CreateFile({'title': fileName, 'mimeType': 'application/json'})  # Create GoogleDriveFile instance with title 'Hello.txt'
      cumulusTVFile.SetContentString(jsonContent) # Set content of the file from given string
      cumulusTVFile.Upload()
      print "Uploaded to drive: " + fileName
    except Exception as e:
      print "Google Drive upload exception: " + str(e)

#send json to disk
jsonOutput = config.config["outputs"].get("json-file", None)
if jsonOutput:
  if jsonOutput.get("active", False):
    fileName = jsonOutput.get("file-name", "cumulustv.json")
    jsonContent = json.dumps(cumulustv, ensure_ascii=False)
    try:
      with open(fileName, "w") as fd:
        fd.write(jsonContent)
      print fileName + " saved."
    except Exception as e:
      print "ERROR saving json file: " + str(e)
      sys.exit(-1)



