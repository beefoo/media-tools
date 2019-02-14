# -*- coding: utf-8 -*-

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
import subprocess
import sys

def addGridPositions(clips, cols, width, height, offsetX=0, offsetY=0, marginX=0, marginY=0):
    rows = ceilInt(1.0 * len(clips) / cols)
    cellW = 1.0 * (width - marginX * (cols+1)) / cols
    cellH = 1.0 * (height - marginY * (rows+1)) / rows
    for i, c in enumerate(clips):
        row = i / cols
        col = i % cols
        clips[i]["col"] = col
        clips[i]["row"] = row
        clips[i]["x"] = col * cellW + col * marginX + offsetX
        clips[i]["y"] = row * cellH + row * marginY + offsetY
        clips[i]["width"] = cellW
        clips[i]["height"] = cellH
    return clips

def addVideoArgs(parser):
    parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
    parser.add_argument('-ss', dest="EXCERPT_START", type=float, default=-1, help="Excerpt start in seconds")
    parser.add_argument('-sd', dest="EXCERPT_DUR", type=float, default=-1, help="Excerpt duration in seconds")
    parser.add_argument('-vol', dest="VOLUME", type=float, default=1.0, help="Master volume applied to all clips")
    # parser.add_argument('-sort', dest="SORT", default="", help="Query string to sort by")
    parser.add_argument('-count', dest="COUNT", default=-1, type=int, help="Target total sample count, -1 for everything")
    # parser.add_argument('-filter', dest="FILTER", default="", help="Query string to filter by")
    parser.add_argument('-dir', dest="VIDEO_DIRECTORY", default="media/sample/", help="Input file")
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
    parser.add_argument('-cf', dest="CACHE_FILE", default="tmp/pixel_cache.npy", help="File for caching data")
    parser.add_argument('-gpu', dest="USE_GPU", action="store_true", help="Use GPU? (requires caching to be true)")
    parser.add_argument('-rand', dest="RANDOM_SEED", default=1, type=int, help="Random seed to use for pseudo-randomness")
    parser.add_argument('-pad0', dest="PAD_START", default=0, type=int, help="Pad the beginning")
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

def clipsToFrame(p):
    filename = p["filename"]
    saveFrame = p["saveFrame"] if "saveFrame" in p else True
    width = p["width"]
    height = p["height"]
    overwrite = p["overwrite"] if "overwrite" in p else False
    verbose = p["verbose"] if "verbose" in p else False
    useGPU = p["gpu"] if "gpu" in p else False
    debug = p["debug"] if "debug" in p else False
    im = None
    fileExists = os.path.isfile(filename) and not overwrite

    # frame already exists, read it directly
    if not fileExists:
        im = Image.new(mode="RGBA", size=(width, height), color=(0, 0, 0, 255))

        clips = p["clips"]
        if "ms" in p:
            clips = clipsToDicts(p["clips"], p["ms"])

        # filter out clips that are not visible
        clips = [clip for clip in clips if isClipVisible(clip, width, height)]

        # check for debug mode
        if debug:
            im = clipsToFrameDebug(im, clips, width, height)

        # pixels are cached
        elif len(clips) > 0 and "framePixelData" in clips[0]:
            if useGPU:
                im = clipsToFrameGPU(clips, width, height)
            else:
                for clip in clips:
                    framePixelData = clip["framePixelData"]
                    count = len(framePixelData)
                    if count > 0:
                        pixels = framePixelData[roundInt(clip["tn"] * (count-1))]
                        clipImg = Image.fromarray(pixels, mode="RGB")
                        clipImg = fillImage(clipImg, roundInt(clip["width"]), roundInt(clip["height"]))
                        clipImg, x, y = applyEffects(clipImg, clip)
                        im = pasteImage(im, clipImg, x, y)

        # otherwise, load pixels from the video source
        else:
            # load videos
            filenames = list(set([clip["filename"] for clip in clips]))
            fileCount = len(filenames)

            # only open one video at a time
            for i, fn in enumerate(filenames):
                video = VideoFileClip(fn, audio=False)
                videoDur = video.duration
                vclips = [c for c in clips if fn==c["filename"]]

                # extract frames from videos
                for clip in vclips:
                    clipImg = getVideoClipImage(video, videoDur, clip)
                    clipImg, x, y = applyEffects(clipImg, clip)
                    im = pasteImage(im, clipImg, x, y)
                video.reader.close()
                del video

                if verbose:
                    sys.stdout.write('\r')
                    sys.stdout.write("%s%%" % round(1.0*(i+1)/fileCount*100,1))
                    sys.stdout.flush()

        im = im.convert("RGB")

        if saveFrame:
            im.save(filename)
            print("Saved frame %s" % filename)

    return True

