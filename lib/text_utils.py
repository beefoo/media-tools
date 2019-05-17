
import numpy as np
from PIL import Image, ImageFont, ImageDraw
from pprint import pprint
from string import Formatter
from string import Template

from lib.io_utils import *
from lib.math_utils import *

def addTextArguments(parser):
    parser.add_argument('-fdir', dest="FONT_DIR", default="media/fonts/Open_Sans/", help="Directory of font files")
    parser.add_argument('-font', dest="DEFAULT_FONT_FILE", default="OpenSans-Regular.ttf", help="Default font file")
    parser.add_argument('-res', dest="RESOLUTION", default=1.0, type=float, help="Multiplies text sizes")
    # font is "default" or font file name, size in points, margin as a percent of text height, line height as a percent of text height, letter width as a percent of text width
    parser.add_argument('-h1', dest="H1_PROPS", default="OpenSans-Italic.ttf,96,0.3,1,1.3,default", help="Heading 1 (font, size, margin, line-height, letter-width, align)")
    parser.add_argument('-h2', dest="H2_PROPS", default="default,72,0.3,1.2,1.2,default", help="Heading 2 (font, size, margin, line-height, letter-width, align)")
    parser.add_argument('-h3', dest="H3_PROPS", default="default,36,0.5,1.5,1.2,default", help="Heading 3 (font, size, margin, line-height, letter-width, align)")
    parser.add_argument('-pg', dest="P_PROPS", default="default,28,0.5,1.5,1.2,default", help="Paragraph (font, size, margin, line-height, letter-width, align)")
    parser.add_argument('-li', dest="LI_PROPS", default="default,28,0.5,1.5,1.2,default", help="List item (font, size, margin, line-height, letter-width, align)")
    parser.add_argument('-align', dest="TEXT_ALIGN", default="center", help="Default text align")
    parser.add_argument('-tyoffset', dest="TEXTBLOCK_Y_OFFSET", default=-0.02, type=float, help="Vertical offset of text as a percentage of frame height; otherwise will be vertically centered")
    parser.add_argument('-txoffset', dest="TEXTBLOCK_X_OFFSET", default=0.0, type=float, help="Horizontal offset of text as a percentage of frame width; otherwise will be horizontally centered")
    parser.add_argument('-color', dest="TEXT_COLOR", default="#FFFFFF", help="Color of font")
    parser.add_argument('-bg', dest="BG_COLOR", default="#000000", help="Color of background")
    parser.add_argument('-maxw', dest="MAX_TEXT_WIDTH", default=0.8, type=float, help="Max text width as a percentage of frame width")
    parser.add_argument('-indent', dest="TEXT_INDENT", default=0.05, type=float, help="Amount to indent text as a percent of frame width")

def addTextMeasurements(lines, tprops, a):
    prevType = None
    lineCount = len(lines)
    parsedLines = []

    for i, line in enumerate(lines):
        type = line["type"]

        # update lines
        line.update(tprops[type])

        # assume if same type as previous, don't put margin between them
        if i > 0 and type == prevType:
            parsedLines[-1]["marginValue"] = 0

        multilines = getMultilines(line, a.MAX_TEXT_WIDTH, a.TEXT_INDENT)

        # last line has no margin
        if i >= (lineCount-1):
            multilines[-1]["marginValue"] = 0

        parsedLines += multilines
        prevType = type

    return parsedLines

def getBBoxFromLines(lines):
    width = max([l["width"] for l in lines])
    height = sum([l["lineHeightValue"]+l["margin"] for l in lines])
    return (width, height)

def getCreditLines(line, a, uniqueKey="title", lineType="li", sortBy="text"):
    lines = []
    # Line string looks like: ={title};sampledata=ia_fedflixnara_samples.csv&metadata=ia_fedflixnara.csv
    line = line[1:].strip()
    template, queryStr = tuple(line.split(";"))
    query = dict([tuple(c.split("=")) for c in queryStr.split("&")])
    sampleData = None if "sampledata" not in query else a.SAMPLE_DATA_DIR + query["sampledata"]
    metadata = None if "metadata" not in query else a.METADATA_DIR + query["metadata"]

    if metadata is None:
        print("Metadata not found in credit line; skipping")
        return lines

    # pprint(list(Formatter().parse(template)))
    keys = [ele[1] for ele in Formatter().parse(template) if ele[1]]

    if len(keys) < 1:
        print("No keys found in template; skipping")
        return lines

    samples = None
    if sampleData is not None:
        _, samples = readCsv(sampleData)
    _, meta = readCsv(metadata)

    ufilenames = set([s["filename"] for s in samples]) if samples is not None else set([d["filename"] for d in meta])

    # filter out meta that isn't in sampledata
    meta = [d for d in meta if d["filename"] in ufilenames]

    # make unique based on title (by default)
    meta = list({d[uniqueKey]:d for d in meta}.values())

    tmpl = Template(template)
    for d in meta:
        fvalues = dict([(key, normalizeText(d[key])) for key in keys])
        text = tmpl.substitute(fvalues)
        lines.append({
            "type": lineType,
            "text": text
        })

    if sortBy:
        lines = sorted(lines, key=lambda l: l[sortBy])

    return lines

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

