# -*- coding: utf-8 -*-

from functools import partial
from lib.cache_utils import *
from lib.clip import *
from lib.gpu_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from moviepy.editor import VideoFileClip
import multiprocessing
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import numpy as np
import os
from PIL import Image, ImageFilter
from pprint import pprint
import subprocess
import sys

def addGridPositions(clips, cols, width, height, offsetX=0, offsetY=0, marginX=0, marginY=0):
    rows = ceilInt(1.0 * len(clips) / cols)
    cellW = 1.0 * width / cols
    cellH = 1.0 * height / rows
    for i, c in enumerate(clips):
        row = int(i / cols)
        col = i % cols
        clips[i]["col"] = col
        clips[i]["row"] = row
        clips[i]["x"] = col * cellW + marginX*0.5 + offsetX
        clips[i]["y"] = row * cellH + marginY*0.5 + offsetY
        clips[i]["width"] = cellW - marginX
        clips[i]["height"] = cellH - marginY
        clips[i]["nx"] = 1.0 * col / (cols-1)
        clips[i]["ny"] = 1.0 * row / (rows-1)
    return clips

def addVideoArgs(parser):
    parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
    parser.add_argument('-ss', dest="EXCERPT_START", type=float, default=-1, help="Excerpt start in seconds")
    parser.add_argument('-sd', dest="EXCERPT_DUR", type=float, default=-1, help="Excerpt duration in seconds")
    parser.add_argument('-vol', dest="VOLUME", type=float, default=1.0, help="Master volume applied to all clips")
    # parser.add_argument('-sort', dest="SORT", default="", help="Query string to sort by")
    parser.add_argument('-count', dest="COUNT", default=-1, type=int, help="Target total sample count, -1 for everything")
    # parser.add_argument('-filter', dest="FILTER", default="", help="Query string to filter by")
    parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/sample/", help="Input file")
    parser.add_argument('-aspect', dest="ASPECT_RATIO", default="16:9", help="Aspect ratio of each cell")
    parser.add_argument('-width', dest="WIDTH", default=1920, type=int, help="Output video width")
    parser.add_argument('-height', dest="HEIGHT", default=1080, type=int, help="Output video height")
    parser.add_argument('-fps', dest="FPS", default=30, type=int, help="Output video frames per second")
    parser.add_argument('-frames', dest="SAVE_FRAMES", action="store_true", help="Save frames?")
    parser.add_argument('-outframe', dest="OUTPUT_FRAME", default="tmp/sample/frame.%s.png", help="Output frames pattern")
    parser.add_argument('-out', dest="OUTPUT_FILE", default="output/sample.mp4", help="Output media file")
    parser.add_argument('-threads', dest="THREADS", default=1, type=int, help="Amount of parallel frames to process (too many may result in too many open files)")
    parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing frames?")
    parser.add_argument('-ao', dest="AUDIO_ONLY", action="store_true", help="Render audio only?")
    parser.add_argument('-vo', dest="VIDEO_ONLY", action="store_true", help="Render video only?")
    parser.add_argument('-cache', dest="CACHE_VIDEO", action="store_true", help="Cache video clips?")
    parser.add_argument('-cd', dest="CACHE_DIR", default="tmp/cache/", help="Dir for caching data")
    parser.add_argument('-cf', dest="CACHE_FILE", default="clip_cache.p", help="File for caching data")
    parser.add_argument('-verifyc', dest="VERIFY_CACHE", action="store_true", help="Add a step for verifying existing cache data?")
    parser.add_argument('-rand', dest="RANDOM_SEED", default=1, type=int, help="Random seed to use for pseudo-randomness")
    parser.add_argument('-pad0', dest="PAD_START", default=1000, type=int, help="Pad the beginning")
    parser.add_argument('-pad1', dest="PAD_END", default=3000, type=int, help="Pad the end")
    parser.add_argument('-rvb', dest="REVERB", default=80, type=int, help="Reverberence (0-100)")
    parser.add_argument('-debug', dest="DEBUG", action="store_true", help="Debug mode?")
    parser.add_argument('-mdb', dest="MATCH_DB", default=-16, type=int, help="Match decibels, -9999 for none")

def alphaMask(im, mask):
    w, h = im.size
    transparentImg = Image.new(mode="RGBA", size=(w, h), color=(0, 0, 0, 0))
    mw, mh = mask.size
    if mw != w or mh != h:
        mask = mask.resize((w, h), PIL.Image.BICUBIC)
    return Image.composite(im, transparentImg, mask)

