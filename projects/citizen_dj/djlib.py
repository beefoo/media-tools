import inspect
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

def loadDrumPatterns(config):
    c = config
    drumPatterns = readJSON(c["drumPatternsFile"])
    drumPatterns = zipLists(drumPatterns["patterns"], drumPatterns["itemHeadings"])
    drumPatterns = filterByQueryString(drumPatterns, c["drumPatternsQuery"])
    drums = readJSON(c["drumsFile"])
    drumHeadings = drums["itemHeadings"]
    drums = filterByQueryString(drums["drums"], c["drumsQuery"])
    if len(drums) < 1:
        print("No drums found for this query %s" % c["drumsQuery"])
        return 0
    drums = drums[0]["instruments"]
    drums = zipLists(drums, drumHeadings)

    for i, drum in enumerate(drums):
        drums[i]["filename"] = c["drumsAudioDir"] + drum["filename"]

    drumsByInstrument = groupList(drums, "instrument")
    for i, group in enumerate(drumsByInstrument):
        instruments = sorted(group["items"], key=lambda item: item["priority"])
        drumsByInstrument[i]["prioritizedDrum"] = instruments[0]

    drumLookup = createLookup(drumsByInstrument, "instrument")
    for i, pattern in enumerate(drumPatterns):
        for j, bar in enumerate(pattern["bars"]):
            for k, note in enumerate(bar):
                for l, instrumentKey in enumerate(note):
                    drumPatterns[i]["bars"][j][k][l] = drumLookup[instrumentKey]["prioritizedDrum"] if instrumentKey in drumLookup else None

    return drumPatterns
