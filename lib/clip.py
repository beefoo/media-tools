from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool

from lib.collection_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.audio_utils import getDurationFromAudioFile

def isClipVisible(clip, width, height):
    isInFrame = clip["x"]+clip["width"] > 0 and clip["y"]+clip["height"] > 0 and clip["x"] < width and clip["y"] < height
    alpha = clip["alpha"] if "alpha" in clip else 1.0
    isOpaque = alpha > 0
    return isInFrame and isOpaque

class Vector:

    def __init__(self, props={}):
        defaults = {
            "width": 100.0, "height": 100.0,
            "x": 0.0, "y": 0.0, "z": 0.0, # position
            "origin": [0.0, 0.0], "transformOrigin": [0.5, 0.5],
            "rotation": 0.0, "scale": [1.0, 1.0], "translate": [0.0, 0.0, 0.0],
            "alpha": 1.0, "blur": 0.0, "brightness": 1.0,
            "parent": None, "cache": False
        }
        defaults.update(props)
        self.props = defaults

        self.pos = [0.0, 0.0, 0.0]
        self.size = [100.0, 100.0]
        self.keyframes = []

        # for caching
        self.cache = defaults["cache"]
        self.lastMs = -1
        self.cacheProps = {}

        self.setSize(defaults["width"], defaults["height"])
        self.setPos(defaults["x"], defaults["y"], defaults["z"])
        self.setTransform(defaults["translate"], defaults["scale"], defaults["rotation"])
        self.setOrigin(defaults["origin"])
        self.setTransformorigin(defaults["transformOrigin"])
        self.setParent(defaults["parent"])
        self.setAlpha(defaults["alpha"])
        self.setBlur(defaults["blur"])
        self.setBrightness(defaults["brightness"])

    def addKeyFrame(self, name, ms, value, easing="linear", sortFrames=False):
        keyframe = {"name": name, "ms": ms, "value": value, "dimension": None, "easing": easing}
        # scale and translate instead of changing width/height/x/y
        if name == "width":
            scaleValue = self.getScaleFromWidth(value)
            keyframe.update({"name": "scale", "dimension": 0, "value": scaleValue})
        elif name == "height":
            scaleValue = self.getScaleFromHeight(value)
            keyframe.update({"name": "scale", "dimension": 1, "value": scaleValue})
        elif name == "translateX":
            keyframe.update({"name": "translate", "dimension": 0})
        elif name == "translateY":
            keyframe.update({"name": "translate", "dimension": 1})
        elif name == "x":
            keyframe.update({"name": "pos", "dimension": 0})
        elif name == "y":
            keyframe.update({"name": "pos", "dimension": 1})

        self.keyframes.append(keyframe)
        if sortFrames:
            self.sortFrames()

    def getAlpha(self, ms=None):
        return self.getPropValue("alpha", ms=ms)

    def getBlur(self, ms=None):
        return self.getPropValue("blur", ms=ms)

    def getBrightness(self, ms=None):
        return self.getPropValue("brightness", ms=ms)

    def getHeight(self, ms=None, parent=None, customProps=None):
        return self.getSizeDimension(1, ms, parent, customProps)

    def getPos(self, ms=None):
        return (self.getX(ms), self.getY(ms))

    def getPosDimension(self, i, ms=None, parent=None, customProps=None):
        d = customProps["pos"][i] if customProps is not None and "pos" in customProps else self.getPropValue("pos", i, ms)
        # account for origin
        length = customProps["size"][i] if customProps is not None and "size" in customProps else self.getPropValue("size", i, ms)
        origin = self.origin[i]
        d -= length * origin
        # account for scale
        dto = self.transformOrigin[i]
        tlength = length * self.getPropValue("scale", i, ms)
        d -= (tlength - length) * dto
        # account for translate
        d += self.getPropValue("translate", i, ms)

        # account for parent
        if parent is not None:
            pD = parent["pos"][i]
            pLength = parent["baseSize"][i]
            pTLength = parent["size"][i]
            nd = 1.0 * d / pLength
            d = pTLength * nd + pD
        elif self.parent is not None:
            p = self.parent
            pD = p.getPosDimension(i, ms)
            pLength = p.size[i]
            pTLength = p.getSizeDimension(i, ms)
            nd = 1.0 * d / pLength
            d = pTLength * nd + pD

        return d

    def getPropValue(self, name, dimension=None, ms=None):
        # avoid doing the same calculation over and over again
        nameKey = name if dimension is None else (name, dimension)
        if self.cache and ms is not None and self.lastMs == ms and nameKey in self.cacheProps:
            return self.cacheProps[nameKey]

        # reset cache if changed time
        if self.cache and ms is not None and self.lastMs != ms:
            self.cacheProps = {}
            self.lastMs = ms

        value = getattr(self, name)
        if dimension is not None:
            value = value[dimension]
        if ms is None:
            return value

        # retrieve keyframes for this property
        keyframes = [k for k in self.keyframes if k["name"]==name and (k["dimension"]==dimension or k["dimension"] is None or dimension is None)]
        kcount = len(keyframes)

        # assuming keyframes are sorted
        for i, kf in enumerate(keyframes):
            # we're after the last frame, just take the last frame's value
            if i >= kcount-1 and ms >= kf["ms"]:
                value = kf["value"]
                break
            # we just passed the current ms
            elif kf["ms"] > ms:

                # we're before the first keyframe, just take the first keyframe value
                if i <= 0:
                    value = kf["value"]
                    break

                # lerp between the current and previous keyframe
                kf0 = keyframes[i-1]
                fromValue = kf0["value"]
                toValue = kf["value"]
                value = lerpEase((fromValue, toValue), norm(ms, (kf0["ms"], kf["ms"])), kf["easing"])
                break

        if self.cache:
            self.cacheProps[nameKey] = value

        return value

    def getProps(self):
        return self.getPropsAtTime(None)

    def getPropsAtTime(self, ms, parent=None, customProps=None):
        props = {
            "x": self.getX(ms, parent, customProps),
            "y": self.getY(ms, parent, customProps),
            "width": self.getWidth(ms, parent, customProps),
            "height": self.getHeight(ms, parent, customProps),
            "alpha": self.getAlpha(ms),
            "rotation": self.getRotation(ms),
            "blur": self.getBlur(ms),
            "brightness": self.getBrightness(ms)
        }
        return props

    def getRotation(self, ms=None):
        return self.getPropValue("rotation", ms=ms)

    def getScaleFromHeight(self, h):
        return 1.0 * h / self.size[1]

    def getScaleFromWidth(self, w):
        return 1.0 * w / self.size[0]

    def getSize(self, ms=None):
        return (self.getWidth(ms), self.getHeight(ms))

    def getSizeDimension(self, i, ms=None, parent=None, customProps=None):
        d = customProps["size"][i] if customProps is not None and "size" in customProps else self.getPropValue("size", i, ms)
        d *= self.getPropValue("scale", i, ms)
        if parent is not None:
            d *= parent["scale"][i]
        elif self.parent is not None:
            d *= self.parent.getPropValue("scale", i, ms)
        return d

    def getWidth(self, ms=None, parent=None, customProps=None):
        return self.getSizeDimension(0, ms, parent, customProps)

    def getX(self, ms=None, parent=None, customProps=None):
        return self.getPosDimension(0, ms, parent, customProps)

    def getY(self, ms=None, parent=None, customProps=None):
        return self.getPosDimension(1, ms, parent, customProps)

    def isFullyVisible(self, containerW, containerH, ms=None, alphaCheck=True):
        x, y = self.getPos(ms)
        w, h = self.getSize(ms)
        alpha = self.getAlpha(ms) if alphaCheck else 1.0
        return x >= 0 and y >= 0 and (x+w) < containerW and (y+h) < containerH and alpha > 0

    def isVisible(self, containerW, containerH, ms=None, alphaCheck=True):
        x, y = self.getPos(ms)
        w, h = self.getSize(ms)
        alpha = self.getAlpha(ms) if alphaCheck else 1.0
        return (x+w) > 0 and (y+h) > 0 and x < containerW and y < containerH and alpha > 0

    def plotKeyframes(self, name, dimension=None, additionalPlots=[]):
        import matplotlib.pyplot as plt
        keyframes = [k for k in self.keyframes if k["name"]==name and k["dimension"]==dimension]
        keyframes = sorted(keyframes, key=lambda k: k["ms"])
        for xs, ys in additionalPlots:
            plt.plot(xs, ys)
        for i, kf in enumerate(keyframes):
            if i < 1:
                continue
            prev = keyframes[i-1]
            if prev["ms"] >= kf["ms"]:
                continue
            s0 = prev["ms"]/1000.0
            s1 = kf["ms"]/1000.0
            steps = roundInt((s1 - s0) * 100)
            xs = np.linspace(s0, s1, steps)
            ys = []
            for j in range(steps):
                n = 1.0 * j / (steps-1)
                value = lerpEase((prev["value"], kf["value"]), n, kf["easing"])
                ys.append(value)
            plt.plot(xs, ys)
        plt.show()

    def setAlpha(self, alpha):
        self.alpha = alpha

    def setBlur(self, blur):
        self.blur = blur

    def setBrightness(self, brightness):
        self.brightness = brightness

    def setOrigin(self, origin):
        self.origin = origin

    def setParent(self, parent):
        self.parent = parent

    def setPos(self, x=None, y=None, z=None):
        if x is not None:
            self.pos[0] = x
        if y is not None:
            self.pos[1] = y
        if z is not None:
            self.pos[2] = z

    def setSize(self, width=None, height=None):
        if width is not None:
            self.size[0] = width
        if height is not None:
            self.size[1] = height
        self.aspectRatio = 1.0 * self.size[0] / self.size[1]

    def setTransform(self, translate=None, scale=None, rotation=None):
        if translate is not None:
            self.translate = translate
        if scale is not None:
            self.scale = scale
        if rotation is not None:
            self.rotation = rotation

    def setTransformorigin(self, origin):
        self.transformOrigin = origin

    def sortFrames(self):
        self.keyframes = sorted(self.keyframes, key=lambda k: k["ms"])

    def toDict(self, ms):
        return {
            "pos": self.getPos(ms),
            "baseSize": (self.size[0], self.size[1]),
            "size": self.getSize(ms),
            "scale": (self.getPropValue("scale", 0, ms), self.getPropValue("scale", 1, ms))
        }