def applyEffects(im, clip):
    im = updateAlpha(im, getAlpha(clip))
    angle = getRotation(clip)
    blur = getValue(clip, "blur", 0)
    mask = getValue(clip, "mask", None)
    if mask:
        im = alphaMask(im, mask)
    x = clip["x"]
    y = clip["y"]
    if angle > 0.0 or blur > 0.0:
        cx, cy = getCenter(clip)
        bx, by, bw, bh = bboxRotate(cx, cy, clip["width"], clip["height"], 45.0) # make the new box size as big as if it was rotated 45 degrees
        im = resizeCanvas(im, roundInt(bw), roundInt(bh)) # resize canvas to account for expansion from rotation or blur
        im = rotateImage(im, angle)
        im = blurImage(im, blur)
        x = bx
        y = by
    return (im, x, y)

def blurImage(im, radius):
    if radius > 0.0:
        im = im.filter(ImageFilter.GaussianBlur(radius=radius))
    return im

def clipsToFrame(params, pixelData):
    p, clips = params
    filename = p["filename"]
    width = p["width"]
    height = p["height"]
    overwrite = p["overwrite"] if "overwrite" in p else False
    verbose = p["verbose"] if "verbose" in p else False
    debug = p["debug"] if "debug" in p else False
    im = None
    fileExists = os.path.isfile(filename) and not overwrite

    # frame already exists, read it directly
    if not fileExists:
        im = Image.new(mode="RGBA", size=(width, height), color=(0, 0, 0, 255))
        im = clipsToFrameGPU(clips, width, height, pixelData)
        im = im.convert("RGB")
        im.save(filename)
        print("Saved frame %s" % filename)

    return True

def clipsToFrameGPU(clips, width, height, clipsPixelData, precision=5):
    pixelData = []
    properties = []
    offset = 0
    c = 3
    precisionMultiplier = int(10 ** precision)

    _x, _y, _w, _h, _alpha, _tn, _z = (0, 1, 2, 3, 4, 5, 6)

    # filter out clips with no pixels, or zero [width, height, alpha]
    # keep track of how many pixels we'll need
    indices = []
    pixelCount = 0
    for i in range(len(clips)):
        clip = clips[i]
        frameCount = len(clipsPixelData[i])
        if frameCount > 0 and clip[_w] > 0 and clip[_h] > 0 and clip[_alpha] > 0:
            indices.append(i)
            h, w, c = clipsPixelData[i][roundInt(clip[_tn] * (frameCount-1))].shape
            pixelCount += int(h*w*c)

    validCount = len(indices)
    propertyCount = 9
    properties = np.zeros((validCount, propertyCount), dtype=np.int32)
    pixelData = np.zeros(pixelCount, dtype=np.uint8)
    for i, clipIndex in enumerate(indices):
        clip = clips[clipIndex]
        clipPixelData = clipsPixelData[clipIndex]
        frameCount = len(clipPixelData)
        x, y, tw, th, alpha, tn, zindex = tuple(clip)
        pixels = clipPixelData[roundInt(tn * (frameCount-1))]
        h, w, c = pixels.shape
        alpha = roundInt(alpha*255)
        # # not ideal, but don't feel like implementing blur/rotation in opencl; just use PIL's algorithm
        # if "rotation" in clip and clip["rotation"] % 360 > 0 or "blur" in clip and clip["blur"] > 0.0:
        #     im = Image.fromarray(pixels, mode="RGB")
        #     im, x, y = applyEffects(im, clip)
        #     pixels = np.array(im)
        #     w0 = w
        #     h0 = h
        #     h, w, c = pixels.shape
        #     tw = roundInt(1.0 * w / w0 * tw)
        #     th = roundInt(1.0 * h / h0 * th)
        # print("%s, %s, %s" % pixels.shape)
        # print("%s, %s, %s, %s" % (x, y, tw, th))

        properties[i] = np.array([offset, roundInt(x*precisionMultiplier), roundInt(y*precisionMultiplier), w, h, roundInt(tw*precisionMultiplier), roundInt(th*precisionMultiplier), alpha, zindex])

        px0 = offset
        px1 = px0 + int(h*w*c)
        pixelData[px0:px1] = pixels.reshape(-1)
        offset += int(h*w*c)

    pixels = clipsToImageGPU(width, height, pixelData, properties, c, precision)
    return Image.fromarray(pixels, mode="RGB")