def clipsToFrameDebug(im, clips, width, height):
    for i, clip in enumerate(clips):
        if "framePixelData" in clip:
            break
        rindex = getValue(clip, "index", i)
        pixels = np.array([[getRandomColor(rindex)]])
        clips[i]["framePixelData"] = [pixels]
        # sys.stdout.write('\r')
        # sys.stdout.write("%s%%" % round(1.0*(i+1)/len(clips)*100,1))
        # sys.stdout.flush()
    return clipsToFrameGPU(clips, width, height)

def clipsToFrameGPU(clips, width, height):
    pixelData = []
    properties = []
    offset = 0
    precision = 3

    for clip in clips:
        framePixelData = clip["framePixelData"]
        count = len(framePixelData)
        if count > 0:
            pixels = framePixelData[roundInt(clip["tn"] * (count-1))]
            h, w, c = pixels.shape
            tw = clip["width"]
            th = clip["height"]
            x = clip["x"]
            y = clip["y"]
            # not ideal, but don't feel like implementing blur/rotation in opencl; just use PIL's algorithm
            if "rotation" in clip and clip["rotation"] % 360 > 0 or "blur" in clip and clip["blur"] > 0.0:
                im = Image.fromarray(pixels, mode="RGB")
                im, x, y = applyEffects(im, clip)
                pixels = np.array(im)
                w0 = w
                h0 = h
                h, w, c = pixels.shape
                tw = roundInt(1.0 * w / w0 * tw)
                th = roundInt(1.0 * h / h0 * th)
            pixelData.append(pixels)
            # print("%s, %s, %s" % pixels.shape)
            alpha = getAlpha(clip)
            # rotation = roundInt(getRotation(clip) * 1000)
            # blur = roundInt(getValue(clip, "blur", 0) * 1000)
            properties.append([offset, x, y, w, h, tw, th, alpha])
            offset += (h*w*c)
    pixels = clipsToImageGPU(width, height, pixelData, properties, c)
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

def getVideoClipImage(video, videoDur, clip):
    videoT = clip["t"] / 1000.0
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

def loadVideoPixelDataFromFile(filename, clipLength):
    pixelData = [[] for i in range(clipLength)]
    loaded = False
    if filename and os.path.isfile(filename):
        pixelData = np.load(filename)
        if len(pixelData) != clipLength:
            print("Mismatch of cached data; resetting...")
            pixelData = [[] for i in range(clipLength)]
        else:
            loaded = True

    return (loaded, pixelData)

