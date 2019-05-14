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

def addVideoArgs(parser):
    parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
    parser.add_argument('-ss', dest="EXCERPT_START", type=float, default=-1, help="Excerpt start in seconds")
    parser.add_argument('-sd', dest="EXCERPT_DUR", type=float, default=-1, help="Excerpt duration in seconds")
    parser.add_argument('-db', dest="MASTER_DB", type=float, default=0.0, help="Master +/- decibels to be applied to final audio")
    parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/sample/", help="Input file")
    parser.add_argument('-width', dest="WIDTH", default=1920, type=int, help="Output video width")
    parser.add_argument('-height', dest="HEIGHT", default=1080, type=int, help="Output video height")
    parser.add_argument('-fps', dest="FPS", default=30, type=int, help="Output video frames per second")
    parser.add_argument('-outframe', dest="OUTPUT_FRAME", default="tmp/sample/frame.%s.png", help="Output frames pattern")
    parser.add_argument('-out', dest="OUTPUT_FILE", default="output/sample.mp4", help="Output media file")
    parser.add_argument('-threads', dest="THREADS", default=1, type=int, help="Amount of parallel frames to process (too many may result in too many open files)")
    parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing frames?")
    parser.add_argument('-ao', dest="AUDIO_ONLY", action="store_true", help="Render audio only?")
    parser.add_argument('-vo', dest="VIDEO_ONLY", action="store_true", help="Render video only?")
    parser.add_argument('-cache', dest="CACHE_VIDEO", action="store_true", help="Cache video clips?")
    parser.add_argument('-cd', dest="CACHE_DIR", default="tmp/cache/", help="Dir for caching data")
    parser.add_argument('-ckey', dest="CACHE_KEY", default="sample", help="Key for caching data")
    parser.add_argument('-verifyc', dest="VERIFY_CACHE", action="store_true", help="Add a step for verifying existing cache data?")
    parser.add_argument('-rand', dest="RANDOM_SEED", default=1, type=int, help="Random seed to use for pseudo-randomness")
    parser.add_argument('-pad0', dest="PAD_START", default=1000, type=int, help="Pad the beginning")
    parser.add_argument('-pad1', dest="PAD_END", default=3000, type=int, help="Pad the end")
    parser.add_argument('-rvb', dest="REVERB", default=80, type=int, help="Reverberence (0-100)")
    parser.add_argument('-debug', dest="DEBUG", action="store_true", help="Debug mode?")
    parser.add_argument('-mdb', dest="MATCH_DB", default=-16, type=int, help="Match decibels, -9999 for none")
    parser.add_argument('-maxdb', dest="MAX_DB", default=-16, type=int, help="Max decibels, -9999 for none")
    parser.add_argument('-precision', dest="PRECISION", default=3, type=int, help="Precision for position and size")
    parser.add_argument('-margin', dest="CLIP_MARGIN", default=0.06666666667, type=float, help="Margin between clips as a percentage of a clip's width")
    parser.add_argument('-alphar', dest="ALPHA_RANGE", default="0.33,1.0", help="Alpha range")
    parser.add_argument('-brightr', dest="BRIGHTNESS_RANGE", default="0.33,1.0", help="Brightness range")
    parser.add_argument('-mcd', dest="MIN_CLIP_DUR", default=1200, type=int, help="Minumum clip duration")
    parser.add_argument('-noise', dest="NOISE", default=0.0, type=float, help="Amount of pixel noise to add")
    parser.add_argument('-maxa', dest="MAX_AUDIO_CLIPS", default=-1, type=int, help="Maximum number of audio clips to play")
    parser.add_argument('-keep', dest="KEEP_FIRST_AUDIO_CLIPS", default=-1, type=int, help="Ensure the middle x audio files play")
    parser.add_argument('-inva', dest="INVERT_LOUDEST", action="store_true", help="Clips on the outer edge are louder?")
    parser.add_argument('-fa', dest="FRAME_ALPHA", default=1.0, type=float, help="For adding frame content on top of previous frames; must be 0 <= x < 1; lower number = slower fade of prev frames")
    parser.add_argument('-rmode', dest="RESIZE_MODE", default="fill", help="Mode for resizing frames: fill, contain, or warp")
    parser.add_argument('-io', dest="CLIP_INITIAL_OFFSET", default=0, type=int, help="Milliseconds to offset the initial clip state for continuity between compositions")
    parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just spit out duration info?")

