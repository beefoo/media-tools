# -*- coding: utf-8 -*-

from math_utils import *
import os
from PIL import Image

def clipsToFrame(p):
    clips = p["clips"]
    filename = p["filename"]
    saveFrame = p["saveFrame"]
    width = p["width"]
    height = p["height"]
    im = None
    fileExists = os.path.isfile(filename)

    # frame already exists, read it directly
    if fileExists:
        im = Image.open(filename)

    else:
        im = Image.new(mode="RGB", size=(width, height), color=(0, 0, 0))
        for clip in clips:
            video = clip["video"]
            videoDur = video.duration
            videoT = clip["t"]
            # check if we need to loop video clip
            if videoT > videoDur:
                videoT = videoT % videoDur
            # a numpy array representing the RGB picture of the clip
            videoPixels = video.get_frame(videoT)
            clipImg = Image.fromarray(videoPixels, mode="RGB")
            clipImg = clipImg.resize((clip["w"], clip["h"]))
            im.paste(clipImg, (clip["x"], clip["y"]))

    if saveFrame and not fileExists:
        im.save(filename)

    return im

# resize video using fill method
def fillVideo(video, w, h):
    ratio = 1.0 * w / h
    vw, vh = video.size
    vratio = 1.0 * vw / vh

    # first, resize video
    newW = w
    newH = h
    if vratio > ratio:
        newW = h * vratio
    else:
        newH = w / vratio
    resized = video.resize((newW, newH))

    # and then crop
    x = 0
    y = 0
    if vratio > ratio:
        x = roundInt((newW - w) * 0.5)
    else:
        y = roundInt((newH - h) * 0.5)
    cropped = resized.crop(x, y, w, h)

    return cropped
