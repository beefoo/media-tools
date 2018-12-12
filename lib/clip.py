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
            "rotate": 0.0, "scale": 0.0, "translate": (0.0, 0.0)
        }
        defaults.update(props)
        self.props = defaults

        self.setSize(defaults["width"], defaults["height"])
        self.setPos(defaults["x"], defaults["y"], defaults["z"])
        self.setVeloc(defaults["vx"], defaults["vy"], defaults["vz"])
        self.setAccel(defaults["ax"], defaults["ay"], defaults["az"])

        self.setTransform(defaults["translate"], defaults["scale"], defaults["rotate"])
        self.setOrigin(defaults["origin"])

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

    def setTransform(self, translate=None, scale=None, rotate=None):
        if translate is not None:
            self.translate = translate
        if scale is not None:
            self.scale = scale
        if rotate is not None:
            self.rotate = rotate

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
            "alpha": 0.0,
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
        self.setVector(Vector(defaults))
        self.setStates(defaults["state"])

    def getClipTime(self, ms):
        plays = [t for t in self.plays if t[0] <= ms <= t[1]]
        time = 0.0
        for p in plays:
            start, end, params = p
            n = norm(ms, (start, end))
            if 0.0 <= n <= 1.0:
                time = n * self.dur / 1000.0
        return time

    def getTweenedProperties(self, ms):
        tweens = [t for t in self.tweens if t[0] < ms < t[1]]
        props = {
            "x": self.vector.x,
            "y": self.vector.y,
            "width": self.vector.width,
            "height": self.vector.height,
            "alpha": self.alpha
        }
        for t in tweens:
            start, end, tprops = t
            p = norm(ms, (start, end))
            for tprop in tprops:
                name, tfrom, tto = tprop
                props[name] = lerp((tfrom, tto), p)
        return props

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

    def setState(self, key, value):
        self.state[key] = value

    def setStates(self, state):
        self.state = state

    def setVector(self, vector):
        self.vector = Vector() if vector is None else vector

def getTweenedClips(clips, ms):
    props = []
    for clip in clips:
        props.append(clip.getTweenedProperties(ms))
    return props

def clipsToParams(clips, ms):
    params = []
    for clip in clips:
        props = clip.getTweenedProperties(ms)
        props["t"] = clip.getClipTime(ms)
        params.append(props)
    return params

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
