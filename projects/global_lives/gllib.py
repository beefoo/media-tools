
import inspect
from moviepy.editor import VideoFileClip
import numpy as np
import os
from PIL import Image, ImageDraw
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.audio_utils import *
from lib.collection_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.video_utils import *

def addCellDataToCollections(collections, cellsPerCollection, cellFilename, updateData=False):
    cells = []
    cellFieldnames = []
    cellsByCollection = None
    cellDataLookup = None
    cCount = len(collections)

    if not updateData:
        cellFieldnames, cells = readCsv(cellFilename)

    cellFieldnames = unionLists(cellFieldnames, ["collection", "col", "power"])

    if len(cells) > 1:
        cellsByCollection = groupList(cells, "collection")

    if cellsByCollection is not None and len(cellsByCollection) != cCount:
        print("Collection size mismatch: resetting cell data")
        cellsByCollection = None

    if cellsByCollection is not None:
        cellDataLookup = createLookup(cellsByCollection, "collection")
        for i, c in enumerate(collections):
            cdata = cellDataLookup[c["id"]]["items"]
            if len(cdata) != cellsPerCollection:
                print("Cell count mismatch in %s (%s != %s): resetting cell data" % (c["id"], len(cdata), cellsPerCollection))
                cellsByCollection = None
                break
            cdata = sorted(cdata, key=lambda cell: cell["col"])
            for j, cell in enumerate(c["cells"]):
                collections[i]["cells"][j]["power"] = cdata[j]["power"]

    if cellsByCollection is None or updateData:
        for i, c in enumerate(collections):
            print("Collection %s processing..." % (i+1))
            samples = flattenList([cell["samples"] for cell in c["cells"]])
            samples = getPowerFromSamples(samples)
            for s in samples:
                collections[i]["cells"][s["col"]]["samples"][s["index"]]["power"] = s["power"]
            for j, cell in enumerate(collections[i]["cells"]):
                values = [s["power"] for s in cell["samples"]]
                weights = [s["dur"] for s in cell["samples"]]
                cpower = weightedMean(values, weights=weights)
                collections[i]["cells"][j]["power"] = cpower
            printProgress(i+1, cCount)

        cellData = []
        for i, c in enumerate(collections):
            for j, cell in enumerate(c["cells"]):
                cellData.append({
                    "collection": c["id"],
                    "col": cell["col"],
                    "power": cell["power"]
                })
        writeCsv(cellFilename, cellData, cellFieldnames)

    # add normalized power
    for i, c in enumerate(collections):
        collections[i]["cells"] = addNormalizedValues(collections[i]["cells"], "power", "npower")

    return collections

def addCellsToCollections(collections, videos, cellsPerCollection):
    for i, c in enumerate(collections):
        cVideos = [v for v in videos if v["collection"] == c["id"]]
        cVideos = sorted(cVideos, key=lambda v: v["start"])
        cTotalDur = int(sum([v["duration"] for v in cVideos]))
        durPerCell = int(1.0 * cTotalDur / cellsPerCollection)
        print("%s has %s duration per cell" % (c["name"], formatSeconds(durPerCell)))
        cCells = []
        currentVideoIndex = 0
        currentVideoOffset = 0
        for j in range(cellsPerCollection):
            cellSamples = []
            cellDur = 0
            while cellDur < durPerCell and currentVideoIndex < len(cVideos):
                currentVideo = cVideos[currentVideoIndex]
                durLeftInVideo = currentVideo["duration"] - currentVideoOffset
                # Not enough time left in current video
                if durLeftInVideo < 1:
                    currentVideoIndex += 1
                    currentVideoOffset = 0
                    currentVideo = cVideos[currentVideoIndex]
                    durLeftInVideo = currentVideo["duration"]
                durLeftInCell = durPerCell - cellDur
                # we can finish the cell with the current video
                if durLeftInVideo > durLeftInCell:
                    cellSamples.append({
                        "filename": currentVideo["filename"],
                        "start": roundInt(currentVideoOffset * 1000),
                        "dur": int(durLeftInCell * 1000),
                        "videoDur": int(currentVideo["duration"] * 1000)
                    })
                    currentVideoOffset += durLeftInCell
                    cellDur += durLeftInCell
                    break
                # otherwise, we need to add the rest of video and go to the next video
                else:
                    cellSamples.append({
                        "filename": currentVideo["filename"],
                        "start": roundInt(currentVideoOffset * 1000),
                        "dur": int(durLeftInVideo * 1000),
                        "videoDur": int(currentVideo["duration"] * 1000)
                    })
                    currentVideoIndex += 1
                    currentVideoOffset = 0
                    cellDur += durLeftInVideo
            if cellDur < durPerCell * 0.9:
                print("   Warning: Cell %s of %s is too small (%s)" % (j+1, cellsPerCollection, formatSeconds(cellDur)))
            cellStart = 0
            for k, cs in enumerate(cellSamples):
                cellSamples[k]["index"] = k
                cellSamples[k]["row"] = c["row"]
                cellSamples[k]["col"] = j
                cellSamples[k]["cellStart"] = cellStart
                cellSamples[k]["end"] = cs["start"] + cs["dur"]
                cellSamples[k]["cellEnd"] = cellStart + cs["dur"]
                cellStart += cs["dur"]
            cCells.append({
                "row": c["row"],
                "col": j,
                "samples": cellSamples,
                "dur": cellStart
            })
        collections[i]["cells"] = cCells
    return collections