class Clip:

    npProperties = [("x", "f"), ("y", "f"), ("width", "f"), ("height", "f"), ("alpha", "f"), ("tn", "f"), ("zindex", "i"), ("rotation", "f"), ("blur", "f"), ("brightness", "f")]
    gpuPropertyCount = 10

    @staticmethod
    def npPropertyCount():
        return len(Clip.npProperties)

    def __init__(self, props={}):
        self.props = props
        defaults = {
            "filename": None,
            "start": 0,
            "dur": 0,
            "state": {},
            "plays": [],
            "index": 0,
            "initialOffset": 0
        }

        defaults.update(props)
        self.props = defaults

        self.filename = defaults["filename"]
        self.start = defaults["start"]
        self.dur = defaults["dur"]
        self.plays = defaults["plays"]
        self.initialOffset = defaults["initialOffset"]

        if self.dur <= 0 and self.filename is not None:
            self.dur = getDurationFromAudioFile(self.filename)
        self.dur = max(1, self.dur)

        self.setFadeIn(getClipFadeDur(self.dur))
        self.setFadeOut(getClipFadeDur(self.dur, 0.25))

        self.setVector(Vector(defaults))
        self.setStates(defaults["state"])

    def getClipTime(self, ms):
        if ms is None:
            return 0.0

        plays = [t for t in self.plays if t[0] <= ms <= t[1]]
        time = 0.0
        start = 0

        # check if we are playing this clip at this time
        if len(plays) > 0:
            start, end, params = plays[0]

        # otherwise, find the closest play
        elif len(self.plays) > 0:
            plays = sorted(self.plays, key=lambda p: abs(ms - lerp((p[0], p[1]), 0.5)))
            closestPlay = plays[0]
            start, end, params =  closestPlay

            # assumes plays are sorted
            firstPlay = self.plays[0]
            lastPlay = self.plays[-1]

            # if we are before the first play or after the last one, set to initial offset
            # for continuity between compositions
            if ms < firstPlay[0] or ms > lastPlay[1]:
                start = self.initialOffset

        msSincePlay = ms - start
        remainder = msSincePlay % self.dur

        # play forward and backward
        if msSincePlay > self.dur:
            dremainder = msSincePlay % int(self.dur*2)
            # go backwards the 2nd half
            if dremainder > self.dur:
                remainder = max(0, self.dur - 1 - remainder)

        time = roundInt(self.start + remainder)
        return time

    def getGridNeighbors(self, clips, gridW, gridH, dimCol="col", dimRow="row", isSorted=True):
        col = self.props[dimCol]
        row = self.props[dimRow]

        if not isSorted:
            clips = sorted(clips, key=lambda c: (c.props[dimRow], c.props[dimCol]))

        neighbors = []
        for i in range(3):
            for j in range(3):
                ncol = col+i-1
                nrow = row+j-1
                # exclude self, or out of bounds
                if ncol==col and nrow==row or not (0 <= ncol < gridW) or not (0 <= nrow < gridH):
                    continue
                neighbors.append(clips[nrow*gridW+ncol])

        return neighbors

    def getNeighbors(self, clips, count, dim1="x", dim2="y", idKey="index", newKey="distance"):
        myId = self.props[idKey]
        myDim1 = self.props[dim1]
        myDim2 = self.props[dim2]

        clips = [c for c in clips if c.props[idKey] !=myId]
        for i, c in enumerate(clips):
            clips[i].setProp(newKey, distance(myDim1, myDim2, c.props[dim1], c.props[dim2]))
        sortedByDistance = sorted(clips, key=lambda c: c.props[newKey])
        neighbors = sortedByDistance[:count]

        return neighbors

    def getState(self, name):
        return self.state[name] if name in self.state else None

    def queuePlay(self, ms, params={}):
        dur = params["dur"] if "dur" in params else self.dur
        self.plays.append((ms, ms+dur, params))

    def queueTween(self, ms, dur="auto", tweens=[], sortFrames=False):
        if isinstance(tweens, tuple):
            tweens = [tweens]

        if dur == "auto":
            dur = self.dur

        for tween in tweens:
            easing = "linear"
            if len(tween) == 4:
                name, fromValue, toValue, easing = tween
            else:
                name, fromValue, toValue = tween
            self.vector.addKeyFrame(name, ms, fromValue, easing, sortFrames)
            if dur > 0:
                self.vector.addKeyFrame(name, ms+dur, toValue, easing, sortFrames)

    def setFadeIn(self, fadeDur):
        self.fadeIn = fadeDur

    def setFadeOut(self, fadeDur):
        self.fadeOut = fadeDur

    def setProp(self, key, value):
        self.props[key] = value

    def setState(self, key, value):
        self.state[key] = value

    def setStates(self, state):
        self.state = state

    def setVector(self, vector):
        self.vector = Vector() if vector is None else vector

    def sortPlays(self):
        self.plays = sorted(self.plays, key=lambda p: p[0])

    def toDict(self, ms=None, containerW=None, containerH=None, parent=None, customProps=None):
        props = self.props.copy()
        t = self.getClipTime(ms)
        props.update({
            "t": t,
            "tn": norm(t, (self.start, self.start+self.dur), limit=True)
        })
        props["zindex"] = self.props["zindex"] if "zindex" in props else self.props["index"]+1
        props.update(self.vector.getPropsAtTime(ms, parent, customProps))
        # update properties if not visible
        if containerW is not None and containerH is not None:
            isVisible = isClipVisible(props, containerW, containerH)
            if not isVisible:
                props.update({
                    "x": 0,
                    "y": 0,
                    "width": 0,
                    "height": 0,
                    "alpha": 0
                })
        return props

    def toNpArr(self, ms=None, containerW=None, containerH=None, precision=3, parent=None, globalArgs={}):
        precisionMultiplier = int(10 ** precision)
        props = self.toDict(ms, containerW, containerH, parent)
        arr = np.zeros(self.npPropertyCount(), dtype=np.int32)
        for i, p in enumerate(self.npProperties):
            pkey, ptype = p
            value = roundInt(props[pkey] * precisionMultiplier) if ptype == "f" else roundInt(props[pkey])
            arr[i] = value
        return arr

