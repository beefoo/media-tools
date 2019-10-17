# -*- coding: utf-8 -*-

import argparse
from functools import partial
from moviepy.editor import VideoFileClip, CompositeVideoClip
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
from PIL import Image, ImageDraw, ImageFont
from pprint import pprint
import subprocess
import sys

from lib.collection_utils import *
from lib.color_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.text_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/item.mp4", help="Input media file")
parser.add_argument('-sdata', dest="SAMPLE_DATA_FILE", default="path/to/sampledata.csv", help="Input csv sampldata file")
parser.add_argument('-pdata', dest="PHRASE_DATA_FILE", default="", help="Input csv phrase data file; blank if none")
parser.add_argument('-outframe', dest="OUTPUT_FRAME", default="tmp/item_viz/frame.%s.png", help="Temporary output frames pattern")
parser.add_argument('-width', dest="WIDTH", default=1280, type=int, help="Output video width")
parser.add_argument('-height', dest="HEIGHT", default=720, type=int, help="Output video height")
parser.add_argument('-fsize', dest="FONT_SIZE", default=24, type=int, help="Font size of timecode")
parser.add_argument('-speed', dest="SPEED", default=48.0, type=float, help="Speed of viz in pixels per second")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/item_viz.mp4", help="Output media file")
parser.add_argument('-quality', dest="QUALITY", default="high", help="High quality is slower")
parser.add_argument('-threads', dest="THREADS", default=3, type=int, help="Amount of parallel frames to process")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just view statistics?")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing frames?")
addTextArguments(parser)
a = parser.parse_args()
aa = vars(a)

MARGIN = min(roundInt(a.HEIGHT * 0.1), 20)
PHRASE_HEIGHT = MARGIN * 2

fieldNames, sampledata = readCsv(a.SAMPLE_DATA_FILE)
phrasedata = []
if len(a.PHRASE_DATA_FILE) > 0:
    _, phrasedata = readCsv(a.PHRASE_DATA_FILE)
    phrasedata = addNormalizedValues(phrasedata, "clarity", "nclarity")
hasPhrases = len(phrasedata) > 0
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE])

# determine video properties from the first clip
baseVideo = VideoFileClip(a.INPUT_FILE)
width, height = baseVideo.size
fps = round(baseVideo.fps, 2)
duration = baseVideo.duration
print("Base video: (%s x %s) %sfps %s" % (width, height, fps, formatSeconds(duration)))

if a.PROBE:
    sys.exit()

# Make the base video smaller and place in the center-ish
vratio = 1.0 * width / height
vh = roundInt(a.HEIGHT / 2.0)
vw = roundInt(vh * vratio)
vx = roundInt((a.WIDTH - vw) * 0.5)
vy = roundInt((a.HEIGHT - vh) * 0.25)
baseVideo = baseVideo.resize((vw, vh)).set_pos((vx, vy))

# Determine size/positioning of timecode text
font = ImageFont.truetype(font=a.FONT_DIR+a.DEFAULT_FONT_FILE, size=a.FONT_SIZE, layout_engine=ImageFont.LAYOUT_RAQM)
ftemplate = "00:00" if duration < 60 * 60 else "00:00:00"
fwidth, fheight = font.getsize(ftemplate)
tx = roundInt((a.WIDTH - fwidth) * 0.5)
ty = vy + vh + MARGIN

# Assign times, colors, and dimensions to sampledata
sy = ty + fheight + MARGIN
maxSHeight = a.HEIGHT - sy - MARGIN * 0.5
if hasPhrases:
    maxSHeight = a.HEIGHT - PHRASE_HEIGHT - sy - MARGIN
if maxSHeight < 10:
    print("Data height too small")
    sys.exit()
