# -*- coding: utf-8 -*-

# File structure:
# {provider}_{collection_name}_{format}
#     - one_shots/
#         + {item_name}_{sequence}_{timestamp}_{note}.{format}
#             - title
#             - artist
#             - year
#     - attributions/
#         + {item_name}.txt
#             - citations
#             - url
#             - rights and access
#     + {item_name}_{sequence}_{timestamp}.{format}
#         - title
#         - artist
#         - year
#     - README.txt
#         - title
#         - url
#         - description
#         - rights and access
#         - structure

import argparse
import os
import sys

from lib.collection_utils import *
from lib.io_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-cdata', dest="COLLECTION_DATA_FILE", default="data/collections.csv", help="Input collection csv file")
parser.add_argument('-idata', dest="ITEM_DATA_FILE", default="data/collection_items.csv", help="Input collection items csv file")
parser.add_argument('-sdata', dest="SAMPLE_DATA_FILE", default="data/collection_samples.csv", help="Input collection samples csv file")
parser.add_argument('-sdir', dest="SAMPLE_DIR", default="path/to/samples/", help="Audio sample dir")
parser.add_argument('-iid', dest="ITEM_ID", default="filename", help="Key to match samples to item")
parser.add_argument('-sid', dest="SAMPLE_ID", default="sourceFilename", help="Key to match samples to item")
parser.add_argument('-ctmpl', dest="COLLECTION_TEMPLATE", default="readme_template.txt", help="Input template file for collection")
parser.add_argument('-itmpl', dest="ITEM_TEMPLATE", default="item_readme_template.txt", help="Input template file for item")
parser.add_argument('-formats', dest="FORMATS", default="mp3,wav", help="List of formats to produce")
parser.add_argument('-provider', dest="PROVIDER", default="loc.gov", help="Provider name")
parser.add_argument('-cid', dest="COLLECTION_ID", default="john-and-ruby-lomax", help="Collection id")
parser.add_argument('-dir', dest="OUTPUT_DIR", default="path/to/audio/", help="Output dir")
parser.add_argument('-out', dest="MANIFEST_FILE", default="output/%s.json", help="Output json manifest file")
a = parser.parse_args()

FORMATS = a.FORMATS.strip().split(',')
collectionTemplate = ""
with open(a.COLLECTION_TEMPLATE, 'r') as f:
    collectionTemplate = f.read()

itemTemplate = ""
with open(a.ITEM_TEMPLATE, 'r') as f:
    itemTemplate = f.read()

_, collections = readCsv(a.COLLECTION_DATA_FILE)
_, items = readCsv(a.ITEM_DATA_FILE)
_, samples = readCsv(a.SAMPLE_DATA_FILE)

collection = findWhere(collections, ("id", a.COLLECTION_ID))
if collection is None:
    print("Could not find %s" % a.COLLECTION_ID)
    sys.exit()

removeDir(a.OUTPUT_DIR)

for format in FORMATS:
    folder_name = '{provider}_{collection_name}_{format}'.format(provider=a.PROVIDER, collection_name=a.COLLECTION_ID, format=format)
    folder_path = a.OUTPUT_DIR + folder_name '/'
    one_shot_path = folder_path+'one_shots/'
    attributions_path = folder_path+'attributions/'
    makeDirectories([one_shot_path, attributions_path])

    # make main readme file
    collectionText = collectionTemplate.format(**collection)
    with open(folder_path+"README.txt", "w") as f:
        f.write(collectionText)

    # make attributions

    # make phrases

    # make samples

    # zip the directory
    zipdir = folder_path.rstrip('/')
    zipfilename = zipdir + '.zip'
    zipDir(zipfilename, zipdir)
