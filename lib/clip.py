from lib.collection_utils import *
from lib.math_utils import *

class Vector:

    def __init__(self, props={}):
        defaults = {
            "width": 100.0, "height": 100.0,
            "x": 0.0, "y": 0.0, "z": 0.0, # position
            "origin": [0.0, 0.0], "transformOrigin": [0.5, 0.5],
            "rotation": 0.0, "scale": [1.0, 1.0], "translate": [0.0, 0.0, 0.0],
            "alpha": 1.0, "blur": 0.0,
            "parent": None, "cache": False
        }
        defaults.update(props)
        self.props = defaults

        self.pos = [0.0, 0.0, 0.0]
        self.size = [100.0, 100.0]
        self.keyframes = {}

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

    def addKeyFrame(self, name, ms, value, easing="linear"):
        keyframe = {"name": name, "ms": ms, "value": value, "dimension": None, "easing": easing}
        # scale and translate instead of changing width/height/x/y
        if name == "width":
            scaleValue = self.getScaleFromWidth(value)
            keyframe.update({"name": "scale", "dimension": 0, "value": scaleValue})
        elif name == "height":
            scaleValue = self.getScaleFromHeight(value)
            keyframe.update({"name": "scale", "dimension": 1, "value": scaleValue})
        elif name == "x":
            keyframe.update({"name": "translate", "dimension": 0})
        elif name == "y":
            keyframe.update({"name": "translate", "dimension": 1})

        if name in self.keyframes:
            self.keyframes[name].append(keyframe)
            self.keyframes[name] = sorted(self.keyframes[name], key=lambda k: k["ms"])
        else:
            self.keyframes[name] = [keyframe]

    def getAlpha(self, ms=None):
        return self.getPropValue("alpha", ms=ms)

    def getBlur(self, ms=None):
        return self.getPropValue("blur", ms=ms)

    def getHeight(self, ms=None):
        return self.getSizeDimension(1, ms)

    def getPos(self, ms=None):
        return (self.getX(ms), self.getY(ms))

    def getPosDimension(self, i, ms=None):
        d = self.getPropValue("pos", i, ms)
        # account for origin
        length = self.getPropValue("size", i, ms)
        origin = self.origin[i]
        d -= length * origin
        # account for scale
        dto = self.transformOrigin[i]
        tlength = length * self.getPropValue("scale", i, ms)
        d -= (tlength - length) * dto
        # account for translate
        d += self.getPropValue("translate", i, ms)

        # account for parent
        if self.parent is not None:
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
        keyframes = self.keyframes[name] if name in self.keyframes else []
        keyframes = [k for k in keyframes if k["dimension"]==dimension or k["dimension"] is None or dimension is None]
        kcount = len(keyframes)

        # assuming keyframes are sorted
        for i, kf in enumerate(keyframes):
            # we're before the first frame
            if ms < kf["ms"] and i <= 0:
                fromValue = value
                toValue = kf["value"]
                value = lerpEase((fromValue, toValue), 1.0*ms/kf["ms"], kf["easing"])
                break
            elif ms >= kf["ms"]:
                fromValue = kf["value"]
                # we've passed the last keyframe, just take it's value
                if i >= kcount-1:
                    value = fromValue
                # otherwise, we're between two keyframes
                else:
                    kf1 = keyframes[i+1]
                    toValue = kf1["value"]
                    value = lerpEase((fromValue, toValue), norm(ms, (kf["ms"], kf1["ms"])), kf1["easing"])
                break

        if self.cache:
            self.cacheProps[nameKey] = value

        return value

    def getPropsAtTime(self, ms):
        props = {
            "x": roundInt(self.getX(ms)),
            "y": roundInt(self.getY(ms)),
            "width": roundInt(self.getWidth(ms)),
            "height": roundInt(self.getHeight(ms)),
            "rotation": self.getRotation(ms),
            "alpha": self.getAlpha(ms),
            "blur": self.getBlur(ms)
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

    def getSizeDimension(self, i, ms=None):
        d = self.getPropValue("size", i, ms) * self.getPropValue("scale", i, ms)
        if self.parent is not None:
            d *= self.parent.getPropValue("scale", i, ms)
        return d

    def getWidth(self, ms=None):
        return self.getSizeDimension(0, ms)

    def getX(self, ms=None):
        return self.getPosDimension(0, ms)

    def getY(self, ms=None):
        return self.getPosDimension(1, ms)

    def isVisible(self, containerW, containerH, ms=None):
        x, y = self.getPos(ms)
        w, h = self.getSize(ms)
        return (x+w) > 0 and (y+h) > 0 and x < containerW and y < containerH

    def setAlpha(self, alpha):
        self.alpha = alpha

    def setBlur(self, blur):
        self.blur = blur

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

    def setTransform(self, translate=None, scale=None, rotation=None):
        if translate is not None:
            self.translate = translate
        if scale is not None:
            self.scale = scale
        if rotation is not None:
            self.rotation = rotation

    def setTransformorigin(self, origin):
        self.transformOrigin = origin

class Clip:

    def __init__(self, props={}):
        self.props = props
        defaults = {
            "filename": None,
            "start": 0,
            "dur": 0,
            "state": {},
            "plays": []
        }

        defaults.update(props)
        self.props = defaults

        self.filename = defaults["filename"]
        self.start = defaults["start"]
        self.dur = defaults["dur"]
        self.plays = defaults["plays"]

        self.setFadeIn(getClipFadeDur(self.dur))
        self.setFadeOut(getClipFadeDur(self.dur, 0.25))

        self.setVector(Vector(defaults))
        self.setStates(defaults["state"])

    def getClipTime(self, ms):
        plays = [t for t in self.plays if t[0] <= ms <= t[1]]
        time = 0.0
        start = 0

        # check if we are playing this clip at this time
        if len(plays) > 0:
            for p in plays:
                start, end, params = p

        # otherwise, find the closest play
        elif len(self.plays) > 0:
            plays = sorted(self.plays, key=lambda p: abs(ms - lerp((p[0], p[1]), 0.5)))
            closestPlay = plays[0]
            start, end, params =  closestPlay

        msSincePlay = ms - start
        remainder = msSincePlay % self.dur
        time = roundInt(self.start + remainder)

        return time

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

    def queuePlay(self, ms, params={}):
        dur = self.dur
        self.plays.append((ms, ms+dur, params))

    def queueTween(self, ms, dur="auto", tweens=[]):
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
            self.vector.addKeyFrame(name, ms, fromValue, easing)
            if dur > 0:
                self.vector.addKeyFrame(name, ms+dur, toValue, easing)

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

    def toDict(self, ms):
        props = self.props.copy()
        t = self.getClipTime(ms)
        props.update({
            "t": t,
            "tn": norm(t, (self.start, self.start+self.dur), limit=True)
        })
        props.update(self.vector.getPropsAtTime(ms))
        return props

def clipsToDicts(clips, ms):
    dicts = []
    count = len(clips)
    # startTime = logTime()
    for i, clip in enumerate(clips):
        # Get video data
        dicts.append(clip.toDict(ms))
        # sys.stdout.write('\r')
        # sys.stdout.write("%s%%" % round(1.0*(i+1)/count*100,1))
        # sys.stdout.flush()
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

def getClipFadeDur(clipDur, percentage=0.1, maxDur=100):
    dur = roundInt(clipDur * percentage)
    dur = min(dur, maxDur)
    return dur

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
            clips[i].state[key] = value

    return clips
