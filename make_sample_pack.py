# -*- coding: utf-8 -*-

# File structure:
# {provider}_{collection_name}_{format}
#     - one_shots/
#         + {item_title}_{item_id}_{sequence}_{timestamp}.{format}
#             - title
#             - artist
#             - year
#     - attributions/
#         + {item_title}_{item_id}.txt
#             - title
#             - contributors
#             - year
#             - provider
#             - url
#             - rights and access
#     + {item_title}_{item_id}_{sequence}_{timestamp}.{format}
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

from lib.audio_utils import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-basedir', dest="BASE_DATA_DIR", default="data/", help="Base directory for each data file")
parser.add_argument('-cdata', dest="COLLECTION_DATA_FILE", default="collectiondata/citizen_dj_collections.csv", help="Input collection csv file")
parser.add_argument('-idata', dest="ITEM_DATA_FILE", default="metadata/loc_john-and-ruby-lomax.csv", help="Input collection items csv file")
parser.add_argument('-pdata', dest="PHRASE_DATA_FILE", default="phrasedata/loc_project_one_pd_av/%s.csv", help="Path for phrase data csv files")
parser.add_argument('-sdata', dest="SAMPLE_DATA_FILE", default="sampledata/loc_john-and-ruby-lomax_subset_64x64_grid.csv", help="Input collection samples csv file")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="path/to/samples/", help="Audio sample dir")
parser.add_argument('-tmp', dest="TEMP_DIR", default="tmp/samplepack/", help="Temp dir")
parser.add_argument('-id', dest="ID_KEY", default="id", help="Key that contains item identifier")
parser.add_argument('-sid', dest="SAMPLE_ID", default="sourceFilename", help="Key to match samples to item")
parser.add_argument('-ctmpl', dest="COLLECTION_TEMPLATE", default="templates/collection_readme_template.txt", help="Input template file for collection")
parser.add_argument('-itmpl', dest="ITEM_TEMPLATE", default="templates/item_readme_template.txt", help="Input template file for item")
parser.add_argument('-formats', dest="FORMATS", default="mp3,wav", help="List of formats to produce")
parser.add_argument('-mdb', dest="MATCH_DB", default=-16, type=int, help="Match decibels, -9999 for none")
parser.add_argument('-cmin', dest="MIN_CLIP_DUR", default=200, type=int, help="Minimum clip duration in ms")
parser.add_argument('-cmax', dest="MAX_CLIP_DUR", default=4000, type=int, help="Maximum clip duration in ms")
parser.add_argument('-provider', dest="PROVIDER", default="loc.gov", help="Provider name")
parser.add_argument('-cid', dest="COLLECTION_ID", default="john-and-ruby-lomax", help="Collection id")
parser.add_argument('-out', dest="OUTPUT_DIR", default="path/to/output/", help="Output dir")
a = parser.parse_args()

FORMATS = a.FORMATS.strip().split(',')
collectionTemplate = ""
with open(a.BASE_DATA_DIR+a.COLLECTION_TEMPLATE, 'r') as f:
    collectionTemplate = f.read()

itemTemplate = ""
with open(a.BASE_DATA_DIR+a.ITEM_TEMPLATE, 'r') as f:
    itemTemplate = f.read()

_, collections = readCsv(a.BASE_DATA_DIR+a.COLLECTION_DATA_FILE)
_, items = readCsv(a.BASE_DATA_DIR+a.ITEM_DATA_FILE)
_, samples = readCsv(a.BASE_DATA_DIR+a.SAMPLE_DATA_FILE)
PHRASE_PATH = a.BASE_DATA_DIR + a.PHRASE_DATA_FILE

collection = findWhere(collections, ("id", a.COLLECTION_ID))
if collection is None:
    print("Could not find %s" % a.COLLECTION_ID)
    sys.exit()

# group samples by item
samplesByItem = groupList(samples, 'filename')
samplesByItemLookup = createLookup(samplesByItem, 'filename')

# filter items
filenames = set(unique([s['filename'] for s in samples]))
items = [i for i in items if i['filename'] in filenames]
items = sorted(items, key=lambda i: i['title'])
itemLookup = createLookup(items, 'filename')

# retrieve phrases
print('Looking for valid phrases...')
phraseLookup = {}
for item in items:
    _, itemPhrases = readCsv(PHRASE_PATH % item['filename'])
    # filter phrases to just those that have samples
    validItemPhrases = []
    itemSamples = samplesByItemLookup[item['filename']]['items']
    itemSamples = sorted(itemSamples, key=lambda s: s['start'])
    for phrase in itemPhrases:
        pstart = phrase['start']
        pend = pstart + phrase['dur']
        for sample in itemSamples:
            if pstart <= sample['start'] < pend:
                validItemPhrases.append(phrase)
                break
    phraseLookup[item['filename']] = validItemPhrases

