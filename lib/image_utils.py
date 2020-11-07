# -*- coding: utf-8 -*-

from lib.math_utils import *
from lib.processing_utils import *
import numpy as np
import os
from PIL import Image, ImageDraw, ImageFilter
from pprint import pprint
import sys

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

def fillImage(img, w, h, resampleType="default", anchorX=0.5, anchorY=0.5):
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
        x = roundInt((newW - w) * anchorX)
    else:
        y = roundInt((newH - h) * anchorY)
    x1 = x + w
    y1 = y + h
    cropped = resized.crop((x, y, x1, y1))

    return cropped

def pasteImage(im, clipImg, x, y):
    width, height = im.size
    # create a staging image at the same size of the base image, so we can blend properly
    stagingImg = Image.new(mode="RGBA", size=(width, height), color=(0, 0, 0, 0))
    stagingImg.paste(clipImg, (roundInt(x), roundInt(y)))
    im = Image.alpha_composite(im, stagingImg)
    return im

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

def rotateImage(im, angle, expand=False):
    if abs(angle) > 0.0:
        im = im.rotate(360.0-angle, expand=expand, resample=Image.BICUBIC, fillcolor=(0,0,0,0))
    return im

def rotatePixels(pixels, angle, resize=None):
    im = Image.fromarray(pixels, mode="RGB")
    im = im.convert("RGBA")
    if resize is not None:
        cw, ch = resize
        im = resizeCanvas(im, cw, ch)
    im = rotateImage(im, angle)
    return np.array(im)

def saveBlankFrame(fn, width, height, bgColor="#000000", overwrite=False, verbose=True):
    if os.path.isfile(fn) and not overwrite:
        print("%s already exists." % fn)
        return
    im = Image.new('RGB', (width, height), bgColor)
    im.save(fn)
    if verbose:
        print("Saved %s" % fn)

def toEightBit(filename, toFilename):
    im = Image.open(filename)

    # PIL complains if you don't load explicitly
    im.load()

    # Get the alpha band
    alpha = im.split()[-1]

    # convert to RGB, then to 8-bit color
    im = im.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255)

    # Set all pixel values below 128 to 255, and the rest to 0
    mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)

    # Paste the color of index 255 and use alpha as a mask
    im.paste(255, mask)

    # The transparency index is 255
    im.save(toFilename, transparency=255)

def updateAlpha(im, alpha):
    im = im.convert("RGBA")
    im.putalpha(alpha)
    return im

def validateImages(filenames):
    print("Validating images...")
    validFilenames = []
    for fn in filenames:
        w = 0
        h = 0
        try:
            im = Image.open(fn)
            w, h = im.size
        except IOError:
            w = 0
            h = 0
        if w > 0 and h > 0:
            validFilenames.append(fn)
    print("Done.")
    return validFilenames
