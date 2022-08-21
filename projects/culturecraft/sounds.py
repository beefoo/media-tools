# -*- coding: utf-8 -*-

import argparse
import inspect
import os
from pprint import pprint
import subprocess
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.collection_utils import *
from lib.io_utils import *

parser = argparse.ArgumentParser()
parser.add_argument('-ids', dest="IDS", default="00694027,00694029,00694030,00694031,00694033,00694034,00694035,00694036,00694038,00694040,00694056,00694087,00694088,00694091,00694092,00694094,00694098,00694105", help="List of item ids")
parser.add_argument('-meta', dest="METADATA_FILE", default="E:/Dropbox/citizen_dj/metadata/loc-edison.csv", help="Metadata file")
parser.add_argument('-sd', dest="SAMPLE_DATA_DIR", default="E:/Dropbox/citizen_dj/sampledata/loc-edison/{filename}.csv", help="Sample data directory")
parser.add_argument('-dir', dest="AUDIO_FILE_DIR", default="D:/citizen_dj/downloads/loc-edison/", help="Directory of input audio files")
parser.add_argument('-sort', dest="SORT", default="clarity=desc=100&dur=asc=50&power=asc=20", help="Query string to sort by")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/culturecraft_samples.csv", help="Path to output sample file")
parser.add_argument('-outaudio', dest="OUT_AUDIO", default="output/culturecraft_sounds.mp3", help="Output audio file")
parser.add_argument('-outdata', dest="OUT_DATA", default="output/culturecraft_sounds.json", help="Output data file")
parser.add_argument('-reverb', dest="REVERB", default=0, type=int, help="Add reverb (0-100)")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just display details?")
a = parser.parse_args()

_, items = readCsv(a.METADATA_FILE)
itemLookup = createLookup(items, 'id')
ids = a.IDS.split(",")

items = {}
allSamples = []
sampleFields = []
for id in ids:
    if id not in itemLookup:
        print(f'Could not find id {id}')
        continue
    item = itemLookup[id]
    filename = item['filename']
    samplefile = a.SAMPLE_DATA_DIR.format(filename=filename)
    if not os.isfile(samplefile):
        print(f'Could not find file {samplefile}')
        continue
    fields, samples = readCsv(samplefile)
    if len(sampleFields) <= 0:
        sampleFields = fields
    if len(a.SORT) > 0:
        samples = sortByQueryString(samples, a.SORT)
    if id not in items:
        rstart = len(allSamples)
        rstop = rstart + len(samples)
        sprites = [str(i) for i in range(rstart, rstop)]
        items[id] = {
            "id": id,
            "title": item["title"],
            "url": item["url"],
            "sprites": sprites
        }
    allSamples += samples

print(f'{len(allSamples)} samples in total')

if a.PROBE:
    sys.exit()

makeDirectories(a.OUTPUT_FILE)
writeCsv(a.OUTPUT_FILE, allSamples, headings=sampleFields)

command = [sys.executable, 'samples_to_audio_sprite.py',
            '-in', a.OUTPUT_FILE, 
            '-dir', a.AUDIO_FILE_DIR,
            '-out', a.OUT_AUDIO,
            '-data', a.OUT_DATA,
            '-reverb', str(a.REVERB)]
print("------")
print(" ".join(command))
finished = subprocess.check_call(command)

jsonData = readJSON(a.OUT_DATA)
newJsonData = {
    "sprites": jsonData,
    "groups": [items[key] for key in items]
}
writeJSON(a.OUT_DATA, jsonData)