def addQueueToSamples(combinedSamples, queue):
    if len(queue) < 1:
        return combinedSamples
    first = queue[0]
    last = queue[-1]
    end = last["start"] + last["dur"]
    newSample = {}
    if len(queue) < 2:
        newSample = first.copy()
    else:
        newSample = {
            "filename": f["filename"],
            "col": first["col"],
            "start": first["start"],
            "dur": end - first["start"],
            "volumes": [(q["start"]-first["start"], q["volume"]) for q in queue]
        }
    combinedSamples.append(newSample)
    return combinedSamples

def collectionPowerToImg(collections, filename, cellsPerCollection):
    cCount = len(collections)
    rowH = 40
    colW = 10
    imgH = cCount * rowH
    imgW = cellsPerCollection * colW
    im = Image.new(mode="RGB", size=(imgW, imgH), color=(0, 0, 0))
    draw = ImageDraw.Draw(im)

    colors = [
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 0, 255),
        (0, 255, 255)
    ]
    colorCount = len(colors)

    for i, c in enumerate(collections):
        color = colors[i % colorCount]
        for j, cell in enumerate(c["cells"]):
            x = j * colW
            y = cell["ny"] * imgH
            cellH = cell["nsize"] * imgH
            draw.rectangle([x, y, x+colW, y+cellH], fill=color, outline=(0, 0, 0), width=1)

    im.save(filename)
    print("Saved %s" % filename)

def collectionToImg(collections, filename, cellsPerCollection, imgH=1080, margin=1):
    cCount = len(collections)
    cellH = int(imgH / cCount)
    aspectRatio = 640.0 / 360.0
    cellW = roundInt(cellH * aspectRatio)
    imgW = cellW * cellsPerCollection
    im = Image.new(mode="RGB", size=(imgW, imgH), color=(0, 0, 0))

    # take the first sample in each cell
    clips = []
    for c in collections:
        for cell in c["cells"]:
            clips.append(cell["samples"][0])
    filenames = groupList(clips, "filename")
    filecount = len(filenames)
    for i, f in enumerate(filenames):
        video = VideoFileClip(f["filename"], audio=False)
        videoDur = video.duration
        fclips = f["items"]
        for fclip in fclips:
            t = fclip["start"] + fclip["dur"]/2
            clipImg = getVideoClipImage(video, videoDur, {"width": cellW-margin*2, "height": cellH-margin*2}, t)
            x = fclip["col"] * cellW + margin
            y = fclip["row"] * cellH + margin
            im.paste(clipImg, (x, y))
        video.reader.close()
        del video
        printProgress(i+1, filecount)
    im.save(filename)
    print("Saved %s" % filename)

def getGLAudioSequence(collections, cellsPerCollection, sequenceStart, cellMs, offsetMs, a):
    cCount = len(collections)
    playSamples = []
    for i in range(cellsPerCollection):
        weights = [0 for j in range(cCount)]
        for j, c in enumerate(collections):
            weights[j] = (c["cells"][i]["power"], i)
        sweights = sorted(weights, key=lambda w: w[0], reverse=True)
        sweights = sweights[:a.MAX_TRACKS_PER_CELL]
        # # start and end time of cell in the sequence
        # cellSeqStartMs = sequenceStart + offsetMs + i * cellMs
        # cellSeqEndMs = cellSeqStartMs + cellMs
        # start and end time in the cell itself
        cellStartMs = offsetMs
        cellEndMs = cellStartMs + cellMs
        for j, w in enumerate(sweights):
            playWeight = 1.0 - 1.0 * j / (a.MAX_TRACKS_PER_CELL - 1)
            nvolume = ease(playWeight)
            volume = lerp(a.VOLUME_RANGE, nvolume)
            for sample in collections[w[1]]["cells"][i]["samples"]:
                # Check to see if sample is playing during this window
                if sample["cellStart"] > cellEndMs or sample["cellEnd"] < cellStartMs:
                    continue
                psample = sample.copy()

                # determine start
                start = sample["start"] + offsetMs - a.PADDING
                deltaStart = 0
                if cellStartMs > sample["cellStart"]:
                    deltaStart = cellStartMs - sample["cellStart"]
                    start += deltaStart
                start = max(0, start)

                # determine end
                dur = sample["dur"]-deltaStart
                if sample["cellEnd"] > cellEndMs:
                    deltaEnd = sample["cellEnd"] - cellEndMs
                    dur -= deltaEnd
                dur += a.PAD_AUDIO * 2
                end = start + dur
                end = min(end, sample["videoDur"])
                dur = end - start

                psample["ms"] = sequenceStart
                psample["volume"] = volume
                psample["start"] = start
                psample["dur"] = dur
                playSamples.append(psample)

    # combine samples that overlap
    combinedSamples = []
    filenames = groupList(playSamples, "filename")
    for f in filenames:
        fsamples = sorted(f["items"], key=lambda s: s["start"])
        queue = []
        for j, s in enumerate(fsamples):
            if len(queue) < 1 or (queue[-1]["start"] + queue[-1]["dur"]) >= s["start"]:
                queue.append(s)
            else:
                combinedSamples = addQueueToSamples(combinedSamples, queue)
                queue = [s]
        if len(queue) > 0:
            combinedSamples = addQueueToSamples(combinedSamples, queue)

    # add audio properties
    for i, s in enumerate(combinedSamples):
        combinedSamples[i]["ms"] = sequenceStart - a.PAD_AUDIO + roundInt(s["col"] * cellMs)
        combinedSamples[i]["fadeIn"] = min(a.PAD_AUDIO, int(s["dur"] * 0.5))
        combinedSamples[i]["fadeOut"] = min(a.PAD_AUDIO, int(s["dur"] * 0.5))
        combinedSamples[i]["matchDb"] = a.MATCH_DB

    return combinedSamples