sampledata = addNormalizedValues(sampledata, "clarity", "nclarity")
sampledata = addNormalizedValues(sampledata, "power", "npower")
totalSequenceWidth = duration * a.SPEED
cx = a.WIDTH * 0.5
seqX0 = cx
seqX1 = cx - totalSequenceWidth
for i, s in enumerate(sampledata):
    sampledata[i]["color"] = getColorGradientValue(s["nclarity"])
    # determine pos and size
    nx = s["start"] / 1000.0 / duration
    nw = s["dur"] / 1000.0 / duration
    nh = s["npower"]
    myH = max(roundInt(maxSHeight * nh), 4)
    sampledata[i]["sY"] = roundInt(sy + (maxSHeight - myH))
    sampledata[i]["sX"] = roundInt(totalSequenceWidth * nx)
    sampledata[i]["sW"] = roundInt(totalSequenceWidth * nw)
    sampledata[i]["sH"] = myH

# calculate dimensions for phrase data
for i, p in enumerate(phrasedata):
    nx = p["start"] / 1000.0 / duration
    nw = p["dur"] / 1000.0 / duration
    phrasedata[i]["sY"] = roundInt(sy + maxSHeight + MARGIN)
    phrasedata[i]["sW"] = roundInt(totalSequenceWidth * nw)
    phrasedata[i]["sX"] = roundInt(totalSequenceWidth * nx)
    phrasedata[i]["sH"] = roundInt(PHRASE_HEIGHT)
    phrasedata[i]["color"] = getColorGradientValue(p["nclarity"])

# Generate annotation frames
frameProps = []
totalFrames = msToFrame(roundInt(duration*1000), fps)
for i in range(totalFrames):
    frame = i+1
    filename = a.OUTPUT_FRAME % zeroPad(frame, totalFrames)
    frameProps.append({
        "frame": frame,
        "filename": filename
    })

def doFrame(p, totalFrames, drawData):
    global a
    global MARGIN
    global cx
    global duration
    global seqX0
    global seqX1
    global font
    global tx
    global ty
    global sy
    global maxSHeight

    if os.path.isfile(p["filename"]):
        return

    im = Image.new(mode="RGB", size=(a.WIDTH, a.HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(im)
    nprogress = 1.0 * (p["frame"] - 1) / (totalFrames - 1)

    # draw text
    seconds = duration * nprogress
    timestring = formatSeconds(seconds)
    draw.text((tx, ty), timestring, font=font, fill=(255, 255, 255))

    xoffset = lerp((seqX0, seqX1), nprogress)
    for s in drawData:
        if s["sH"] <= 0:
            continue
        x0 = s["sX"] + xoffset
        x1 = x0 + s["sW"]
        if x0 < a.WIDTH and x1 > 0:
            draw.rectangle([x0, s["sY"], x1, s["sY"]+s["sH"]], fill=s["color"], outline=(0,0,0), width=1)

    draw.line([(cx, sy), (cx, sy + maxSHeight)], fill=(255, 255, 255), width=1)

    del draw
    im.save(p["filename"])

    sys.stdout.write('\r')
    sys.stdout.write("Wrote %s to file" % p["filename"])
    sys.stdout.flush()

if a.OVERWRITE:
    removeFiles(a.OUTPUT_FRAME % "*")

drawData = sampledata + phrasedata

threads = getThreadCount(a.THREADS)
pool = ThreadPool(threads)
pclipsToFrame = partial(doFrame, totalFrames=totalFrames, drawData=drawData)
pool.map(pclipsToFrame, frameProps)
pool.close()
pool.join()

annotationVideoFn = appendToBasename(a.OUTPUT_FILE, "_annotation")
if a.OVERWRITE or not os.path.isfile(annotationVideoFn):
    compileFrames(a.OUTPUT_FRAME, fps, annotationVideoFn, getZeroPadding(totalFrames))
annotationVideo = VideoFileClip(annotationVideoFn, audio=False)

clips = [annotationVideo, baseVideo]
video = CompositeVideoClip(clips, size=(a.WIDTH, a.HEIGHT))
video = video.set_duration(duration)
if a.QUALITY == "high":
    video.write_videofile(a.OUTPUT_FILE, preset="slow", audio_bitrate="256k", audio_fps=48000, bitrate="19820k")
else:
    video.write_videofile(a.OUTPUT_FILE)
print("Wrote %s to file" % a.OUTPUT_FILE)
