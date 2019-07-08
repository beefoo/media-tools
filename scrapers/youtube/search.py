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
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-key', dest="API_KEY", default="", help="Your API Key. See: https://google-developers.appspot.com/youtube/v3/getting-started")
parser.add_argument('-query', dest="QUERY", default=" location=40.903125,-73.85062&locationRadius=10km&videoLicense=creativeCommon", help="Search query parameters as a query string")
parser.add_argument('-sort', dest="SORT_BY", default="", help="Sort by string")
parser.add_argument('-lim', dest="LIMIT", default=100, type=int, help="Limit results")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/yt-search/%s.json", help="JSON output file pattern")
parser.add_argument('-verbose', dest="VERBOSE", action="store_true", help="Display search result details")
a = parser.parse_args()
aa = vars(a)
makeDirectories([a.OUTPUT_FILE])

aa["QUERY"] = a.QUERY.strip()
MAX_YT_RESULTS_PER_PAGE = 50

if len(a.API_KEY) <= 0:
    print("You must pass in your developer API key. See more at https://google-developers.appspot.com/youtube/v3/getting-started")
    sys.exit()

if len(a.QUERY) <= 0:
    print("Please pass in a query.")

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=a.API_KEY)

ytQuery = parseQueryString(a.QUERY)

ytQuery["part"] = "id,snippet"
ytQuery["type"] = "video" # Always get videos back
ytQuery["videoDimension"] = "2d" # exclude 3d videos

if len(a.SORT_BY) > 0:
    ytQuery["order"] = a.SORT_BY

pages = 1
if a.LIMIT > 0:
    pages = ceilInt(1.0 * a.LIMIT / MAX_YT_RESULTS_PER_PAGE)
    ytQuery["maxResults"] = min(a.LIMIT, MAX_YT_RESULTS_PER_PAGE)

results = []
for page in range(pages):
    print("Page %s..." % (page+1))
    # Make one query to retrieve ids
    search_response = youtube.search().list(**ytQuery).execute()
    nextPageToken = search_response.get('nextPageToken', "")
    # pprint(search_response.get('items', []))
    # sys.exit()

    ids = []
    for r in search_response.get('items', []):
        ids.append(r['id']['videoId'])
    print("%s results found." % (len(ids)))

    missingIds = []
    for id in ids:
        outfile = a.OUTPUT_FILE % id
        if not os.path.isfile(outfile):
            missingIds.append(id)

    if len(missingIds) > 0:
        print("Getting details for %s videos..." % (len(missingIds)))
        # Make another query to retrieve stats
        idString = ",".join(ids)
        search_response = youtube.videos().list(id=idString, part="id,statistics,snippet").execute()
        if a.VERBOSE:
            print("-----\nResults: ")
        for r in search_response.get('items', []):
            outfile = a.OUTPUT_FILE % r['id']
            writeJSON(outfile, r, verbose=a.VERBOSE)
            # pprint(r['id'])
            # pprint(r['statistics'])
            # pprint(r['snippet'])
            if a.VERBOSE:
                print("%s: %s (%s views)" % (r['id'], r['snippet']['title'], r['statistics']['viewCount']))
        if a.VERBOSE:
            print("-----")

    # Retrieve the next page
    if len(nextPageToken) < 1:
        break

    ytQuery["pageToken"] = nextPageToken

print("Done.")