def compileFrames(infile, fps, outfile, padZeros, audioFile=None):
    print("Compiling frames...")
    padStr = '%0'+str(padZeros)+'d'
    if audioFile:
        command = ['ffmpeg','-y',
                    '-framerate',str(fps)+'/1',
                    '-i',infile % padStr,
                    '-i',audioFile,
                    '-c:v','libx264',
                    '-r',str(fps),
                    '-pix_fmt','yuv420p',
                    '-c:a','aac',
                    '-q:v','1',
                    '-b:a', '192k',
                    '-shortest',
                    outfile]
    else:
        command = ['ffmpeg','-y',
                    '-framerate',str(fps)+'/1',
                    '-i',infile % padStr,
                    '-c:v','libx264',
                    '-r',str(fps),
                    '-pix_fmt','yuv420p',
                    '-q:v','1',
                    outfile]
    print(" ".join(command))
    finished = subprocess.check_call(command)
    print("Done.")

def fillImage(img, w, h):
    vw, vh = img.size

    if vw == w and vh == h:
        return img

    ratio = 1.0 * w / h
    vratio = 1.0 * vw / vh

    # first, resize video
    newW = w
    newH = h
    if vratio > ratio:
        newW = h * vratio
    else:
        newH = w / vratio
    resized = img.resize((roundInt(newW), roundInt(newH)))

    # and then crop
    x = 0
    y = 0
    if vratio > ratio:
        x = roundInt((newW - w) * 0.5)
    else:
        y = roundInt((newH - h) * 0.5)
    x1 = x + w
    y1 = y + h
    cropped = resized.crop((x, y, x1, y1))

    return cropped

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
    resized = video.resize((roundInt(newW), roundInt(newH)))

    # and then crop
    x = 0
    y = 0
    if vratio > ratio:
        x = roundInt((newW - w) * 0.5)
    else:
        y = roundInt((newH - h) * 0.5)
    cropped = resized.crop(x, y, w, h)

    return cropped

def frameToMs(frame, fps, roundResult=True):
    result = (1.0 * frame / fps) * 1000.0
    if roundResult:
        result = roundInt(result)
    return result

def getAlpha(clip):
    alpha = clip["alpha"] if "alpha" in clip and clip["alpha"] < 1.0 else 1.0
    return roundInt(alpha*255)

def getCenter(clip):
    cx = clip["x"] + clip["width"] * 0.5
    cy = clip["y"] + clip["height"] * 0.5
    return (cx, cy)

def getDurationFromFile(filename, accurate=False):
    result = 0
    if os.path.isfile(filename):
        if accurate:
            try:
                video = VideoFileClip(filename, audio=False)
                result = video.duration
                video.reader.close()
                del video
            except IOError as e:
                print("I/O error({0}): {1}".format(e.errno, e.strerror))
                result = 0
        else:
            command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', filename]
            result = subprocess.check_output(command).strip()
    return float(result)

def getEmptyVideoClipImage(clip):
    cw = roundInt(clip["width"])
    ch = roundInt(clip["height"])
    videoPixels = np.zeros((ch, cw, 4), dtype='uint8')
    clipImg = Image.fromarray(videoPixels, mode="RGBA")
    return clipImg

