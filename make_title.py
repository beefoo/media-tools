# -*- coding: utf-8 -*-

import argparse
import os
from PIL import Image, ImageFont, ImageDraw
from pprint import pprint
import subprocess
import sys

from lib.io_utils import *
from lib.math_utils import *
from lib.text_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="titles/main.md", help="Input sample csv file")
parser.add_argument('-width', dest="WIDTH", default=1920, type=int, help="Output video width")
parser.add_argument('-height', dest="HEIGHT", default=1080, type=int, help="Output video height")
parser.add_argument('-fps', dest="FPS", default=30, type=int, help="Output video frames per second")
parser.add_argument('-duration', dest="DURATION_MS", default=5000, type=int, help="Duration of text in ms, excludes fade and padding")
parser.add_argument('-fadein', dest="FADE_IN_MS", default=500, type=int, help="Fade in of text in ms")
parser.add_argument('-fadeout', dest="FADE_OUT_MS", default=500, type=int, help="Fade out of text in ms")
parser.add_argument('-pad0', dest="PAD_START", default=2000, type=int, help="Padding at start in ms")
parser.add_argument('-pad1', dest="PAD_END", default=3000, type=int, help="Padding at end in ms")
parser.add_argument('-res', dest="RESOLUTION", default=1.0, type=float, help="Multiplies text sizes")
parser.add_argument('-fdir', dest="FONT_DIR", default="media/fonts/Open_Sans/", help="Directory of font files")
parser.add_argument('-font', dest="DEFAULT_FONT_FILE", default="OpenSans-Regular.ttf", help="Default font file")
parser.add_argument('-outframe', dest="OUTPUT_FRAME", default="tmp/titles/frame.%s.png", help="Output frames pattern")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/title_main.mp4", help="Output media file")

# text properties
# font is "default" or font file name, size in points, margin as a percent of text height, line height as a percent of text height, letter width as a percent of text width
parser.add_argument('-h1', dest="H1_PROPS", default="OpenSans-Italic.ttf,128,0.3,1,1.1", help="Heading 1 (font, size, margin, line-height, letter-width)")
parser.add_argument('-h2', dest="H2_PROPS", default="default,60,0.2,1.2,1.2", help="Heading 2 (font, size, margin, line-height, letter-width)")
parser.add_argument('-h3', dest="H3_PROPS", default="default,36,0.2,1.5,1.2", help="Heading 3 (font, size, margin, line-height, letter-width)")
parser.add_argument('-pg', dest="P_PROPS", default="default,24,0.2,1.5,1", help="Paragraph (font, size, margin, line-height, letter-width)")
parser.add_argument('-align', dest="TEXT_ALIGN", default="center", help="Paragraph size in pts")
parser.add_argument('-tyoffset', dest="TEXTBLOCK_Y_OFFSET", default=-0.02, type=float, help="Vertical offset of text as a percentage of frame height; otherwise will be vertically centered")
parser.add_argument('-txoffset', dest="TEXTBLOCK_X_OFFSET", default=0.0, type=float, help="Horizontal offset of text as a percentage of frame width; otherwise will be horizontally centered")
parser.add_argument('-color', dest="TEXT_COLOR", default="#ffffff", help="Color of font")
parser.add_argument('-bg', dest="BG_COLOR", default="#000000", help="Color of font")
a = parser.parse_args()

# parse properties
H1_FONT, H1_SIZE, H1_MARGIN, H1_LH, H1_LW = tuple([parseNumber(v) for v in a.H1_PROPS.strip().split(",")])
H2_FONT, H2_SIZE, H2_MARGIN, H2_LH, H2_LW = tuple([parseNumber(v) for v in a.H2_PROPS.strip().split(",")])
H3_FONT, H3_SIZE, H3_MARGIN, H3_LH, H3_LW = tuple([parseNumber(v) for v in a.H3_PROPS.strip().split(",")])
P_FONT, P_SIZE, P_MARGIN, P_LH, P_LW = tuple([parseNumber(v) for v in a.P_PROPS.strip().split(",")])
H1_FONT = a.FONT_DIR + a.DEFAULT_FONT_FILE if H1_FONT=="default" else a.FONT_DIR + H1_FONT
H2_FONT = a.FONT_DIR + a.DEFAULT_FONT_FILE if H2_FONT=="default" else a.FONT_DIR + H2_FONT
H3_FONT = a.FONT_DIR + a.DEFAULT_FONT_FILE if H3_FONT=="default" else a.FONT_DIR + H3_FONT
P_FONT = a.FONT_DIR + a.DEFAULT_FONT_FILE if P_FONT=="default" else a.FONT_DIR + P_FONT
TEXTBLOCK_Y_OFFSET = roundInt(a.HEIGHT * a.TEXTBLOCK_Y_OFFSET)
TEXTBLOCK_X_OFFSET = roundInt(a.WIDTH * a.TEXTBLOCK_X_OFFSET)

# make dirs
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE])

# load fonts
h1Font = ImageFont.truetype(font=H1_FONT, size=roundInt(H1_SIZE*a.RESOLUTION), layout_engine=ImageFont.LAYOUT_RAQM)
h2Font = ImageFont.truetype(font=H2_FONT, size=roundInt(H2_SIZE*a.RESOLUTION), layout_engine=ImageFont.LAYOUT_RAQM)
h3Font = ImageFont.truetype(font=H3_FONT, size=roundInt(H3_SIZE*a.RESOLUTION), layout_engine=ImageFont.LAYOUT_RAQM)
pFont = ImageFont.truetype(font=P_FONT, size=roundInt(P_SIZE*a.RESOLUTION), layout_engine=ImageFont.LAYOUT_RAQM)
tprops = {
    "h1": {"font": h1Font, "margin": H1_MARGIN, "lineHeight": H1_LH, "letterWidth": H1_LW},
    "h2": {"font": h2Font, "margin": H2_MARGIN, "lineHeight": H2_LH, "letterWidth": H2_LW},
    "h3": {"font": h3Font, "margin": H3_MARGIN, "lineHeight": H3_LH, "letterWidth": H3_LW},
    "p": {"font": pFont, "margin": P_MARGIN, "lineHeight": P_LH, "letterWidth": P_LW}
}

# Read text
lines = parseMdFile(a.INPUT_FILE)

linesToImage(lines, a.OUTPUT_FRAME % "test", tprops, a.WIDTH, a.HEIGHT,
                color=a.TEXT_COLOR,
                bgColor=a.BG_COLOR,
                talign=a.TEXT_ALIGN,
                tblockYOffset=TEXTBLOCK_Y_OFFSET,
                tblockXOffset=TEXTBLOCK_X_OFFSET)

totalMs = a.PAD_START + a.FADE_IN_MS + a.DURATION_MS + a.FADE_OUT_MS + a.PAD_END
print("Total time: %s" % formatSeconds(totalMs/1000.0))
