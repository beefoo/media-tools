# -*- coding: utf-8 -*-

# Search API docs: https://developers.google.com/youtube/v3/docs/search/list
# Search API Python docs: https://developers.google.com/resources/api-libraries/documentation/youtube/v3/python/latest/youtube_v3.search.html

import argparse
import inspect
import math
import os
from pprint import pprint
import sys

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.collection_utils import *
from lib.io_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-key', dest="API_KEY", default="", help="Your API Key. See: https://google-developers.appspot.com/youtube/v3/getting-started")
parser.add_argument('-in', dest="QUERY_FILE", default="", help="CSV file with queries")
parser.add_argument('-query', dest="QUERY", default=" location=45.517967,-73.732461&locationRadius=10km&videoLicense=creativeCommon", help="Search query parameters as a query string")
parser.add_argument('-sort', dest="SORT_BY", default="", help="Sort by string")
parser.add_argument('-lim', dest="LIMIT", default=50, type=int, help="Limit results")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="CSV output file to save results")
a = parser.parse_args()

QUERY = a.QUERY.strip()

if len(a.API_KEY) <= 0:
    print("You must pass in your developer API key. See more at https://google-developers.appspot.com/youtube/v3/getting-started")
    sys.exit()

if len(QUERY) <= 0:
    print("Please pass in a query.")

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=a.API_KEY)

ytQuery = parseQueryString(QUERY)

ytQuery["part"] = "id,snippet"
ytQuery["type"] = "video" # Always get videos back
ytQuery["videoDimension"] = "2d" # exclude 3d videos

if len(a.SORT_BY) > 0:
    ytQuery["order"] = a.SORT_BY

if a.LIMIT > 0:
    ytQuery["maxResults"] = a.LIMIT

# Make one query to retrieve ids
search_response = youtube.search().list(**ytQuery).execute()
ids = []
for r in search_response.get('items', []):
    ids.append(r['id']['videoId'])

# Make another query to retrieve stats
idString = ",".join(ids)
search_response = youtube.videos().list(id=idString, part="id,statistics,snippet").execute()
print("-----\nResults: ")
for r in search_response.get('items', []):
    # pprint(r['id'])
    # pprint(r['statistics'])
    # pprint(r['snippet'])
    print("%s: %s (%s views)" % (r['id'], r['snippet']['title'], r['statistics']['viewCount']))
print("-----")

# writeCsv(a.OUTPUT_FILE, results, fieldNames)

print("Done.")