def alphaMask(im, mask):
    w, h = im.size
    transparentImg = Image.new(mode="RGBA", size=(w, h), color=(0, 0, 0, 0))
    mw, mh = mask.size
    if mw != w or mh != h:
        mask = mask.resize((w, h), PIL.Image.BICUBIC)
    return Image.composite(im, transparentImg, mask)

def applyEffects(im, x, y, rotation=0.0, blur=0.0, mask=None, colors=4):
    im = im.convert("RGBA")
    w, h = im.size
    angle = normalizeAngle(rotation)
    if mask is not None:
        im = alphaMask(im, mask)
    if angle > 0.0 or blur > 0.0:
        bx, by, bw, bh = bboxRotate(x, y, w, h, 45.0) # make the new box size as big as if it was rotated 45 degrees
        im = resizeCanvas(im, roundInt(bw), roundInt(bh)) # resize canvas to account for expansion from rotation or blur
        im = rotateImage(im, angle)
        im = blurImage(im, blur)
        x = bx
        y = by
    if colors == 3:
        im = im.convert("RGB")
    return (im, x, y)

def blurImage(im, radius):
    if radius > 0.0:
        im = im.filter(ImageFilter.GaussianBlur(radius=radius))
    return im

def clipsToFrame(p, clips, pixelData, precision=3, customClipToArrFunction=None, baseImage=None, gpuProgram=None, postProcessingFunction=None, globalArgs={}):
    filename = p["filename"]
    width = p["width"]
    height = p["height"]

    ms = getValue(p, "ms", 0)
    overwrite = getValue(p, "overwrite", False)
    verbose = getValue(p, "verbose", False)
    debug = getValue(p, "debug", False)
    saveFrame = getValue(p, "saveFrame", filename)

    frameAlpha = getValue(globalArgs, "frameAlpha", None)
    isSequential = getValue(globalArgs, "isSequential", False)
    container = getValue(globalArgs, "container", None)

    im = None
    fileExists = filename and os.path.isfile(filename) and not overwrite
    clipArr = None
    returnValue = None

    if not fileExists and saveFrame or not saveFrame or isSequential:
        clipArr = clipsToNpArr(clips, ms, width, height, precision, customClipToArrFunction=customClipToArrFunction, globalArgs=globalArgs)
        # Clip debug:
    #     pprint(clips[8124].props)
    #     clipArr = clipsToNpArr(clips, ms, width, height, precision, customClipToArrFunction=customClipToArrFunction, globalArgs=globalArgs)
    #     print("---")
    #     pprint(clipArr[8124])
    # sys.exit()
        # Time debug:
        # debugFilename = "tmp/debug.%s.%s.txt" % (os.path.basename(filename), ms)
        # debugArr = clipArr[:,5].astype(int)
        # np.savetxt(debugFilename, debugArr, fmt='%i')
    # sys.exit()

    # frame does not exist, create frame image
    if not fileExists:
        im = Image.new(mode="RGBA", size=(width, height), color=(0, 0, 0, 255))
        im = clipsToFrameGPU(clipArr, width, height, pixelData, precision, baseImage=baseImage, gpuProgram=gpuProgram, globalArgs=globalArgs)
        im = im.convert("RGB")
        # check to see if we're applying container-level effects
        if container is not None:
            # right now we only care about blur
            blur = container.vector.getBlur(ms)
            if blur > 0.0:
                im = blurImage(im, blur)
        # check to see if there's post-processing to be done
        if postProcessingFunction is not None:
            im = postProcessingFunction(im, ms)
        # save if necessary
        if saveFrame:
            im.save(filename)
            print("Saved frame %s" % filename)
        if frameAlpha is None:
            returnValue = im

    # frame has alpha, so darken for next frame
    if frameAlpha is not None and 0.0 <= frameAlpha < 1.0:
        if im is None:
            im = Image.open(filename)
        blackOverlay = Image.new(mode="RGB", size=im.size, color=(0, 0, 0))
        im = Image.blend(im, blackOverlay, frameAlpha)
        returnValue = im

    return returnValue