def allClipStatesEqual(clips, key, value):
    areEqual = True
    for clip in clips:
        if clip.getState(key)!=value:
            areEqual = False
            break
    return areEqual

def clipArrToDict(clipArr, precision=3):
    precisionMultiplier = int(10 ** precision)
    d = {}
    for i, p in enumerate(Clip.npProperties):
        pkey, ptype = p
        d[pkey] = (1.0 * clipArr[i] / precisionMultiplier) if ptype == "f" else clipArr[i]
    return d

def clipToDict(p):
    ms, clip = p
    return clip.toDict(ms)

def clipsToNpArr(clips, ms=None, containerW=None, containerH=None, precision=3, customClipToArrFunction=None, globalArgs={}):
    # startTime = logTime()
    parentProps = clips[0].vector.parent.toDict(ms) if len(clips) > 0 and clips[0].vector.parent is not None else None
    clipCount = len(clips)
    propertyCount = Clip.npPropertyCount()
    arr = np.zeros((clipCount, propertyCount), dtype=np.int32)
    for i, clip in enumerate(clips):
        if customClipToArrFunction is not None:
            arr[clip.props["index"]] = customClipToArrFunction(clip, ms, containerW, containerH, precision, parentProps, globalArgs=globalArgs)
        else:
            arr[clip.props["index"]] = clip.toNpArr(ms, containerW, containerH, precision, parentProps, globalArgs=globalArgs)
    # stepTime = logTime(startTime, "Step %s" % ms)
    return arr

