# -*- coding: utf-8 -*-

from math_utils import *
import numpy as np
import os
from PIL import Image

def clipsToFrame(p):
    clips = p["clips"]
    filename = p["filename"]
    saveFrame = p["saveFrame"]
    width = p["width"]
    height = p["height"]
    overwrite = p["overwrite"]
    im = None
    fileExists = os.path.isfile(filename) and not overwrite

    # frame already exists, read it directly
    if not fileExists:
        im = Image.new(mode="RGB", size=(width, height), color=(0, 0, 0))
        for clip in clips:
            video = clip["video"]
            videoDur = video.duration
            videoT = clip["t"]
            cw = roundInt(clip["w"])
            ch = roundInt(clip["h"])
            # check if we need to loop video clip
            if videoT > videoDur:
                videoT = videoT % videoDur
            # a numpy array representing the RGB picture of the clip
            try:
                videoPixels = video.get_frame(videoT)
            except IOError:
                print("Could not read pixels for %s at time %s" % (video.filename, videoT))
                videoPixels = np.zeros((ch, cw, 3), dtype='uint8')
            clipImg = Image.fromarray(videoPixels, mode="RGB")
            w, h = clipImg.size
            if w != cw or h != ch:
                clipImg = clipImg.resize((cw, ch))
            im.paste(clipImg, (roundInt(clip["x"]), roundInt(clip["y"])))

        if saveFrame:
            im.save(filename)
            print("Saved frame %s" % filename)


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