# e.g. returns ['audio', 'video'] for a/v files
def getMediaTypes(filename):
    result = []
    if os.path.isfile(filename):
        command = ['ffprobe', '-loglevel', 'error', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', filename]
        # print(" ".join(command))
        result = subprocess.check_output(command).splitlines()
    return result

def getSolidPixels(color, width=100, height=100):
    dim = len(color)
    pixels = np.zeros((height, width, dim))
    pixels[:,:] = color
    return pixels

def getVideoClipImage(video, videoDur, clip, t=None):
    videoT = clip["t"] / 1000.0 if t is None else t / 1000.0
    cw = roundInt(clip["width"])
    ch = roundInt(clip["height"])
    delta = videoDur - videoT
    # check if we need to loop video clip
    if delta < 0:
        videoT = videoT % videoDur
    # hack: ffmpeg sometimes has trouble reading the very end of the video; choose 500ms from end
    elif delta < 0.5:
        videoT = videoDur - 0.5
    # a numpy array representing the RGB picture of the clip
    try:
        videoPixels = video.get_frame(videoT)
    except IOError:
        print("Could not read pixels for %s at time %s" % (video.filename, videoT))
        videoPixels = np.zeros((ch, cw, 3), dtype='uint8')
    clipImg = Image.fromarray(videoPixels, mode="RGB")
    clipImg = fillImage(clipImg, cw, ch)
    return clipImg

def getRotation(clip):
    rotation = clip["rotation"] if "rotation" in clip else 0.0
    angle = rotation % 360.0
    return angle

def hasAudio(filename):
    return ("audio" in getMediaTypes(filename))

def isClipVisible(clip, width, height):
    isInFrame = clip["x"]+clip["width"] > 0 and clip["y"]+clip["height"] > 0 and clip["x"] < width and clip["y"] < height
    isOpaque = getAlpha(clip) > 0
    return isInFrame and isOpaque

def loadVideoPixelData(clips, fps, cacheDir="tmp/", width=None, height=None, verifyData=True, cache=True):
    # load videos
    filenames = list(set([clip.props["filename"] for clip in clips]))
    fileCount = len(filenames)
    msStep = frameToMs(1, fps, False)
    clipsPixelData = [None] * len(clips)

    # only open one video at a time
    for i, fn in enumerate(filenames):
        # check for cache fors filename
        cacheFn = cacheDir + os.path.basename(fn) + ".p"
        loaded = False
        fileCacheData = []
        if cache:
            loaded, fileCacheData = loadCacheFile(cacheFn)
        vclips = [c for c in clips if fn==c.props["filename"]]
        valid = True

        # Verify loaded data
        if loaded and verifyData:
            print("Verifying cache data for %s..." % cacheFn)
            clipTimesSet = set(fileCacheData[0])
            for clip in vclips:
                start = clip.props["start"]
                end = start + clip.props["dur"]
                ms = start
                while ms < end:
                    t = roundInt(ms)
                    ms += msStep
                    if t not in clipTimesSet:
                        print("%s not found in %s. Resetting cache data" % (t, cacheFn))
                        loaded = False
                        break
                    index = fileCacheData[0].index(t)
                    clipH, clipW, _ = fileCacheData[1][index].shape
                    if roundInt(clip.props["width"]) > clipW:
                        print("Clip width is too small (%s > %s) for %s at %s. Resetting cache data" % (clip.props["width"], clipW, cacheFn, t))
                        loaded = False
                        break
                    # TODO: Add check for aspect ratio?
                if not loaded:
                    break
            print("Verified cache data for %s" % cacheFn)

        if not loaded:
            print("No cache for %s, rebuilding..." % fn)
            video = VideoFileClip(fn, audio=False)
            videoDur = video.duration
            clipTimes = []
            clipPixels = []

            # Already loaded cache data; append to it rather than overwrite it
            if len(fileCacheData) > 0:
                clipTimes, clipPixels = fileCacheData

            # extract frames from videos
            vclipCount = len(vclips)
            for j, clip in enumerate(vclips):
                start = clip.props["start"]
                end = start + clip.props["dur"]
                ms = start
                while ms < end:
                    fclip = clip.props.copy()
                    t = roundInt(ms)
                    ms += msStep
                    # already exists, check size
                    existIndex = None
                    if t in set(clipTimes):
                        existIndex = clipTimes.index(t)
                        clipH, clipW, _ = clipPixels[existIndex].shape
                        if roundInt(fclip["width"]) <= clipW:
                            continue
                    clipImg = getVideoClipImage(video, videoDur, fclip, t)
                    if existIndex is not None:
                        clipPixels[existIndex] = np.array(clipImg, dtype=np.uint8)
                    else:
                        clipTimes.append(t)
                        clipPixels.append(np.array(clipImg, dtype=np.uint8))
                printProgress(j+1, vclipCount)

            # save cache data
            fileCacheData = (clipTimes, clipPixels)

            if cache:
                saveCacheFile(cacheFn, fileCacheData, overwrite=True)

            # close video to free up memory
            video.reader.close()
            del video

        # assign pixel data to clips
        for clip in vclips:
            start = clip.props["start"]
            end = start + clip.props["dur"]
            ms = start
            pixelData = []
            while ms < end:
                t = roundInt(ms)
                ms += msStep
                index = fileCacheData[0].index(t)
                pixelData.append(fileCacheData[1][index])
            clipsPixelData[clip.props["index"]] = pixelData
            # clip.setProp("framePixelData", pixelData)

        printProgress(i+1, fileCount)

    print("Finished loading pixel data.")
    return clipsPixelData

def loadVideoPixelDataFromFrames(frames, clips, fps, cacheDir="tmp/", cacheFile="clip_cache.p", verifyData=True, cache=True, debug=False):
    frameCount = len(frames)
    clipCount = len(clips)

    loaded = False
    clipSequence = []
    if cache:
        loaded, clipSequence = loadCacheFile(cacheDir+cacheFile)

    if not loaded or clipSequence.shape[0] != frameCount or clipSequence.shape[1] != clipCount:
        print("Calculating clip size/position from frame sequence...")
        clipSequence = np.zeros((frameCount, clipCount, 7), dtype=np.float32) # will store each clip's x/y/width/height/alpha for each frame
        for i, frame in enumerate(frames):
            frameClips = clipsToDicts(clips, frame["ms"])
            for clip in frameClips:
                if isClipVisible(clip, frame["width"], frame["height"]):
                    clipSequence[i, clip["index"], 0] = clip["x"]
                    clipSequence[i, clip["index"], 1] = clip["y"]
                    clipSequence[i, clip["index"], 2] = clip["width"]
                    clipSequence[i, clip["index"], 3] = clip["height"]
                    clipSequence[i, clip["index"], 4] = clip["alpha"]
                    clipSequence[i, clip["index"], 5] = clip["tn"]
                    clipSequence[i, clip["index"], 6] = clip["zindex"] if "zindex" in clip else clip["index"]+1
            printProgress(i+1, frameCount)
        # get max dimension of each clip

        if cache:
            saveCacheFile(cacheDir+cacheFile, clipSequence, overwrite=True)

    if debug:
        clipsPixelData = np.zeros((clipCount, 1, 1, 3))
        for i in range(clipCount):
            clipsPixelData[i, 0, 0] = getRandomColor(i)
    else:
        clipMaxes = np.amax(clipSequence, axis=0)
        # update clips with max width/height
        for i, clip in enumerate(clips):
            clip.setProp("width", clipMaxes[clip.props["index"], 2])
            clip.setProp("height", clipMaxes[clip.props["index"], 3])
        clipsPixelData = loadVideoPixelData(clips, fps, cacheDir=cacheDir, verifyData=verifyData, cache=cache)

    return (clipSequence, clipsPixelData)

def msToFrame(ms, fps):
    return roundInt((ms / 1000.0) * fps)

def parseVideoArgs(args):
    d = vars(args)
    aspectW, aspectH = tuple([int(p) for p in args.ASPECT_RATIO.split(":")])
    d["ASPECT_RATIO"] = 1.0 * aspectW / aspectH
    d["THREADS"] = min(args.THREADS, multiprocessing.cpu_count()) if args.THREADS > 0 else multiprocessing.cpu_count()
    d["AUDIO_OUTPUT_FILE"] = args.OUTPUT_FILE.replace(".mp4", ".mp3")
    d["MS_PER_FRAME"] = frameToMs(1, args.FPS, False)
    d["CACHE_VIDEO"] = args.CACHE_VIDEO
    d["MATCH_DB"] = args.MATCH_DB if args.MATCH_DB > -9999 else False

def pasteImage(im, clipImg, x, y):
    width, height = im.size
    # create a staging image at the same size of the base image, so we can blend properly
    stagingImg = Image.new(mode="RGBA", size=(width, height), color=(0, 0, 0, 0))
    stagingImg.paste(clipImg, (roundInt(x), roundInt(y)))
    im = Image.alpha_composite(im, stagingImg)
    return im

def processFrames(params, clipSequence, clipsPixelData, threads=1, verbose=True):
    count = len(params)
    print("Processing %s frames" % count)

    zippedParams = zip(params, clipSequence)

    if threads > 1:
        pool = ThreadPool(threads)
        pclipsToFrame = partial(clipsToFrame, pixelData=clipsPixelData)
        results = pool.map(pclipsToFrame, zippedParams)
        pool.close()
        pool.join()
    else:
        for i, p in enumerate(zippedParams):
            clipsToFrame(p, pixelData=clipsPixelData)
            if verbose:
                printProgress(i+1, count)

def resizeCanvas(im, cw, ch):
    canvasImg = Image.new(mode="RGBA", size=(cw, ch), color=(0, 0, 0, 0))
    w, h = im.size
    x = roundInt((cw - w) * 0.5)
    y = roundInt((ch - h) * 0.5)
    newImg = pasteImage(canvasImg, im, x, y)
    return newImg

def rotateImage(im, angle):
    if angle > 0.0:
        im = im.rotate(360.0-angle, expand=False, resample=Image.BICUBIC, fillcolor=(0,0,0,0))
    return im

def rotatePixels(pixels, angle, resize=None):
    im = Image.fromarray(pixels, mode="RGB")
    im = im.convert("RGBA")
    if resize is not None:
        cw, ch = resize
        im = resizeCanvas(im, cw, ch)
    im = rotateImage(im, angle)
    return np.array(im)

def updateAlpha(im, alpha):
    im = im.convert("RGBA")
    im.putalpha(alpha)
    return im
