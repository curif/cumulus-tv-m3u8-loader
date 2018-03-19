
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
import logging
import logging.handlers
import validators

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

m3u_regex = '(.+?),(.+)\s*(.+)\s*'
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

urlCollector = []

class Command(object):
  """
  Thanks: http://stackoverflow.com/questions/1191374/using-module-subprocess-with-timeout
  """
  def __init__(self, cmd, killTimeoutCmd=None):
    self.cmd = cmd
    self.process = None
    self.killTimeoutCmd = killTimeoutCmd

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
      if self.killTimeoutCmd is not None:
        os.system(self.killTimeoutCmd)
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

  if not 'EXTM3U' in data:
    raise Exception(url + " is not a m3u8 file.")

  #return data.encode('utf-8')
  return data


def regParse(parser, data):
  foundString = parser.search(data)
  if foundString:
    #print "regParse result", x.group(1)
    return foundString.group(1).strip()
  return None


def filterByName(filterNames, name):
  """
  Verify channel name contains string
  :param filterNames: names array ["blah", "sese"]
  :param name: channel name "blah"
  :return: True if at least one element in array is part of string channel name.
  """
  if len(filterNames) == 0:
    return True

  lowName = name.lower()
  for n in filterNames:
    if n.lower() in lowName:
      return True

  return False


def mapGenres(genre, provider):
  if genre:
    genre = genre.lower()
    genres = config.config["providers"][provider].get("genres-map", None)
    if genres and genre in genres:
      return genres[genre]
  return genre or ""


def mapGenresByName(name, provider):
  ret = ""
  if name != "":
    name = name.lower()
    genres = config.config["providers"][provider].get("genres-map-by-name", None)
    if genres:
      for partialName in genres.keys():
        if partialName.lower() in name:
          ret = genres[partialName]
          break
  return ret or ""


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
  cmd = Command(str.replace(validation["command"], "__file__", url),
                killTimeoutCmd=validation.get("timeout-kill-command", None))
  ret = cmd.run(timeout=validation.get("timeout-secs", 3))
  return ret not in validation["return-code-error"]


def verifyFilters(filters, name, country, group, lang):
  """
  @:return True if the channel pass the filter validation
  """

  if filters is None:
    return True

  filterCountry = filters.get("country", None)
  if filterCountry is not None:
    if country is None or country.lower() not in filterCountry:
      return False

  filterGroup = filters.get("group", None)
  if filterGroup is not None:
    if group is None or group.lower() not in filterGroup:
      return False

  filterLang = filters.get("lang", None)
  if filterLang is not None:
    if lang is None or lang.lower() not in filterLang:
      return False

  filterName = filters.get("names", None)
  if filterName:
    if "include" in filterName:
      if not filterByName(filterName["include"], name):
        return False
    if "exclude" in filterName:
      if filterByName(filterName["exclude"], name):
        return False

  return True


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

    if verifyFilters(filters, name, country, group, lang):

      if urlEndChar and urlEndChar != "":
        url = url.split(urlEndChar)[0]

      valid = True
      if validation and validation.get("active", False):
        try:
          valid = validate(validation, url)
        except Exception as e:
          valid = False
          print "Validation error:" + str(e)
          pass

      #avoid duplicates
      valid = valid and url not in urlCollector

      #valid url
      valid = valid and validators.url(url) == True

      logging.info(" - Channel: " + name + " - valid: " + str(valid) + " " + url)

      if valid:
        contStart += 1

        genres = mapGenres(group, provider)
        if genres.strip() == "":
          genres = mapGenresByName(name, provider)

        #valid logo:
        if logo is not None and logo != "":
          if validators.url(logo) != True:
            logo = None

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

        urlCollector.append(url)

        logging.info("     - assigned number: " + str(contStart))
        logging.info("     - genres         : " + str(genres))
        logging.info("     - language       : " + str(lang))
        logging.info("     - country        : " + str(country))

  return contStart


def dictToM3U(cumulustv):
  channels = cumulustv["channels"]
  channelDataMap = [
    ("number", "tvg-id"),
    ("name", "tvg-name"),
    ("logo", "tvg-logo"),
    ("genres", "group-title"),
    ("country", "tvg-country"),
    ("lang", "tvg-language")
  ]
  m3uStr = "#EXTM3U\n"
  for channel in channels:
    m3uStr += "#EXTINF:-1"
    for dataId, extinfId in channelDataMap:
      if channel[dataId] is not None and channel[dataId] != "":
        m3uStr += " " + extinfId + "=\"" + channel[dataId].strip() + "\""
    m3uStr += "," + channel["name"].strip() + "\n"
    m3uStr += channel["url"] + "\n"

  return m3uStr

def write2File(fd, cumulustv):
  fd.write(dictToM3U(cumulustv))
  return


def logStart():
  """
  start logging
  """

  if "log" not in config.config:
    return

  configLog = config.config["log"]
  fileName = configLog.get("file", "m3u8_loader.log")

  # inicia el logging
  logging.basicConfig(
    filename=fileName,
    level=int(configLog.get("level",10)),
    format='%(asctime)s - %(name)s: %(levelname)s: %(message)s'
  )

  # Se configura para que sea rotativo
  hand = logging.handlers.RotatingFileHandler(fileName,
                                              maxBytes=configLog.get('maxBytes', 100*1024),
                                              backupCount=configLog.get('backupCount', 5))

  logger = logging.getLogger('root')
  logger.addHandler(hand)

  return


