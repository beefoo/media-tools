from lib.collection_utils import *
from lib.math_utils import *

class Vector:

    def __init__(self, props={}):
        defaults = {
            "width": 100.0, "height": 100.0,
            "x": 0.0, "y": 0.0, "z": 0.0, # position
            "origin": [0.0, 0.0], "transformOrigin": [0.5, 0.5],
            "rotation": 0.0, "scale": [1.0, 1.0], "translate": [0.0, 0.0, 0.0],
            "parent": None
        }
        defaults.update(props)
        self.props = defaults

        self.pos = [0.0, 0.0, 0.0]
        self.size = [100.0, 100.0]

        self.setSize(defaults["width"], defaults["height"])
        self.setPos(defaults["x"], defaults["y"], defaults["z"])
        self.setTransform(defaults["translate"], defaults["scale"], defaults["rotation"])
        self.setOrigin(defaults["origin"])
        self.setTransformorigin(defaults["transformOrigin"])
        self.setParent(defaults["parent"])

    def getHeight(self):
        return self.getSizeDimension(1)

    def getPos(self):
        return (self.getX(), self.getY())

    def getPosDimension(self, i):
        d = self.pos[i]
        # account for origin
        length = self.size[i]
        origin = self.origin[i]
        d -= length * origin
        # account for scale
        dto = self.transformOrigin[i]
        tlength = length * self.scale[i]
        d -= (tlength - length) * dto
        # account for translate
        d += self.translate[i]

        # account for parent
        if self.parent is not None:
            p = self.parent
            pD = p.getPosDimension(i)
            pLength = p.size[i]
            pTLength = p.getSizeDimension(i)
            nd = 1.0 * d / pLength
            d = pTLength * nd + pD

        return d

    def getRotation(self):
        r = self.rotation
        return r

    def getScaleFromWidth(self, w):
        return 1.0 * w / self.size[0]

    def getSize(self):
        return (self.getWidth(), self.getHeight())

    def getSizeDimension(self, i):
        d = self.size[i] * self.scale[i]
        if self.parent is not None:
            d *= self.parent.scale[i]
        return d

    def getWidth(self):
        return self.getSizeDimension(0)

    def getX(self):
        return self.getPosDimension(0)

    def getY(self):
        return self.getPosDimension(1)

    def isVisible(self, containerW, containerH):
        x, y = self.getPos()
        w, h = self.getSize()
        return (x+w) > 0 and (y+h) > 0 and x < containerW and y < containerH

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
            "alpha": 1.0,
            "blur": 0.0,
            "state": {},
            "tweens": [],
            "plays": []
        }

        defaults.update(props)
        self.props = defaults

        self.filename = defaults["filename"]
        self.start = defaults["start"]
        self.dur = defaults["dur"]
        self.tweens = defaults["tweens"]
        self.plays = defaults["plays"]

        self.setFadeIn(getClipFadeDur(self.dur))
        self.setFadeOut(getClipFadeDur(self.dur, 0.25))

        self.setAlpha(defaults["alpha"])
        self.setBlur(defaults["blur"])
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

    def getDefaultVectorProperties(self):
        return {
            "x": self.vector.getX(),
            "y": self.vector.getY(),
            "width": self.vector.getWidth(),
            "height": self.vector.getHeight(),
            "alpha": self.alpha,
            "blur": self.blur,
            "rotation": self.vector.getRotation()
        }

    def getFilledTweens(self):
        ftweens = []
        defaults = self.getDefaultVectorProperties()
        for i, t in enumerate(self.tweens):
            start, end, tprops = t
            pstart = pend = 0
            ptprops = []

            # get previous tween
            if i > 0:
                pstart, pend, ptprops = self.tweens[i-1]

            if pend < start:
                # get combined tween names from previous and current tweens
                tnames = unique([p[0] for p in ptprops] + [p[0] for p in tprops])
                # get the filler properties
                ftprops = []
                for tname in tnames:
                    # tween from the end of the previous to the begenning of the current
                    ptpropsMatches = [p for p in ptprops if p[0]==tname]
                    tfrom = ptpropsMatches[0][2] if len(ptpropsMatches) > 0 else defaults[tname]
                    tpropsMatches = [p for p in tprops if p[0]==tname]
                    tto = tpropsMatches[0][1] if len(tpropsMatches) > 0 else defaults[tname]
                    ftprops.append((tname, tfrom, tto))
                ftweens.append((pend, start, ftprops))
            ftweens.append(t)

        return ftweens

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

    def getTweenedProperties(self, ms):
        tweens = self.getFilledTweens()
        tweens = [t for t in tweens if t[0] < ms <= t[1]]
        # set default properties that can be tweened
        props = {}
        for t in tweens:
            start, end, tprops = t
            p = norm(ms, (start, end))
            for tprop in tprops:
                name = tfrom = tto = None
                easing = "linear"
                if len(tprop) == 3:
                    name, tfrom, tto = tprop
                elif len(tprop) == 4:
                    name, tfrom, tto, easing = tprop
                if easing == "sin":
                    p = easeIn(p)
                value = lerp((tfrom, tto), p)
                if name in props:
                    props[name] = max(value, props[name])
                else:
                    props[name] = value
        return props

    def isTweening(self, ms):
        tweens = [t for t in self.tweens if t[0] < ms <= t[1]]
        return len(tweens) > 0

    def queuePlay(self, ms, params={}):
        dur = self.dur
        self.plays.append((ms, ms+dur, params))

    def queueTween(self, ms, dur="auto", tweens=[]):
        if isinstance(tweens, tuple):
            tweens = [tweens]

        if dur == "auto":
            dur = self.dur

        self.tweens.append((ms, ms+dur, tweens))

    def setAlpha(self, alpha):
        self.alpha = alpha

    def setBlur(self, blur):
        self.blur = blur

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
        props.update(self.getDefaultVectorProperties())
        props.update({
            "t": t,
            "tn": norm(t, (self.start, self.start+self.dur), limit=True)
        })
        if len(self.tweens) > 0:
            props.update(self.getTweenedProperties(ms))
        return props

def clipsToDicts(clips, ms):
    dicts = []
    for clip in clips:
        dicts.append(clip.toDict(ms))
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