def clipsToDicts(clips, ms=None, threads=-1):
    # startTime = logTime()
    threads = getThreadCount(threads)

    dicts = []
    if threads <= 1:
        for i, clip in enumerate(clips):
            dicts.append(clip.toDict(ms))
    else:
        pool = ThreadPool(threads)
        dicts = pool.map(clipToDict, zip([ms for i in range(len(clips))], clips))
        pool.close()
        pool.join()

    # stepTime = logTime(startTime, "Step %s" % ms)
    return dicts

def clipsToSequence(clips):
    audioSequence = []
    for clip in clips:
        for play in clip.plays:
            start, end, params = play
            p = {
                "filename": clip.filename,
                "ms": start,
                "start": clip.start,
                "dur": clip.dur
            }
            p.update(params)
            audioSequence.append(p)
    return audioSequence

def filterClips(clips, filters):
    clipProps = []
    for i, clip in enumerate(clips):
        props = clip.props.copy()
        props["index"] = i
        clipProps.append(props)
    clipProps = filterWhere(clipProps, filters)
    indices = set([c["index"] for c in clipProps])
    return [c for i, c in enumerate(clips) if i in indices]

def getClipFadeDur(clipDur, percentage=0.1, maxDur=100):
    dur = roundInt(clipDur * percentage)
    if maxDur > 0:
        dur = min(dur, maxDur)
    return dur