def clipsToFrameGPU(clips, width, height, clipsPixelData, precision=3, baseImage=None, gpuProgram=None, globalArgs={}):
    c = getValue(globalArgs, "colors", 3)
    offset = 0
    maxScaleFactor = 2.0
    precisionMultiplier = int(10 ** precision)

    # filter out clips with no pixels, or zero [width, height, alpha]
    # keep track of how many pixels we'll need
    indices = []
    pixelCount = 0
    for i in range(len(clips)):
        clip = clipArrToDict(clips[i], precision)
        frameCount = len(clipsPixelData[i])
        # only take clips that are visible
        if frameCount > 0 and clip["width"] > 0.0 and clip["height"] > 0.0 and clip["alpha"] > 0.0:
            indices.append(i)
            tn = clip["tn"]
            h, w, _ = clipsPixelData[i][roundInt(tn * (frameCount-1))].shape
            # we want to resample if scaled too much
            scaleFactor = 1.0 * w / clip["width"]
            if scaleFactor > maxScaleFactor:
                w = roundInt(clip["width"])
                h = roundInt(clip["height"])
            # we need to resize if blurred or rotated
            if clip["blur"] > 0.0 or clip["rotation"] % 360.0 > 0.0:
                _x, _y, newW, newH = bboxRotate(0, 0, roundInt(clip["width"]), roundInt(clip["height"]), angle=45.0)
                w = roundInt(newW)
                h = roundInt(newH)
            pixelCount += int(h*w*c)

    validCount = len(indices)
    propertyCount = Clip.gpuPropertyCount
    properties = np.zeros((validCount, propertyCount), dtype=np.int32)
    pixelData = np.zeros(pixelCount, dtype=np.uint8)
    for i, clipIndex in enumerate(indices):
        clipArr = clips[clipIndex]
        x, y, tw, th, alpha, t, zindex, rotation, blur, brightness = tuple(clipArr)
        clip = clipArrToDict(clipArr, precision)
        clipPixelData = clipsPixelData[clipIndex]
        frameCount = len(clipPixelData)
        tn = clip["tn"]
        pixels = clipPixelData[roundInt(tn * (frameCount-1))]
        h, w, _c = pixels.shape
        # we want to resample if scaled too much
        scaleFactor = 1.0 * w / clip["width"]
        if scaleFactor > maxScaleFactor or clip["blur"] > 0.0 or clip["rotation"] % 360.0 > 0.0:
            rw = roundInt(clip["width"])
            rh = roundInt(clip["height"])
            im = None
            # assume we are debugging if single pixel
            if h==1 and w==1:
                newPixels = np.zeros((rh, rw, _c), dtype=np.uint8)
                newPixels[:,:] = pixels[0,0]
                im = Image.fromarray(newPixels, mode="RGB")
            else:
                im = Image.fromarray(pixels, mode="RGB")

            # apply effects before resize for better quality
            if clip["blur"] > 0.0 or clip["rotation"] % 360.0 > 0.0:
                im, _x, _y = applyEffects(im, 0, 0, clip["rotation"], clip["blur"], colors=c)
                # retrieve new coordinates based on target/resized size
                newX, newY, newW, newH = bboxRotate(clip["x"], clip["y"], roundInt(clip["width"]), roundInt(clip["height"]), angle=45.0)
                rw = roundInt(newW)
                rh = roundInt(newH)
                # x, y, tw, th changes if we rotate or blur
                x = roundInt(newX * precisionMultiplier)
                y = roundInt(newY * precisionMultiplier)
                tw = roundInt(newW * precisionMultiplier)
                th = roundInt(newH * precisionMultiplier)

            # resize image
            imW, imH = im.size
            if imW != rw or imH != rh:
                resampleType = Image.LANCZOS if imW > rw else Image.NEAREST
                im = im.resize((rw, rh), resample=resampleType)

            # im.save("output/test_pil.png")
            pixels = np.array(im)
            h, w, _c = pixels.shape
        # pixels are size 3, but need size 4
        if c > _c:
            fillVals = np.full((h, w, 1), 255, dtype='uint8')
            pixels = np.concatenate((pixels, fillVals), axis=2)
        properties[i] = np.array([offset, x, y, w, h, tw, th, alpha, zindex, brightness])
        px0 = offset
        px1 = px0 + int(h*w*c)
        pixelData[px0:px1] = pixels.reshape(-1)
        offset += int(h*w*c)

    pixels = clipsToImageGPU(width, height, pixelData, properties, c, precision, gpuProgram=gpuProgram, baseImage=baseImage)
    return Image.fromarray(pixels, mode="RGB")

