
from moviepy.editor import VideoFileClip
import multiprocessing
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import numpy as np
from PIL import Image
import sys

from lib.math_utils import *
from lib.processing_utils import *
from lib.video_utils import *

# Given a sample, shorten or make longer based on "scene detection",
# i.e. don't allow sample to go to the next scene and thus create a blinking effect
def analyzeAndAdjustVideoFileSamples(p, startKey, durKey, minDur, targetDur, varDur, frameW, frameH, fps, threads=1, overwrite=False, verbose=True, threshold=30.0):
    samples = p["samples"]
    fp = p["filepath"]
    fileIndex = p["fileIndex"]

    video = VideoFileClip(fp, audio=False)
    videoDur = video.duration
    msStep = frameToMs(1, fps, False)

    if verbose:
        print("Reading %s with %s samples" % (fp, len(samples)))

    for i, s in enumerate(samples):
        start = s["start"]
        dur = s["dur"] if s["dur"] > targetDur else int(math.ceil(1.0 * targetDur / s["dur"]) * s["dur"])
        variance = pseudoRandom(fileIndex + i, range=(0, varDur), isInt=True)
        end = start + dur + variance
        ms = start
        prev = None
        runningDur = 0
        newStart = start
        newEnd = end
        bestStart = None
        bestEnd = None
        while ms < end:
            t = roundInt(ms)
            im = getVideoClipImage(video, videoDur, {"width": frameW, "height": frameH}, t, resizeMode="warp", resampleType=Image.NEAREST)
            im = im.convert('HSV')
            pixels = np.array(im, dtype=np.uint8)
            meanHSV = np.mean(pixels, axis=(0,1)) # get the mean of each of the h, s, and v values
            meanHSV = np.mean(meanHSV) # then get the mean of those three values
            if prev is not None:
                delta = abs(meanHSV-prev)
                # we've reached the beginning of a new scene
                if delta >= threshold:
                    prevMs = ms-msStep
                    # sample is not long enough; make this the beginning instead
                    if runningDur < minDur:
                        print("Short break")
                        # keep track of the longest in case we find no good matches
                        if bestStart is None or (prevMs-newStart) > (bestEnd-bestStart):
                            bestStart = newStart
                            bestEnd = prevMs
                        runningDur = 0
                        newStart = ms
                    # otherwise, we have a valid end; break now
                    else:
                        print("Valid break")
                        newEnd = prevMs
                        break
            prev = meanHSV
            ms += msStep
            runningDur += msStep

        # in the case we cannot find any samples long enough, take the longest one
        if bestStart is not None and (bestEnd-bestStart) > (newEnd-newStart):
            print("No valid breaks")
            newStart = bestStart
            newEnd = bestEnd

        samples[i][startKey] = roundInt(newStart)
        samples[i][durKey] = roundInt(newEnd-newStart)
        # print("--")

    # close video to free up memory
    video.reader.close()
    del video

    return samples

def analyzeAndAdjustVideoSamples(samples, startKey, durKey, minDur, targetDur, varDur, frameW, frameH, fps, threads=1, overwrite=False):
    # find unique filepaths
    ufilepaths = list(set([s["filepath"] for s in samples]))
    files = [{
        "samples": [s for s in samples if s["filepath"]==fp],
        "filepath": fp,
        "fileIndex": i
    } for i, fp in enumerate(ufilepaths)]
    fileCount = len(files)
    print("%s unique files" % fileCount)

    usamples = []
    threads = getThreadCount(threads)
    if threads > 1:
        pool = ThreadPool(threads)
        partialDef = partial(analyzeAndAdjustVideoFileSamples, startKey=startKey, durKey=durKey, minDur=minDur, targetDur=targetDur, varDur=varDur, frameW=frameW, frameH=frameH, fps=fps, threads=threads, overwrite=overwrite)
        usamples = pool.map(partialDef, files)
        usamples = [item for sublist in usamples for item in sublist]
        pool.close()
        pool.join()
    else:
        for i, p in enumerate(files):
            usamples += analyzeAndAdjustVideoFileSamples(p, startKey, durKey, minDur, targetDur, varDur, frameW, frameH, fps, threads, overwrite)
            printProgress(i+1, fileCount)
    return usamples