def getMultilines(line, maxWidth, textIndent):
    mlines = [line]
    lw, lh, letterSpacing = getLineSize(line["font"], line["text"], line["letterWidth"])

    # for paragraphs and line items, wrap into multiline with text indent
    if line["type"] in set(["p", "li"]) and maxWidth > 1 and lw > maxWidth:
        mlines = []
        font = line["font"]
        text = line["text"]
        words = text.split(" ")
        mlw = 0
        index0 = 0
        sw, sh = font.getsize(" ")
        currentLineText = ""
        wordCount = len(words)
        for i, word in enumerate(words):
            ww, wh = font.getsize(word)
            testW = mlw + ww if mlw <= 0 else mlw + ww + sw
            if testW > maxWidth:
                mline = line.copy()
                if len(currentLineText) > 0:
                    mline["text"] = currentLineText
                    currentLineText = word
                    mlw = ww
                # Word is too long... just add it
                else:
                    mline["text"] = word
                tw, th = font.getsize(mline["text"])
                mline["width"] = tw
                mlines.append(mline)
            else:
                mlw = testW
                currentLineText += " " + word
            if i >= wordCount-1 and len(currentLineText) > 0:
                mline = line.copy()
                mline["text"] = currentLineText
                tw, th = font.getsize(mline["text"])
                mline["width"] = tw
                mlines.append(mline)

    margin = lh * line["margin"]
    lineHeight = lh * line["lineHeight"]
    mlineCount = len(mlines)
    for i, mline in enumerate(mlines):
        mlines[i]["width"] = lw if "width" not in mline else mline["width"]
        mlines[i]["height"] = lh
        mlines[i]["marginValue"] = 0 if i < mlineCount-1 else margin # only add margin to last line
        mlines[i]["lineHeightValue"] = lineHeight
        mlines[i]["letterSpacing"] = letterSpacing
        mlines[i]["indent"] = 0 if "indent" not in mline else mline["indent"]

    return mlines

def getTextProperty(a, prop):
    fontName, size, margin, lineHeight, letterWidth, align = tuple([parseNumber(v) for v in prop.strip().split(",")])
    fontName = a.FONT_DIR + a.DEFAULT_FONT_FILE if fontName=="default" else a.FONT_DIR + fontName
    align = a.TEXT_ALIGN if align=="default" else align
    font = ImageFont.truetype(font=fontName, size=roundInt(size*a.RESOLUTION), layout_engine=ImageFont.LAYOUT_RAQM)
    return {"font": font, "margin": margin, "lineHeight": lineHeight, "letterWidth": letterWidth, "align": align}

def getTextProperties(a):
    return {
        "h1": getTextProperty(a, a.H1_PROPS),
        "h2": getTextProperty(a, a.H2_PROPS),
        "h3": getTextProperty(a, a.H3_PROPS),
        "p": getTextProperty(a, a.P_PROPS),
        "li": getTextProperty(a, a.LI_PROPS)
    }

def linesToImage(lines, fn, tprops, width, height, color="#ffffff", bgColor="#000000", tblockYOffset=0, tblockXOffset=0, x="auto", y="auto"):
    tw, th = getBBoxFromLines(lines)

    if x=="auto":
        x = (width - tw) * 0.5 + tblockXOffset
    if y=="auto":
        y = (height - th) * 0.5 + tblockYOffset

    im = Image.new('RGB', (width, height), bgColor)
    draw = ImageDraw.Draw(im)

    ty = y
    for line in lines:
        lfont = line["font"]
        talign = line["align"]
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

def parseMdFile(fn, a, includeBlankLines=False):
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
        elif line.startswith("-"):
            type = "li"
            line = line[1:].strip()

        if line.startswith("="):
            creditLines = getCreditLines(line, a)
            parsedLines += creditLines

        elif includeBlankLines or len(line) > 0:
            parsedLines.append({
                "type": type,
                "text": line
            })
    return parsedLines

def normalizeText(text):

    if text.isupper():
        text = text.title()

    return text