def uploadS3(filename, contents):
  import io
  import boto3
  from cStringIO import StringIO

  session = boto3.Session()
  credentials = session.get_credentials()

  # Credentials are refreshable, so accessing your access key / secret key
  # separately can lead to a race condition. Use this to get an actual matched
  # set.
  credentials = credentials.get_frozen_credentials()
  access_key = credentials.access_key
  secret_key = credentials.secret_key

  s3 = boto3.resource(
    's3',
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key
  )

  fake_handle = StringIO(contents)

  bucket, filename_only = filename.split('/')

  # notice if you do fake_handle.read() it reads like a file handle
  file = s3.Bucket(bucket).put_object(
    Key=filename_only,
    Body=fake_handle.read(),
    ContentType='text/plain',
    ACL='public-read'
  )

#-------------------------------------------------------------------------------
# process
#-------------------------------------------------------------------------------

logStart()

logging.info("================================================================================")
logging.info("================================================================================")
logging.info("start")
logging.info("================================================================================")
logging.info("================================================================================")

cumulustv = {"channels": [],
             "timestamp": str(time.time())}
startAt = 0  #first channel number - 1

for provider, providerData in config.config["providers"].iteritems():
  if providerData.get("active", False):
    logging.info("Provider: " + provider + " ======================")
    logging.info("url     : " + providerData["url"])
    try:
      m3uContent = loadm3u(providerData["url"])
    except Exception as e:
      logging.error("loading " + providerData["url"] + " - " + str(e))
    else:
      startAt = int(providerData.get("first-channel-number", startAt))
      startAt += process(m3uContent, provider, cumulustv, startAt)

      genres = possibleGenres(cumulustv)
      if len(genres) > 0:
        cumulustv.update({"possibleGenres": genres})

      #pp.pprint(cumulustv)

logging.info("END - Channels loaded: " + str(len(urlCollector)))

#write to file
m3uFile = config.config["outputs"].get("m3u-file", None)
if m3uFile:
  if m3uFile.get("active", False):
    try:
      fileName = m3uFile["file-name"]
      logging.info("Write to file:" + fileName)
      with open(fileName, "w") as fd:
        write2File(fd, cumulustv)
    except Exception as e:
      logging.error("can't open/write file: " + str(e))
      sys.exit(-1)

#write to s3
s3File = config.config["outputs"].get("s3", None)
if s3File:
  if s3File.get("active", False):
    try:
      fileName = s3File["file-name"]
      logging.info("Write to s3 file:" + fileName)
      uploadS3(s3File["file-name"], dictToM3U(cumulustv))
    except Exception as e:
      logging.error("can't open/write file to s3: " + str(e))
      sys.exit(-1)

#send to DRIVE
driveConfig = config.config["outputs"].get("google-drive", None)
if driveConfig:
  if driveConfig.get("active", False):
    gauth = GoogleAuth()
    gauth.CommandLineAuth()
    #gauth.LocalWebserverAuth() # Creates local webserver and auto handles authentication
    # authCode = driveConfig.get("auth-code", "")
    # if authCode is None or authCode == "":
    #   url = gauth.GetAuthUrl()
    #   print "This application have not access to your Google Drive. Yo need an access code from:"
    #   print url
    #   print "then copy and paste the code in \"auth-code\" in the outputs/google-drive section in your config.py file"
    #   sys.exit(0)

    try:
      #gauth.Auth(authCode)
      drive = GoogleDrive(gauth)
    except Exception as e:
      print "Exception: " + str(e)
      print "If you have problems with the application permissions try to use this url:"
      print gauth.GetAuthUrl()
      print "then copy and paste the code in the outputs/google-drive/auth-code section in your config.py file"
      sys.exit(-1)

    fileName = driveConfig.get("file-name", "cumulustv.json")
    jsonContent = json.dumps(cumulustv, ensure_ascii=True)

    try:
      cumulusTVFile = drive.CreateFile({'title': fileName, 'mimeType': 'application/json'})  # Create GoogleDriveFile instance with title 'Hello.txt'
      cumulusTVFile.SetContentString(jsonContent) # Set content of the file from given string
      cumulusTVFile.Upload()
      print "Uploaded to drive: " + fileName
    except Exception as e:
      err="Google Drive upload exception: " + str(e)
      print err
      logging.error(err)

#send json to disk
jsonOutput = config.config["outputs"].get("json-file", None)
if jsonOutput:
  if jsonOutput.get("active", False):
    fileName = jsonOutput.get("file-name", "cumulustv.json")
    logging.info("Cumulus tv json - write to file:" + fileName)
    jsonContent = json.dumps(cumulustv, ensure_ascii=False)
    try:
      logging.info("Write to file:" + fileName)
      with open(fileName, "w") as fd:
        fd.write(jsonContent)
    except Exception as e:
      logging.error("ERROR saving json file: " + str(e))
      sys.exit(-1)

logging.info("END -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
