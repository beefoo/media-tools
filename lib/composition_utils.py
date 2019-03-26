
from lib.audio_mixer import *
from lib.clip import *
from lib.io_utils import *
from lib.math_utils import *
from lib.sampler import *
from lib.video_utils import *
import math

def addGridPositions(clips, cols, width, height, offsetX=0, offsetY=0, marginX=0, marginY=0):
    rows = ceilInt(1.0 * len(clips) / cols)
    cellW = 1.0 * width / cols
    cellH = 1.0 * height / rows
    marginX *= cellW
    marginY *= cellW
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

def addPositionNoise(clips, noiseXRange, noiseYRange, randomSeed=3):
    for i, c in enumerate(clips):
        clips[i]["x"] = c["x"] + pseudoRandom(randomSeed+i*2, range=noiseXRange)
        clips[i]["y"] = c["y"] + pseudoRandom(randomSeed+i*2+1, range=noiseYRange)
    return clips

def getDivisionIncrement(count):
    if count < 2:
        return 1.0
    divisions = math.ceil(math.log(count, 2))
    increment = 1.0 / divisions / 2.0
    return increment

def getOffset(count, index):
    if count < 2 or index < 1:
        return 0

    divisions = math.ceil(math.log(count, 2))
    currentIndex = 0
    foundOffset = 0
    for i in range(divisions):
        add = 2 ** i
        offset = 2 ** (-(i+1))
        for j in range(add):
            thisOffset = offset + offset * 2 * j
            currentIndex += 1
            if index == currentIndex:
                foundOffset = thisOffset
                break
        if foundOffset > 0:
            break
    return foundOffset

def getRing(col, row, cCol, cRow):
    return ceilInt(max(abs(cCol-col), abs(cRow-row)))

def initGridComposition(a, stepTime=False):
    startGridW, startGridH = tuple([int(v) for v in a.START_GRID.strip().split("x")])
    endGridW, endGridH = tuple([int(v) for v in a.END_GRID.strip().split("x")])
    gridW, gridH = tuple([int(v) for v in a.GRID.strip().split("x")])

    makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_DIR])

    _, samples = readCsv(a.INPUT_FILE)
    stepTime = logTime(stepTime, "Read CSV")
    sampleCount = len(samples)
    sampler = Sampler()
    container = Clip({
        "width": a.WIDTH,
        "height": a.HEIGHT,
        "cache": True
    })

    gridCount = gridW * gridH
    if gridCount > sampleCount:
        print("Not enough samples (%s) for the grid you want (%s x %s = %s). Exiting." % (sampleCount, gridW, gridH, gridCount))
        sys.exit()
    elif gridCount < sampleCount:
        print("Too many samples (%s), limiting to %s" % (sampleCount, gridCount))
        samples = samples[:gridCount]
        sampleCount = gridCount

    # further reduce sample size if grid is larger than max grid in composition
    maxGridW, maxGridH = (max(startGridW, endGridW), max(startGridH, endGridH))
    offsetGridX, offsetGridY = (int((gridW-maxGridW)/2), int((gridH-maxGridH)/2))
    if offsetGridX > 0 or offsetGridY > 0:
        subset = []
        for s in samples:
            if offsetGridX <= s["gridX"] < (offsetGridX + maxGridW) and offsetGridY <= s["gridY"] < (offsetGridY+maxGridH):
                subset.append(s)
        samples = subset[:]
        sampleCount = len(samples)
        gridW = maxGridW
        gridH = maxGridH
        print("Reduced grid to %s x %s = %s" % (maxGridW, maxGridH, formatNumber(sampleCount)))

    # Sort by grid
    samples = sorted(samples, key=lambda s: (s["gridY"], s["gridX"]))
    samples = addIndices(samples)
    samples = prependAll(samples, ("filename", a.MEDIA_DIRECTORY))
    aspectRatio = (1.0*a.HEIGHT/a.WIDTH)
    samples = addGridPositions(samples, gridW, a.WIDTH, a.HEIGHT, marginX=a.CLIP_MARGIN, marginY=a.CLIP_MARGIN)
    if a.NOISE > 0:
        samples = addPositionNoise(samples, (-a.NOISE, a.NOISE), (-a.NOISE*aspectRatio, a.NOISE*aspectRatio), a.RANDOM_SEED+3)

    cCol, cRow = ((gridW-1) * 0.5, (gridH-1) * 0.5)
    for i, s in enumerate(samples):
        # Add audio properties
        # make clip longer if necessary
        audioDur = s["dur"]
        samples[i]["audioDur"] = audioDur
        samples[i]["dur"] = s["dur"] if s["dur"] > a.MIN_CLIP_DUR else int(math.ceil(1.0 * a.MIN_CLIP_DUR / s["dur"]) * s["dur"])
        samples[i]["pan"] = lerp((-1.0, 1.0), s["nx"])
        samples[i]["fadeOut"] = getClipFadeDur(audioDur, percentage=0.5, maxDur=-1)
        samples[i]["fadeIn"] = getClipFadeDur(audioDur)
        samples[i]["reverb"] = a.REVERB
        samples[i]["matchDb"] = a.MATCH_DB
        samples[i]["maxDb"] = a.MAX_DB
        samples[i]["distanceFromCenter"] = distance(cCol, cRow, s["col"], s["row"])
    samples = addNormalizedValues(samples, "distanceFromCenter", "nDistanceFromCenter")

    # limit the number of clips playing
    if sampleCount > a.MAX_AUDIO_CLIPS and a.MAX_AUDIO_CLIPS > 0:
        samples = limitAudioClips(samples, a.MAX_AUDIO_CLIPS, "nDistanceFromCenter", keepFirst=a.KEEP_FIRST_AUDIO_CLIPS, invert=True, seed=(a.RANDOM_SEED+3))
        stepTime = logTime(stepTime, "Calculate which audio clips are playing")

        # show a viz of which frames are playing
        if a.DEBUG:
            for i, s in enumerate(samples):
                samples[i]["alpha"] = 1.0 if s["playAudio"] else 0.2
            clipsToFrame({ "filename": a.OUTPUT_FRAME % "playTest", "width": a.WIDTH, "height": a.HEIGHT, "overwrite": True, "debug": True },
                samplesToClips(samples), loadVidoPixelDataDebug(len(samples)))
            # reset alpha
            for i, s in enumerate(samples):
                samples[i]["alpha"] = 1.0

    return (samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH)