def loadVideoPixelData(clips, fps, filename=None, width=None, height=None, checkVisibility=True):
    # assumes clip has width, height, and index
    print("Loading video pixel data...")
    dataLoaded, pixelData = loadVideoPixelDataFromFile(filename, len(clips))

    if not dataLoaded:
        print("No cached data found... rebuilding...")
        # load videos
        filenames = list(set([clip["filename"] for clip in clips]))
        fileCount = len(filenames)
        msStep = frameToMs(1, fps, False)

        # only open one video at a time
        for i, fn in enumerate(filenames):
            video = VideoFileClip(fn, audio=False)
            videoDur = video.duration
            vclips = [c for c in clips if fn==c["filename"]]

            # extract frames from videos
            for clip in vclips:
                if checkVisibility and width and height and isClipVisible(clip, width, height):
                    start = clip["start"]
                    end = start + clip["dur"]
                    ms = start
                    clipData = []
                    while ms <= end:
                        fclip = clip.copy()
                        fclip["t"] = roundInt(ms)
                        clipImg = getVideoClipImage(video, videoDur, fclip)
                        clipData.append(np.array(clipImg))
                        ms += msStep
                    pixelData[clip["index"]] = np.array(clipData)
                else:
                    pixelData[clip["index"]] = np.array([])

            video.reader.close()
            del video
            printProgress(i+1, fileCount)

        if filename:
            print("Saving cached data...")
            np.save(filename, pixelData)

    for i, clip in enumerate(clips):
        clips[i]["framePixelData"] = pixelData[clip["index"]]

    print("Finished loading pixel data.")

    return clips

def loadVideoPixelDataFromFrames(frames, clips, fps, filename=None):
    print("Reading frames for caching...")
    dataLoaded, pixelData = loadVideoPixelDataFromFile(filename, len(clips))

    if not dataLoaded:
        frameCount = len(frames)
        clipCount = len(clips)
        clipData = np.zeros((frameCount, clipCount, 2)) # will store each clip's width/height for each frame
        for i, frame in enumerate(frames):
            frameClips = clipsToDicts(clips, frame["ms"])
            # filter out clips that are not visible
            frameClips = [clip for clip in frameClips if isClipVisible(clip, frame["width"], frame["height"])]
            for clip in frameClips:
                clipData[i, clip["index"], 0] = clip["width"]
                clipData[i, clip["index"], 1] = clip["height"]
            printProgress(i+1, frameCount)
        # get max dimension of each clip
        clipMaxes = np.amax(clipData, axis=0)
        # update clip dicts with max width/height
        print("Assigning widths and heights")
        clipDicts = clipsToDicts(clips)
        for i, clip in enumerate(clipDicts):
            clipDicts["width"] = clipMaxes[i, 0]
            clipDicts["height"] = clipMaxes[i, 1]
        clipDicts = loadVideoPixelData(clipDicts, fps, filename=filename, checkVisibility=False)
        print("Assigning clip pixel data")
        for i, clip in enumerate(clipDicts):
            clips[i].setProp("framePixelData", clip["framePixelData"])

    else:
        for clip in clips:
            clip.setProp("framePixelData", pixelData[clip.props["index"])

def msToFrame(ms, fps):
    return roundInt((ms / 1000.0) * fps)

def parseVideoArgs(args):
    d = vars(args)
    aspectW, aspectH = tuple([int(p) for p in args.ASPECT_RATIO.split(":")])
    d["ASPECT_RATIO"] = 1.0 * aspectW / aspectH
    d["THREADS"] = min(args.THREADS, multiprocessing.cpu_count()) if args.THREADS > 0 else multiprocessing.cpu_count()
    d["AUDIO_OUTPUT_FILE"] = args.OUTPUT_FILE.replace(".mp4", ".mp3")
    d["MS_PER_FRAME"] = frameToMs(1, args.FPS, False)
    d["CACHE_VIDEO"] = args.CACHE_VIDEO or args.USE_GPU
    d["MATCH_DB"] = args.MATCH_DB if args.MATCH_DB > -9999 else False

def pasteImage(im, clipImg, x, y):
    width, height = im.size
    # create a staging image at the same size of the base image, so we can blend properly
    stagingImg = Image.new(mode="RGBA", size=(width, height), color=(0, 0, 0, 0))
    stagingImg.paste(clipImg, (roundInt(x), roundInt(y)))
    im = Image.alpha_composite(im, stagingImg)
    return im

def processFrames(params, threads=1, verbose=True):
    count = len(params)
    print("Processing %s frames" % count)
    if threads > 1:
        pool = ThreadPool(threads)
        results = pool.map(clipsToFrame, params)
        pool.close()
        pool.join()
    else:
        for i, p in enumerate(params):
            clipsToFrame(p)
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