def compileFrames(infile, fps, outfile, padZeros, audioFile=None, quality="high"):
    print("Compiling frames...")
    padStr = '%0'+str(padZeros)+'d'

    # https://trac.ffmpeg.org/wiki/Encode/H.264
    # presets: veryfast, faster, fast, medium, slow, slower, veryslow
    #   slower = better quality
    # crf: 0 is lossless, 23 is the default, and 51 is worst possible quality
    #   17 or 18 to be visually lossless or nearly so
    preset = "veryslow"
    crf = "18"
    if quality=="medium":
        preset = "medium"
        crf = "23"
    elif quality=="low":
        preset = "medium"
        crf = "28"

    if audioFile:
        command = ['ffmpeg','-y',
                    '-framerate',str(fps)+'/1',
                    '-i',infile % padStr,
                    '-i',audioFile,
                    '-c:v','libx264',
                    '-preset', preset,
                    '-crf', crf,
                    '-r',str(fps),
                    '-pix_fmt','yuv420p',
                    '-c:a','aac',
                    # '-q:v','1',
                    '-b:a', '192k',
                    # '-shortest',
                    outfile]
    else:
        command = ['ffmpeg','-y',
                    '-framerate',str(fps)+'/1',
                    '-i',infile % padStr,
                    '-c:v','libx264',
                    '-preset', preset,
                    '-crf', crf,
                    '-r',str(fps),
                    '-pix_fmt','yuv420p',
                    # '-q:v','1',
                    outfile]
    print(" ".join(command))
    finished = subprocess.check_call(command)
    print("Done.")

def containImage(img, w, h, resampleType="default", bgcolor=[0,0,0]):
    resampleType = Image.LANCZOS if resampleType=="default" else resampleType
    vw, vh = img.size

    if vw == w and vh == h:
        return img

    # create a base image
    w = roundInt(w)
    h = roundInt(h)
    if img.mode=="RGBA" and len(bgcolor)==3:
        bgcolor.append(0)
    baseImg = Image.new(mode=img.mode, size=(w, h), color=tuple(bgcolor))

    ratio = 1.0 * w / h
    vratio = 1.0 * vw / vh

    # first, resize video
    newW = w
    newH = h
    pasteX = 0
    pasteY = 0
    if vratio > ratio:
        newH = w / vratio
        pasteY = roundInt((h-newH) * 0.5)
    else:
        newW = h * vratio
        pasteX = roundInt((w-newW) * 0.5)

    # Lanczos = good for downsizing
    resized = img.resize((roundInt(newW), roundInt(newH)), resample=resampleType)
    baseImg.paste(resized, (pasteX, pasteY))
    return baseImg

def fillImage(img, w, h, resampleType="default"):
    vw, vh = img.size
    resampleType = Image.LANCZOS if resampleType=="default" else resampleType

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
    # Lanczos = good for downsizing
    resized = img.resize((roundInt(newW), roundInt(newH)), resample=resampleType)

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
            except UnicodeDecodeError:
                print("Unicode decode error for %s" % filename)
                result = 0
            except IOError:
                print("I/O error for %s" % filename)
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
        result = [line.decode("utf-8") for line in subprocess.check_output(command).splitlines()]
    return result

def getSolidPixels(color, width=100, height=100):
    dim = len(color)
    pixels = np.zeros((height, width, dim))
    pixels[:,:] = color
    return pixels

def getVideoClipImage(video, videoDur, clip, t=None, resizeMode="fill", resampleType="default"):
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
    clipImg = resizeImage(clipImg, cw, ch, resizeMode, resampleType)
    return clipImg

def getRotation(clip):
    rotation = clip["rotation"] if "rotation" in clip else 0.0
    angle = normalizeAngle(rotation)
    return angle

def hasAudio(filename):
    return ("audio" in getMediaTypes(filename))

