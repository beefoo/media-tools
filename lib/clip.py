from collection_utils import *
from math_utils import *

class Vector:

    def __init__(self, props={}):
        defaults = {
            "width": 1.0, "height": 1.0,
            "x": 0.0, "y": 0.0, "z": 0.0, # position
            "vx": 0.0, "vy": 0.0, "vz": 0.0, # velocity
            "ax": 0.0, "ay": 0.0, "az": 0.0, # acceleration
            "origin": (0.0, 0.0),
            "rotation": 0.0, "scale": 0.0, "translate": (0.0, 0.0)
        }
        defaults.update(props)
        self.props = defaults

        self.setSize(defaults["width"], defaults["height"])
        self.setPos(defaults["x"], defaults["y"], defaults["z"])
        self.setVeloc(defaults["vx"], defaults["vy"], defaults["vz"])
        self.setAccel(defaults["ax"], defaults["ay"], defaults["az"])

        self.setTransform(defaults["translate"], defaults["scale"], defaults["rotation"])
        self.setOrigin(defaults["origin"])

    def getX(self):
        x = self.x
        if self.origin[0] > 0.0:
            x -= self.width * self.origin[0]
        return x

    def getY(self):
        y = self.y
        if self.origin[1] > 0.0:
            y -= self.height * self.origin[1]
        return y

    def setAccel(self, x, y, z=None):
        self.ax = x
        self.ay = y
        if z is not None:
            self.az = z

    def setOrigin(self, origin):
        self.origin = origin

    def setPos(self, x, y, z=None):
        self.x = x
        self.y = y
        if z is not None:
            self.z = z

    def setSize(self, width, height):
        self.width = width
        self.height = height

    def setTransform(self, translate=None, scale=None, rotation=None):
        if translate is not None:
            self.translate = translate
        if scale is not None:
            self.scale = scale
        if rotation is not None:
            self.rotation = rotation

    def setVeloc(self, x, y, z=None):
        self.vx = x
        self.vy = y
        if z is not None:
            self.vz = z

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
            "width": self.vector.width,
            "height": self.vector.height,
            "alpha": self.alpha,
            "blur": self.blur,
            "rotation": self.vector.rotation
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

# def clipsToDicts(clips, ms, tweeningOnly=True):
#     dicts = []
#     if tweeningOnly:
#         clips = [clip for clip in clips if clip.isTweening(ms)]
#     for clip in clips:
#         dicts.append(clip.toDict(ms))
#     return dicts

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
