# -*- coding: utf-8 -*-

import argparse
import os
from pprint import pprint
import shutil
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-sdir', dest="SAMPLE_PACK_DIR", default="output/samplepack_john-and-ruby-lomax/", help="Base directory for sample packs")
parser.add_argument('-idata', dest="ITEM_DATA_FILE", default="metadata/loc_john-and-ruby-lomax.csv", help="Input collection items csv file")
parser.add_argument('-id', dest="ID_KEY", default="id", help="Key that contains item identifier")
parser.add_argument('-url', dest="URL_KEY", default="url", help="Key that contains URL")
parser.add_argument('-cid', dest="COLLECTION_UID", default="loc-john-and-ruby-lomax", help="Collection uid")
parser.add_argument('-bout', dest="OUTPUT_BASE_DIR", default="", help="Output base dir")
parser.add_argument('-aout', dest="OUTPUT_AUDIO_DIR", default="audio/samplepacks/", help="Output audio dir")
parser.add_argument('-dout', dest="OUTPUT_DATA_FILE", default="_data/%s.json", help="Output data file")
parser.add_argument('-asout', dest="OUTPUT_ASSETS_DIR", default="", help="Output data file")
parser.add_argument('-pout', dest="OUTPUT_PACKAGE_DIR", default="samplepacks/", help="Output package dir")
a = parser.parse_args()

_, items = readCsv(a.ITEM_DATA_FILE)
itemLookup = createLookup(items, a.ID_KEY)

OUTPUT_AUDIO_DIR = a.OUTPUT_BASE_DIR + a.OUTPUT_AUDIO_DIR + a.COLLECTION_UID + '/'
OUTPUT_DATA_FILE = a.OUTPUT_BASE_DIR + a.OUTPUT_DATA_FILE % a.COLLECTION_UID
OUTPUT_PACKAGE_DIR = a.OUTPUT_ASSETS_DIR + a.OUTPUT_PACKAGE_DIR
OUTPUT_WAV_AUDIO_DIR = a.OUTPUT_ASSETS_DIR + a.OUTPUT_AUDIO_DIR + a.COLLECTION_UID + '/'

makeDirectories([OUTPUT_AUDIO_DIR, OUTPUT_DATA_FILE, OUTPUT_PACKAGE_DIR, OUTPUT_WAV_AUDIO_DIR])

zipfilenames = getFilenames(a.SAMPLE_PACK_DIR + '*.zip')

jsonDataOut = {
    "packages": [],
    "clips": []
}
for zipfilename in zipfilenames:
    basefilename = os.path.basename(zipfilename)
    destFilename = OUTPUT_PACKAGE_DIR + basefilename
    # move zipfile over
    shutil.copyfile(zipfilename, destFilename)
    # # remove dest dir and copy over source dir
    # sourceDir = zipfilename[:(len(zipfilename)-4)] + "/"
    # destDir = destFilename[:(len(destFilename)-4)] + "/"
    # print("Moving %s to %s..." % (sourceDir, destDir))
    # removeDir(destDir)
    # shutil.copytree(sourceDir, destDir)
    basename = getBasename(zipfilename)
    format = basename.split('_')[-1]
    print('Processing %s' % format)
    label = 'Download in 16-bit .wav format' if format == 'wav' else 'Download in 192 Kbps .mp3 format'
    comment = 'Ideal for production' if format == 'wav' else 'Ideal if you would just like to preview and browse this collection'
    jsonDataOut["packages"].append({
        'filename': basefilename,
        'label': label,
        'size': getFilesizeString(zipfilename),
        'comment': comment
    })
    # move the phrase files over if mp3
    if format == "mp3":
        print('Moving mp3 files over...')
        audiofiles = getFilenames(a.SAMPLE_PACK_DIR + basename + '/excerpts/*.' + format)
        oneshots = getFilenames(a.SAMPLE_PACK_DIR + basename + '/one_shots/*.' + format)
        for afile in audiofiles:
            baseAfilename = os.path.basename(afile)
            destAfilename = OUTPUT_AUDIO_DIR + baseAfilename
            shutil.copyfile(afile, destAfilename)
            # item
            baseAname = getBasename(afile)
            itemId = baseAname.split('_')[1]
            timeStamp = baseAname.split('_')[-1].replace('-', ':')
            if timeStamp.startswith("00:"):
                timeStamp = timeStamp[3:]
            item = itemLookup[itemId]
            jsonDataOut["clips"].append({
                'filename': baseAfilename,
                'title': item['title'],
                'timestamp': timeStamp,
                'url': item[a.URL_KEY]
            })
        jsonDataOut['segmentCount'] = len(audiofiles)
        jsonDataOut['oneshotCount'] = len(oneshots)
        jsonDataOut['totalCount'] = len(audiofiles) + len(oneshots)

    elif format == "wav":
        print("Moving wav files over...")
        audiofiles = getFilenames(a.SAMPLE_PACK_DIR + basename + '/excerpts/*.' + format)
        for afile in audiofiles:
            baseAfilename = os.path.basename(afile)
            destAfilename = OUTPUT_WAV_AUDIO_DIR + baseAfilename
            shutil.copyfile(afile, destAfilename)

jsonDataOut["clips"] = sorted(jsonDataOut["clips"], key=lambda c: str(c['title']))
writeJSON(OUTPUT_DATA_FILE, jsonDataOut, pretty=True)