def loadVideoPixelData(clips, fps, cacheDir="tmp/", width=None, height=None, verifyData=True, cache=True, resizeMode="fill"):
    # load videos
    filenames = list(set([clip.props["filename"] for clip in clips]))
    fileCount = len(filenames)
    msStep = frameToMs(1, fps, False)
    clipsPixelData = [None] * len(clips)

    for i, clip in enumerate(clips):
        if "maxWidth" in clip.props and "maxHeight" in clip.props:
            break
        if i <= 0:
            print("Warning: max width/height not set, setting it to given width/height")
        if "maxWidth" not in clip.props:
            clip.setProp("maxWidth", clip.props["width"])
        if "maxHeight" not in clip.props:
            clip.setProp("maxHeight", clip.props["height"])

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
                    if roundInt(clip.props["maxWidth"]) > clipW:
                        print("Clip width is too small (%s > %s) for %s at %s. Resetting cache data" % (clip.props["maxWidth"], clipW, cacheFn, t))
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
                    fclip["width"] = fclip["maxWidth"]
                    fclip["height"] = fclip["maxHeight"]
                    t = roundInt(ms)
                    ms += msStep
                    # already exists, check size
                    existIndex = None
                    if t in set(clipTimes):
                        existIndex = clipTimes.index(t)
                        clipH, clipW, _ = clipPixels[existIndex].shape
                        if roundInt(fclip["width"]) <= clipW:
                            continue
                    clipResizeMode = getValue(clip.props, "resizeMode", resizeMode)
                    clipImg = getVideoClipImage(video, videoDur, fclip, t, clipResizeMode)
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

def loadVideoPixelDataDebug(clipCount):
    clipsPixelData = np.zeros((clipCount, 1, 1, 1, 3))
    for i in range(clipCount):
        clipsPixelData[i, 0, 0, 0] = getRandomColor(i)
    return clipsPixelData

def loadVideoPixelDataFromFrames(frames, clips, containerW, containerH, fps, cacheDir="tmp/", cacheKey="sample", verifyData=True, cache=True, debug=False, precision=3, customClipToArrFunction=None, customClipToArrCalcFunction=None, globalArgs={}):
    frameCount = len(frames)
    clipCount = len(clips)
    precisionMultiplier = int(10 ** precision)
    cacheFile = cacheKey + "_maxes.p"
    resizeMode = getValue(globalArgs, "resizeMode", "fill")

    if debug:
        clipsPixelData = loadVideoPixelDataDebug(clipCount)
        return clipsPixelData

    loaded = False
    clipWidthMaxes = None
    if cache:
        loaded, clipWidthMaxes = loadCacheFile(cacheDir+cacheFile)

    if not loaded or len(clipWidthMaxes) != clipCount:
        print("Calculating clip size/position from frame sequence...")
        clipWidthMaxes = np.zeros(clipCount, dtype=np.int32)
        clipCompare = np.zeros((2, clipCount), dtype=np.int32)
        ccfunction = customClipToArrFunction
        # override custom clip arr function for calcuation
        if customClipToArrCalcFunction is "default":
            ccfunction = None
        elif customClipToArrCalcFunction is not None:
            ccfunction = customClipToArrCalcFunction
        for i, frame in enumerate(frames):
            ms = frame["ms"]
            # frameClips = clipsToDictsGPU(clips, ms, container, precision)
            frameClips = clipsToNpArr(clips, ms, containerW, containerH, precision, customClipToArrFunction=ccfunction, globalArgs=globalArgs)
            clipCompare[0] = clipWidthMaxes
            clipCompare[1] = frameClips[:,2] # just take the width (2)
            clipWidthMaxes = np.amax(clipCompare, axis=0)
            printProgress(i+1, frameCount)
        if cache:
            saveCacheFile(cacheDir+cacheFile, clipWidthMaxes, overwrite=True)

    # visualize the result
    # from matplotlib import pyplot as plt
    # totalMax = np.amax(clipWidthMaxes)
    # colors = clipWidthMaxes.astype(np.float32) / totalMax * 255.0
    # colors = colors.astype(np.uint8)
    # im = Image.fromarray(colors, mode="L")
    # plt.imshow(np.asarray(im))
    # plt.show()
    # sys.exit()

    # update clips with max width/height
    for i, clip in enumerate(clips):
        width = 1.0 * clipWidthMaxes[clip.props["index"]] / precisionMultiplier
        height = width / clip.vector.aspectRatio
        clip.setProp("maxWidth", width)
        clip.setProp("maxHeight", height)
        # print("%s, %s" % (clip.props["width"], clip.props["height"]))

    clipsPixelData = loadVideoPixelData(clips, fps, cacheDir=cacheDir, verifyData=verifyData, cache=cache, resizeMode=resizeMode)

    return clipsPixelData

