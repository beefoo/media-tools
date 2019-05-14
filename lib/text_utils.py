
import numpy as np
from PIL import Image, ImageFont, ImageDraw
from pprint import pprint

def getBBoxFromLines(lines):
    maxW = 0
    bboxHeight = 0
    prevType = None
    lineCount = len(lines)
    for i, line in enumerate(lines):
        type = line["type"]

        # assume if same type as previous, don't put margin between them
        if i > 0 and type == prevType:
            bboxHeight -= lines[i-1]["marginValue"]
            lines[i-1]["marginValue"] = 0

        lw, lh, letterSpacing = getLineSize(line["font"], line["text"], line["letterWidth"])
        # print("%s: %s, %s" % (line["text"], lw, lh))
        # if tblockWidth > 0:
        #     lw = min(lw, tblockWidth)
        margin = lh * line["margin"]
        # last line has no margin
        if i >= (lineCount-1):
            margin = 0
        lineHeight = lh * line["lineHeight"]
        lines[i]["width"] = lw
        lines[i]["height"] = lh
        lines[i]["marginValue"] = margin
        lines[i]["lineHeightValue"] = lineHeight
        lines[i]["letterSpacing"] = letterSpacing
        maxW = max(maxW, lw)
        bboxHeight += lineHeight + margin
        prevType = type
    return (lines, maxW, bboxHeight)

def getLineSize(font, text, letterWidth=1.0):
    lw, lh = font.getsize(text)
    letterSpacing = 0

    if letterWidth != 1.0:
        lw = 0
        chars = list(text)
        cws = []
        for char in chars:
            cw, ch = font.getsize(char)
            cws.append(cw)
        cwMean = np.mean(cws)
        cw = cwMean * letterWidth
        letterSpacing = cw - cwMean
        lw = (len(cws)-1) * cw

    return (lw, lh, letterSpacing)

def linesToImage(lines, fn, tprops, width, height, color="#ffffff", bgColor="#000000", talign="center", tblockYOffset=0, tblockXOffset=0, x="auto", y="auto"):
    # update lines
    for line in lines:
        line.update(tprops[line["type"]])
    lines, tw, th = getBBoxFromLines(lines)

    if x=="auto":
        x = (width - tw) * 0.5 + tblockXOffset
    if y=="auto":
        y = (height - th) * 0.5 + tblockYOffset

    im = Image.new('RGB', (width, height), bgColor)
    draw = ImageDraw.Draw(im)

    ty = y
    for line in lines:
        lfont = line["font"]
        tx = x
        if talign == "center":
            tx = x + (tw - line["width"]) * 0.5
        elif talign == "right":
            tx = x + (tw - line["width"])
        ls = line["letterSpacing"]
        if ls <= 0:
            draw.text((tx, ty), line["text"], font=lfont, fill=color)
        # draw char by char if we have letter width set
        else:
            chars = list(line["text"])
            for char in chars:
                draw.text((tx, ty), char, font=lfont, fill=color)
                cw, ch = lfont.getsize(char)
                tx += cw + ls
        ty += line["lineHeightValue"] + line["marginValue"]

    im.save(fn)
    print("Saved %s" % fn)

def parseMdFile(fn, includeBlankLines=False):
    lines = []
    with open(fn) as f:
        lines = f.readlines()
    lines = [l.strip() for l in lines]
    parsedLines = []
    for line in lines:
        type = "p"
        if line.startswith("###"):
            type = "h3"
            line = line[3:].strip()
        elif line.startswith("##"):
            type = "h2"
            line = line[2:].strip()
        elif line.startswith("#"):
            type = "h1"
            line = line[1:].strip()
        if includeBlankLines or len(line) > 0:
            parsedLines.append({
                "type": type,
                "text": line
            })
    return parsedLines
