# -*- coding: utf-8 -*-

import argparse
import inspect
import os
from PIL import Image, ImageDraw
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *
from lib.math_utils import *
from lib.text_utils import *

# input
parser = argparse.ArgumentParser()
addTextArguments(parser)
a = parser.parse_args()

tprops = getTextProperties(a)
_, lineHeight, _ = getLineSize(tprops['h3']['font'], 'A')

baseImage = Image.open('tmp/nara_poster.png')

def drawFrame(filename, baseImage, text, textAlpha):
    global lineHeight

    lines = addTextMeasurements([{
        "type": 'h3',
        "text": text
    }], tprops)
    width, height = baseImage.size
    x = roundInt(width * 0.05)
    y = height - x - lineHeight
    c = roundInt(textAlpha * 255.0)
    baseImage = linesToImage(lines, filename, width, height, color="#ffffff", bgColor="#000000", x=x, y=y, bgImage=baseImage, alpha=textAlpha, overwrite=True)

makeDirectories(['output/textAlphaTest/'])

for i in range(10):
    drawFrame("output/textAlphaTest/frame%s.png" % zeroPad(i+1, 10), baseImage, 'The National Archives of the United States', (i+1)/10.0)

print('Done.')