def msToFrame(ms, fps):
    return roundInt((ms / 1000.0) * fps)

def parseVideoArgs(args):
    d = vars(args)
    d["THREADS"] = min(args.THREADS, multiprocessing.cpu_count()) if args.THREADS > 0 else multiprocessing.cpu_count()
    d["AUDIO_OUTPUT_FILE"] = args.OUTPUT_FILE.replace(".mp4", ".mp3")
    d["MS_PER_FRAME"] = frameToMs(1, args.FPS, False)
    d["CACHE_VIDEO"] = args.CACHE_VIDEO
    d["VOLUME_RANGE"] = tuple([float(v) for v in args.VOLUME_RANGE.strip().split(",")]) if "VOLUME_RANGE" in d else (0.0, 1.0)
    d["ALPHA_RANGE"] =  tuple([float(v) for v in args.ALPHA_RANGE.strip().split(",")])
    d["BRIGHTNESS_RANGE"] =  tuple([float(v) for v in args.BRIGHTNESS_RANGE.strip().split(",")])

def pasteImage(im, clipImg, x, y):
    width, height = im.size
    # create a staging image at the same size of the base image, so we can blend properly
    stagingImg = Image.new(mode="RGBA", size=(width, height), color=(0, 0, 0, 0))
    stagingImg.paste(clipImg, (roundInt(x), roundInt(y)))
    im = Image.alpha_composite(im, stagingImg)
    return im

def processFrames(params, clips, clipsPixelData, threads=1, precision=3, verbose=True, customClipToArrFunction=None, postProcessingFunction=None, globalArgs={}):
    if len(params) < 1:
        return

    count = len(params)
    print("Processing %s frames" % count)
    threads = getThreadCount(threads)

    frameAlpha = getValue(globalArgs, "frameAlpha", 1.0)
    isSequential = getValue(globalArgs, "isSequential", False)
    baseImage = getValue(globalArgs, "baseImage", None)
    propagateFrames = (0.0 <= frameAlpha < 1.0)
    if propagateFrames:
        isSequential = True

    # load gpu program
    p0 = params[0]
    colorDimensions = getValue(globalArgs, "colors", 3)
    pcount = Clip.gpuPropertyCount
    gpuProgram = loadMakeImageProgram(p0["width"], p0["height"], pcount, colorDimensions, precision)

    if threads > 1 and not isSequential:
        pool = ThreadPool(threads)
        pclipsToFrame = partial(clipsToFrame, clips=clips, pixelData=clipsPixelData, precision=precision, customClipToArrFunction=customClipToArrFunction, baseImage=baseImage, gpuProgram=gpuProgram, postProcessingFunction=postProcessingFunction, globalArgs=globalArgs)
        pool.map(pclipsToFrame, params)
        pool.close()
        pool.join()
    else:
        prevImage = None
        for i, p in enumerate(params):
            baseImage = prevImage if propagateFrames else baseImage
            prevImage = clipsToFrame(p, clips=clips, pixelData=clipsPixelData, precision=precision, customClipToArrFunction=customClipToArrFunction, baseImage=baseImage, gpuProgram=gpuProgram, postProcessingFunction=postProcessingFunction, globalArgs=globalArgs)
            if verbose:
                printProgress(i+1, count)

def resizeImage(im, w, h, mode="fill", resampleType="default"):
    resampleType = Image.LANCZOS if resampleType=="default" else resampleType
    if mode=="warp":
        return im.resize((roundInt(w), roundInt(h)), resample=resampleType)
    elif mode=="contain":
        return containImage(im, w, h, resampleType=resampleType)
    else:
        return fillImage(im, w, h, resampleType=resampleType)

def resizeCanvas(im, cw, ch):
    canvasImg = Image.new(mode="RGBA", size=(cw, ch), color=(0, 0, 0, 0))
    w, h = im.size
    x = roundInt((cw - w) * 0.5)
    y = roundInt((ch - h) * 0.5)
    newImg = pasteImage(canvasImg, im, x, y)
    return newImg

def rotateImage(im, angle):
    if abs(angle) > 0.0:
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

def saveBlankFrame(fn, width, height, bgColor="#000000"):
    im = Image.new('RGB', (width, height), bgColor)
    im.save(fn)
    print("Saved %s" % fn)

def updateAlpha(im, alpha):
    im = im.convert("RGBA")
    im.putalpha(alpha)
    return im