def limitAudioClips(samples, maxAudioClips, keyName, invert=False, keepFirst=64, multiplier=10000, easing="quartOut", seed=3):
    indicesToKeep = []
    shuffleSamples = samples[:]
    shuffleSampleCount = maxAudioClips
    if maxAudioClips > keepFirst:
        shuffleSampleCount -= keepFirst
        keepSamples = samples[:keepFirst]
        indicesToKeep = [s["index"] for s in keepSamples]
        shuffleSamples = shuffleSamples[keepFirst:]
    samplesToPlay = weightedShuffle(shuffleSamples, [ease((1.0 - s[keyName] if invert else s[keyName]) * multiplier, easing) for s in shuffleSamples], count=shuffleSampleCount, seed=seed)
    indicesToKeep = set(indicesToKeep + [s["index"] for s in samplesToPlay])
    for i, s in enumerate(samples):
        samples[i]["playAudio"] = (s["index"] in indicesToKeep)
    return samples

def processComposition(a, clips, videoDurationMs, sampler=None, stepTime=False, startTime=False, customClipToArrFunction=None, containsAlphaClips=False, isSequential=False):

    # get audio sequence
    samplerClips = sampler.getClips() if sampler is not None else []

    # kind of a hack: check to see if we're debugging sampler audio
    if len(samplerClips) > 0 and a.DEBUG and a.AUDIO_ONLY and os.path.isfile(a.AUDIO_OUTPUT_FILE):
        processSamplerClips(a, samplerClips)
        stepTime = logTime(stepTime, "Processed audio clip sequence")
        logTime(startTime, "Total execution time")
        return True

    audioSequence = clipsToSequence(clips + samplerClips)
    stepTime = logTime(stepTime, "Processed audio clip sequence")

    # plotAudioSequence(audioSequence)
    # sys.exit()

    # account for excerpt
    excerptStartMs = roundInt(a.EXCERPT_START * 1000) if a.EXCERPT_START >= 0 else False
    excerptDurMs = roundInt(a.EXCERPT_DUR * 1000) if a.EXCERPT_DUR > 0 else False
    excerpted = (excerptStartMs is not False and excerptDurMs is not False)
    excerptEndMs = (excerptStartMs + excerptDurMs) if excerpted else False
    excerptFrameStart = msToFrame(excerptStartMs, a.FPS) if excerpted else False
    if excerpted:
        audioSequence = [s for s in audioSequence if excerptStartMs <= s["ms"] <= excerptEndMs]

    audioDurationMs = getAudioSequenceDuration(audioSequence)
    durationMs = max(videoDurationMs, audioDurationMs) + a.PAD_END

    if excerpted:
        videoDurationMs = excerptDurMs
        audioDurationMs = excerptDurMs
        durationMs = excerptDurMs + a.PAD_END

    print("Video time: %s" % formatSeconds(videoDurationMs/1000.0))
    print("Audio time: %s" % formatSeconds(audioDurationMs/1000.0))
    print("Total time: %s" % formatSeconds(durationMs/1000.0))

    # sort frames and plays
    for clip in clips:
        clip.vector.sortFrames()
        clip.sortPlays()

    # sys.exit()

    # adjust frames if audio is longer than video
    totalFrames = msToFrame(durationMs, a.FPS) if durationMs > videoDurationMs else msToFrame(videoDurationMs, a.FPS)
    print("Total frames: %s" % totalFrames)

    # get frame sequence
    videoFrames = []
    print("Making video frame sequence...")
    for f in range(totalFrames):
        frame = f + 1
        ms = frameToMs(frame, a.FPS)
        if excerpted and (ms < excerptStartMs or ms > excerptEndMs):
            continue
        elif excerpted:
            frame -= excerptFrameStart
        videoFrames.append({
            "filename": a.OUTPUT_FRAME % zeroPad(frame, totalFrames),
            "ms": ms,
            "width": a.WIDTH,
            "height": a.HEIGHT,
            "overwrite": a.OVERWRITE,
            "debug": a.DEBUG
        })
    stepTime = logTime(stepTime, "Processed video frame sequence")

    rebuildAudio = (not a.VIDEO_ONLY and (not os.path.isfile(a.AUDIO_OUTPUT_FILE) or a.OVERWRITE))
    rebuildVideo = (not a.AUDIO_ONLY and (len(videoFrames) > 0 and not os.path.isfile(videoFrames[-1]["filename"]) or a.OVERWRITE))

    if rebuildAudio:
        mixAudio(audioSequence, durationMs, a.AUDIO_OUTPUT_FILE)
        stepTime = logTime(stepTime, "Mix audio")

    if rebuildVideo:
        clipsPixelData = loadVideoPixelDataFromFrames(videoFrames, clips, a.WIDTH, a.HEIGHT, a.FPS, a.CACHE_DIR, a.CACHE_KEY, a.VERIFY_CACHE, cache=True, debug=a.DEBUG, precision=a.PRECISION, customClipToArrFunction=customClipToArrFunction)
        stepTime = logTime(stepTime, "Loaded pixel data")
        if a.OVERWRITE:
            removeFiles(a.OUTPUT_FRAME % "*")
        colors = 4 if containsAlphaClips else 3
        globalArgs = {
            "colors": colors,
            "isSequential": isSequential,
            "frameAlpha": a.FRAME_ALPHA,
            "blendClips": a.BLEND_CLIPS
        }
        processFrames(videoFrames, clips, clipsPixelData, threads=a.THREADS, precision=a.PRECISION, customClipToArrFunction=customClipToArrFunction, globalArgs=globalArgs)

    if not a.AUDIO_ONLY:
        audioFile = a.AUDIO_OUTPUT_FILE if not a.VIDEO_ONLY and os.path.isfile(a.AUDIO_OUTPUT_FILE) else False
        quality = "medium" if a.DEBUG else "high"
        compileFrames(a.OUTPUT_FRAME, a.FPS, a.OUTPUT_FILE, getZeroPadding(totalFrames), audioFile=audioFile, quality=quality)

    logTime(startTime, "Total execution time")

def processSamplerClips(a, clips):
    baseClip = Clip({"filename": a.AUDIO_OUTPUT_FILE})
    parts = a.AUDIO_OUTPUT_FILE.split(".")
    newFilename = ".".join(parts[:-1] + ["with","sampler"] + [parts[-1]])
    baseClip.queuePlay(0)
    audioSequence = clipsToSequence([baseClip] + clips)
    mixAudio(audioSequence, baseClip.dur, newFilename)