def getVisibleClipsAtTime(containerW, containerH, clips, ms):
    return [clip for clip in clips if clip.vector.isVisible(containerW, containerH, ms, alphaCheck=False)]

def getNeighborClips(clips, gridCx, gridCy, gridW, gridH, radius):
    ccol = roundInt(gridCx)
    crow = roundInt(gridCy)
    iradius = roundInt(radius)+2
    halfRadius = roundInt(iradius/2)

    cols = [c+ccol-halfRadius for c in range(iradius)]
    rows = [c+crow-halfRadius for c in range(iradius)]

    frameClips = []
    for col in cols:
        for row in rows:
            # wrap around
            x = col % gridW
            y = row % gridH
            i = y * gridW + x
            clip = clips[i]
            distanceFromCenter = distance(col, row, gridCx, gridCy)
            nDistanceFromCenter = 1.0 - 1.0 * distanceFromCenter / radius
            frameClips.append((nDistanceFromCenter, clip))

    return frameClips

def samplesToClips(samples):
    clips = []
    for sample in samples:
        clip = Clip(sample)
        clips.append(clip)
    return clips

def updateClipStates(clips, updates):
    if isinstance(updates, tuple):
        updates = [updates]

    for i, clip in enumerate(clips):
        for u in updates:
            key, value = u
            clip.setState(key, value)

    return clips
