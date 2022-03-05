# -*- coding: utf-8 -*-

import argparse
import inspect
from matplotlib import pyplot as plt
from moviepy.editor import VideoFileClip
import numpy as np
import os
from PIL import Image, ImageEnhance
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.audio_utils import *
from lib.image_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.video_utils import *

parser = argparse.ArgumentParser()
parser.add_argument('-vf', dest="VIDEO_FILE", default="", help="Input video file")
parser.add_argument('-af', dest="AUDIO_FILE", default="", help="Input audio file")
parser.add_argument('-df', dest="AUDIO_DATA_FILE", default="", help="Input audio data file")
parser.add_argument('-frames', dest="OUTPUT_FRAME", default="tmp/kronos_wax_frames/frame.%s.png", help="Path to frames directory")
parser.add_argument('-width', dest="WIDTH", default=1920, type=int, help="Output width")
parser.add_argument('-height', dest="HEIGHT", default=1080, type=int, help="Output height")
parser.add_argument('-fps', dest="FPS", default=30, type=int, help="Frames per second")
parser.add_argument('-min', dest="MIN_ALPHA", default=0.01, type=float, help="Minimum frame alpha; decrease to increase motion trails")
parser.add_argument('-max', dest="MAX_ALPHA", default=0.8, type=float, help="Maximum frame alpha")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/kronos_wax.mp4", help="Path to output file")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just display details?")
parser.add_argument('-debug', dest="DEBUG", action="store_true", help="Spit out just one frame?")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing frames / audio?")
a = parser.parse_args()
aa = vars(a)

if a.AUDIO_DATA_FILE == "":
    aa["AUDIO_DATA_FILE"] = a.AUDIO_FILE

hopLength = 512
durationMs = getDurationFromAudioFile(a.AUDIO_FILE, accurate=True)

y, sr = loadAudioData(a.AUDIO_DATA_FILE)
dataDurationMs = getDurationFromAudioFile(a.AUDIO_DATA_FILE, accurate=True)
audioData = getStft(y, hop_length=hopLength)
audioDataLen = len(audioData)
maxPower = max(audioData)

# fig, ax = plt.subplots()  # Create a figure containing a single axes.
# x = np.arange(len(audioData))
# ax.plot(x, audioData)  # Plot some data on the axes.
# plt.show()

video = VideoFileClip(a.VIDEO_FILE, audio=False)
videoDurationMs = int(video.duration * 1000)

if a.OVERWRITE:
    removeFiles(a.OUTPUT_FRAME % "*")

makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE])


totalFrames = msToFrame(durationMs, a.FPS)
baseImage = Image.new(mode="RGB", size=(a.WIDTH, a.HEIGHT), color=(0, 0, 0))
for i in range(totalFrames):
    frame = i + 1
    filename = a.OUTPUT_FRAME % zeroPad(frame, totalFrames)
    n = i / (totalFrames-1)
    ms = frameToMs(i, a.FPS)

    # get power
    n = min(ms / dataDurationMs, 1.0)
    audioDataIndex = roundInt(n * (audioDataLen-1))
    npower = audioData[audioDataIndex] / maxPower
    npower = ease(npower)
    alpha = lerp((a.MIN_ALPHA, a.MAX_ALPHA), npower)

    # get video frame
    vt = ms / 1000.0
    if ms > videoDurationMs:
        vms = ms % videoDurationMs
        vt = vms / 1000.0
    videoPixels = video.get_frame(vt)
    frameIm = Image.fromarray(videoPixels, mode="RGB")
    frameIm = frameIm.resize((a.WIDTH, a.HEIGHT))
    enhancer = ImageEnhance.Brightness(frameIm)
    frameIm = enhancer.enhance(npower * 0.5 + 1)

    baseImage = Image.blend(baseImage, frameIm, alpha)
    baseImage.save(filename)
    printProgress(frame, totalFrames)

compileFrames(a.OUTPUT_FRAME, a.FPS, a.OUTPUT_FILE, getZeroPadding(totalFrames), audioFile=a.AUDIO_FILE)
