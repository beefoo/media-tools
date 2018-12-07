# -*- coding: utf-8 -*-

from math_utils import *
from moviepy.editor import VideoFileClip
import multiprocessing
import numpy as np
import os
from PIL import Image
import subprocess
import sys

def addGridPositions(clips, cols, width, height):
    rows = ceilInt(1.0 * len(clips) / cols)
    cellW = 1.0 * width / cols
    cellH = 1.0 * height / rows
    for i, c in enumerate(clips):
        row = i / cols
        col = i % cols
        clips[i]["col"] = col
        clips[i]["row"] = row
        clips[i]["x"] = col * cellW
        clips[i]["y"] = row * cellH
        clips[i]["w"] = cellW
        clips[i]["h"] = cellH
    return clips

def addVideoArgs(parser):
    parser.add_argument('-in', dest="INPUT_FILE", default="../tmp/samples.csv", help="Input file")
    parser.add_argument('-ss', dest="EXCERPT_START", type=float, default=-1, help="Excerpt start in seconds")
    parser.add_argument('-sd', dest="EXCERPT_DUR", type=float, default=-1, help="Excerpt duration in seconds")
    # parser.add_argument('-sort', dest="SORT", default="", help="Query string to sort by")
    # parser.add_argument('-count', dest="COUNT", default=-1, type=int, help="Target total sample count, -1 for everything")
    # parser.add_argument('-filter', dest="FILTER", default="", help="Query string to filter by")
    parser.add_argument('-dir', dest="VIDEO_DIRECTORY", default="../media/sample/", help="Input file")
    parser.add_argument('-aspect', dest="ASPECT_RATIO", default="16:9", help="Aspect ratio of each cell")
    parser.add_argument('-width', dest="WIDTH", default=1920, type=int, help="Output video width")
    parser.add_argument('-height', dest="HEIGHT", default=1080, type=int, help="Output video height")
    parser.add_argument('-fps', dest="FPS", default=30, type=int, help="Output video frames per second")
    parser.add_argument('-frames', dest="SAVE_FRAMES", default=0, type=int, help="Save frames?")
    parser.add_argument('-outframe', dest="OUTPUT_FRAME", default="../tmp/sample/frame.%s.png", help="Output frames pattern")
    parser.add_argument('-out', dest="OUTPUT_FILE", default="../output/sample.mp4", help="Output media file")
    parser.add_argument('-threads', dest="THREADS", default=3, type=int, help="Amount of parallel frames to process (too many may result in too many open files)")
    parser.add_argument('-overwrite', dest="OVERWRITE", default=0, type=int, help="Overwrite existing frames?")
    parser.add_argument('-ao', dest="AUDIO_ONLY", default=0, type=int, help="Render audio only?")
    parser.add_argument('-vo', dest="VIDEO_ONLY", default=0, type=int, help="Render video only?")

def clipsToFrame(p):
    clips = p["clips"]
    filename = p["filename"]
    saveFrame = p["saveFrame"] if "saveFrame" in p else True
    width = p["width"]
    height = p["height"]
    overwrite = p["overwrite"] if "overwrite" in p else False
    verbose = p["verbose"] if "verbose" in p else False
    im = None
    fileExists = os.path.isfile(filename) and not overwrite

    # frame already exists, read it directly
    if not fileExists:
        im = Image.new(mode="RGBA", size=(width, height), color=(0, 0, 0, 255))

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
                clipImg = clipImg.convert("RGBA")
                alpha = clip["alpha"] if "alpha" in clip and clip["alpha"] < 1.0 else 1.0
                clipImg.putalpha(roundInt(alpha*255))
                w, h = clipImg.size
                if w != cw or h != ch:
                    # clipImg = clipImg.resize((cw, ch))
                    clipImg = fillImage(clipImg.copy(), cw, ch)
                # create a staging image at the same size of the base image, so we can blend properly
                stagingImg = Image.new(mode="RGBA", size=(width, height), color=(0, 0, 0, 0))
                stagingImg.paste(clipImg, (roundInt(clip["x"]), roundInt(clip["y"])))
                # stagingImg.save(filename.replace(".png", "%s.png" % videoT))
                # im.paste(stagingImg, (0, 0), mask=stagingImg)
                # im = Image.blend(im, stagingImg, alpha=alpha)
                im = Image.alpha_composite(im, stagingImg)
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
    ratio = 1.0 * w / h
    vw, vh = img.size
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

def frameToMs(frame, fps):
    return roundInt((1.0 * frame / fps) * 1000.0)

def getDurationFromFile(filename):
    result = 0
    if os.path.isfile(filename):
        command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', filename]
        result = subprocess.check_output(command).strip()
    return float(result)

# e.g. returns ['audio', 'video'] for a/v files
def getMediaTypes(filename):
    result = []
    if os.path.isfile(filename):
        command = ['ffprobe', '-loglevel', 'error', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', filename]
        # print(" ".join(command))
        result = subprocess.check_output(command).splitlines()
    return result

def hasAudio(filename):
    return ("audio" in getMediaTypes(filename))

def parseVideoArgs(args):
    d = vars(args)
    aspectW, aspectH = tuple([int(p) for p in args.ASPECT_RATIO.split(":")])
    d["ASPECT_RATIO"] = 1.0 * aspectW / aspectH
    d["SAVE_FRAMES"] = args.SAVE_FRAMES > 0
    d["THREADS"] = min(args.THREADS, multiprocessing.cpu_count()) if args.THREADS > 0 else multiprocessing.cpu_count()
    d["OVERWRITE"] = args.OVERWRITE > 0
    d["AUDIO_ONLY"] = args.AUDIO_ONLY > 0
    d["VIDEO_ONLY"] = args.VIDEO_ONLY > 0
    d["AUDIO_OUTPUT_FILE"] = args.OUTPUT_FILE.replace(".mp4", ".mp3")
    d["MS_PER_FRAME"] = 1.0 / (args.FPS / 1000.0)

def processFrames(params, threads=1, verbose=True):
    count = len(params)
    if threads > 1:
        pool = ThreadPool(threads)
        results = pool.map(clipsToFrame, params)
        pool.close()
        pool.join()
    else:
        for i, p in enumerate(params):
            clipsToFrame(p)
            if verbose:
                sys.stdout.write('\r')
                sys.stdout.write("%s%%" % round(1.0*i/(count-1)*100,1))
                sys.stdout.flush()