# parse stuff for item
for i, item in enumerate(items):
    items[i]['cleanTitle'] = stringToFilename(item['title'])
    artist = item['contributors'] if 'contributors' in item else item['creator']
    items[i]['contributors'] = artist.replace(' | ', '\n')
    items[i]['rights'] = collection['rights']
    items[i]['credit'] = collection['credit']
    # use performer as artist if exists, else use first
    if ' | ' in artist:
        persons = artist.split(' | ')
        artist = persons[0]
        for person in persons:
            if 'performer' in person.lower():
                artist = person
                break
    items[i]['tags'] = {'title': item['title'], 'artist': artist, 'album': collection['display'], 'year': item['year']}

removeDir(a.OUTPUT_DIR)
removeDir(a.TEMP_DIR)
makeDirectories([a.TEMP_DIR])

for format in FORMATS:
    folder_name = '{provider}_{collection_name}_{format}'.format(provider=a.PROVIDER, collection_name=a.COLLECTION_ID, format=format)
    folder_path = a.OUTPUT_DIR + folder_name '/'
    wav_folder_name = '{provider}_{collection_name}_wav'.format(provider=a.PROVIDER, collection_name=a.COLLECTION_ID)
    wav_folder_path = a.OUTPUT_DIR + wav_folder_name '/'
    attributions_path = folder_path+'attributions/'
    one_shot_path = folder_path+'one_shots/'
    makeDirectories([one_shot_path, attributions_path])

    # make main readme file
    collectionText = collectionTemplate.format(**collection)
    with open(folder_path+"README.txt", "w") as f:
        f.write(collectionText)

    # go through each item
    for item in items:
        # make attribution
        itemText = itemTemplate.format(**item)
        itemAttributePath = attributions_path + '%s_%s.txt' % (item['cleanTitle'], item[a.ID_KEY])
        with open(itemAttributePath, "w") as f:
            f.write(itemText)

        itemAudio = itemAudioDurationMs = None
        if format == 'wav':
            itemAudio = getAudio(a.MEDIA_DIRECTORY + item['filename'])
            itemAudioDurationMs = len(itemAudio)

        # make phrases and items
        itemPhrases = phraseLookup[item['filename']]
        phrasesTotal = max(100, len(itemPhrases))
        itemSamples = samplesByItemLookup[item['filename']]
        samplesTotal = max(100, len(itemPhrases))
        clips = []
        for j, phrase in enumerate(itemPhrases):
            clip = phrase.copy()
            clip['sequence'] = zeroPad(j+1, phrasesTotal)
            clip['dir'] = folder_path
            clip['wavdir'] = wav_folder_path
            clips.append(clip)
        for j, sample in enumerate(itemSamples):
            clip = sample.copy()
            clip['sequence'] = zeroPad(j+1, samplesTotal)
            clip['dir'] = folder_path+'one_shots/'
            clip['wavdir'] = wav_folder_path+'one_shots/'
            clips.append(clip)

        for j, clip in enumerate(clips):
            sequence = clip['sequence']
            timestamp = formatSeconds(clip['start']/1000.0, separator="-", retainHours=True)
            clipFilePath = clip['dir'] + '%s_%s_%s_%s.%s' % (item['cleanTitle'], item[a.ID_KEY], sequence, timestamp, format)
            clipTags = item['tags'].copy()
            clipTags['title'] = item['title'] + ' %s %s' % (sequence, timestamp)
            # if wav, build the audio clip
            if format == 'wav':
                # make clip
                cdur = lim(clip['dur'], (a.MIN_CLIP_DUR, a.MAX_CLIP_DUR))
                clipAudio = getAudioClip(itemAudio, clip['start'], cdur, itemAudioDurationMs)
                clipAudio = applyAudioProperties(clipAudio, {
                    "matchDb": a.MATCH_DB,
                    "fadeIn": min(100, roundInt(clip["dur"] * 0.1)),
                    "fadeOut": min(100, roundInt(clip["dur"] * 0.1))
                })
                clipAudio.export(clipFilePath, format=format, tags=clipTags)
            # if not wav, simply read the wav file and convert to other format
            else:
                clipFilenameWav = replaceFileExtension(os.path.basename(clipFilePath), '.wav')
                clipFilePathWav = clip['wavdir'] + clipFilenameWav
                clipAudio = getAudio(clipFilePathWav)
                if format == "mp3":
                    clipAudio.export(clipFilePath, format=format, tags=clipTags, bitrate="192k")
                else:
                    clipAudio.export(clipFilePath, format=format, tags=clipTags)

    # zip the directory
    zipdir = folder_path.rstrip('/')
    zipfilename = zipdir + '.zip'
    zipDir(zipfilename, zipdir)