
import numpy as np
import os
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
    parser.add_argument('-rr', dest="RESIZE_RESOLUTION", default=1.0, type=float, help="Multiplies text sizes, then resizes back to 1.0 upon render for better text positioning")
    # font is "default" or font file name, size in points, margin as a percent of text height, line height as a percent of text height, letter width as a percent of text width
    parser.add_argument('-h1', dest="H1_PROPS", default="font=OpenSans-Italic.ttf&size=96&margin=0.3&letterWidth=1.3", help="Heading 1 (font, size, margin, line-height, letter-width, align)")
    parser.add_argument('-h2', dest="H2_PROPS", default="size=72&margin=0.3&lineHeight=1.2&letterWidth=1.2", help="Heading 2 (font, size, margin, line-height, letter-width, align)")
    parser.add_argument('-h3', dest="H3_PROPS", default="size=36&margin=0.5&lineHeight=1.5&letterWidth=1.2", help="Heading 3 (font, size, margin, line-height, letter-width, align)")
    parser.add_argument('-pg', dest="P_PROPS", default="size=28&margin=0.5&lineHeight=1.5&letterWidth=1.2", help="Paragraph (font, size, margin, line-height, letter-width, align)")
    parser.add_argument('-li', dest="LI_PROPS", default="size=14&margin=0.5&lineHeight=1.1&align=left", help="List item (font, size, margin, line-height, letter-width, align)")
    parser.add_argument('-table', dest="TABLE_PROPS", default="size=16&margin=12.0&align=left", help="List item (font, size, margin, line-height, letter-width, align)")
    parser.add_argument('-align', dest="TEXT_ALIGN", default="center", help="Default text align")
    parser.add_argument('-tyoffset', dest="TEXTBLOCK_Y_OFFSET", default=-0.02, type=float, help="Vertical offset of text as a percentage of frame height; otherwise will be vertically centered")
    parser.add_argument('-txoffset', dest="TEXTBLOCK_X_OFFSET", default=0.0, type=float, help="Horizontal offset of text as a percentage of frame width; otherwise will be horizontally centered")
    parser.add_argument('-color', dest="TEXT_COLOR", default="#FFFFFF", help="Color of font")
    parser.add_argument('-bg', dest="BG_COLOR", default="#000000", help="Color of background")
    parser.add_argument('-maxw', dest="MAX_TEXT_WIDTH", default=0.9, type=float, help="Max text width as a percentage of frame width")

def addTextMeasurements(lines, tprops, maxWidth=-1):
    prevType = None
    lineCount = len(lines)
    parsedLines = []

    for i, line in enumerate(lines):
        type = line["type"]

        if type == "table":
            multilines = getTableLines(line, tprops, maxWidth)

        else:
            # update lines
            line.update(tprops[type])

            # assume if same type as previous, don't put margin between them, except list items
            if i > 0 and type == prevType and type != "li":
                parsedLines[-1]["marginValue"] = 0

            multilines = getMultilines(line, maxWidth)

        # last line has no margin
        if i >= (lineCount-1):
            multilines[-1]["marginValue"] = 0

        parsedLines += multilines
        prevType = type

    return parsedLines

def drawLineToImage(draw, line, tx, ty, width, height, color):
    lfont = line["font"]
    ls = line["letterSpacing"]
    xmin, xmax = (-line["width"], width)
    ymin, ymax = (-line["height"], height)
    # draw text if in bounds
    if xmin <= tx <= xmax and ymin <= ty <= ymax:
        if ls <= 0:
            draw.text((tx, ty), line["text"], font=lfont, fill=color)
        # draw char by char if we have letter width set
        else:
            chars = list(line["text"])
            for char in chars:
                draw.text((tx, ty), char, font=lfont, fill=color)
                cw, ch = lfont.getsize(char)
                tx += cw + ls

def getBBoxFromLines(lines):
    width = max([l["width"] for l in lines])
    height = sum([l["lineHeightValue"]+l["marginValue"] for l in lines])
    return (width, height)

def getCreditLines(line, a, uniqueKey="title", lineType="li", sortBy="text"):
    lines = []
    # Line string looks like: ={title};sampledata=ia_fedflixnara_samples.csv&metadata=ia_fedflixnara.csv
    line = line[1:].strip()
    template, queryStr = tuple(line.split(";"))
    query = parseQueryString(queryStr, parseNumbers=False)
    sampleData = None if "sampledata" not in query else a.SAMPLE_DATA_DIR + query["sampledata"]
    metadata = None if "metadata" not in query else a.METADATA_DIR + query["metadata"]
    cols = 1 if "cols" not in query else int(query["cols"])

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

    print("Found %s credits" % len(lines))

    # if cols are more than one, break them into rows
    if cols > 1:
        lineCount = len(lines)
        rowCount = ceilInt(1.0 * lineCount / cols)
        rows = []
        for row in range(rowCount):
            i0 = row * cols
            i1 = min(i0 + cols, lineCount)
            row = lines[i0:i1]
            rows.append({
                "type": "row",
                "cols": row
            })
        lines = [{
            "type": "table",
            "rows": rows
        }]

    return lines

def getLineSize(font, text, letterWidth=1.0):
    lw, lh = font.getsize(text)
    letterSpacing = 0

    if letterWidth != 1.0:
        # normalize letter spacing with a constant char
        aw, ah = font.getsize("A")
        letterSpacing = aw * letterWidth - aw
        clen = len(text)
        if clen > 1:
            lw += letterSpacing * (clen-1)

    return (lw, lh, letterSpacing)

def getLineWidth(font, text, letterWidth=1.0):
    lw, lh, letterSpacing = getLineSize(font, text, letterWidth)
    return lw

def getMultilines(line, maxWidth):
    mlines = [line]
    lw, lh, letterSpacing = getLineSize(line["font"], line["text"], line["letterWidth"])

    # for line items, wrap into multiline
    if line["type"] == "li" and maxWidth > 1 and lw > maxWidth:
        mlines = []
        font = line["font"]
        text = line["text"]
        words = text.split()
        currentLineText = ""
        wordCount = len(words)
        for i, word in enumerate(words):
            testString = word if len(currentLineText) < 1 else currentLineText + " " + word
            testW = getLineWidth(font, testString, line["letterWidth"])
            # test string too long, must add previous line and move on to next line
            if testW > maxWidth:
                mline = line.copy()
                if len(currentLineText) > 0:
                    mline["text"] = currentLineText
                    currentLineText = word
                # Word is too long... just add it
                else:
                    mline["text"] = word
                mline["width"] = getLineWidth(font, mline["text"], line["letterWidth"])
                mlines.append(mline)
            # otherwise add to current line
            else:
                currentLineText = testString
            # leftover text at the end; just add it
            if i >= wordCount-1 and len(currentLineText) > 0:
                mline = line.copy()
                mline["text"] = currentLineText
                mline["width"] = getLineWidth(font, mline["text"], line["letterWidth"])
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

    return mlines

def getTableLines(line, tprops, maxWidth):
    rows = line["rows"]
    rowCount = len(rows)
    tableProps = tprops["table"].copy()
    colCount = len(rows[0]["cols"])

    # calculate column width with margin
    tlw, tlh, _ = getLineSize(tableProps["font"], "A")
    tableMargin = tableProps["margin"] * tlh
    colMargin = tlh
    colWidth = 1.0 * maxWidth / colCount - colMargin * (colCount-1)

    # break into cols
    cols = [[] for col in range(colCount)]
    for row in rows:
        rowCols = row["cols"]
        for col in range(colCount):
            if col < len(rowCols):
                cols[col].append(rowCols[col])

    tableH = 0
    tableW = maxWidth
    parsedCols = []
    for colRows in cols:
        parsedLines = []
        for line in colRows:
            line.update(tprops["li"])
            multilines = getMultilines(line, colWidth)
            parsedLines += multilines
        colW, colH = getBBoxFromLines(parsedLines)
        tableH = max(tableH, colH)
        parsedCols.append(parsedLines)

    tableProps.update({
        "type": "table",
        "width": tableW,
        "height": tableH,
        "lineHeightValue": tableH,
        "marginValue": tableMargin,
        "cols": parsedCols
    })
    return [tableProps]

def getTextProperty(a, prop):
    query = parseQueryString(prop)
    fontName = a.FONT_DIR + a.DEFAULT_FONT_FILE if "font" not in query else a.FONT_DIR + query["font"]
    query["align"] = a.TEXT_ALIGN if "align" not in query else query["align"]
    query["size"] = 16 if "size" not in query else query["size"]
    query["margin"] = 0.0 if "margin" not in query else query["margin"]
    query["lineHeight"] = 1.0 if "lineHeight" not in query else query["lineHeight"]
    query["letterWidth"] = 1.0 if "letterWidth" not in query else query["letterWidth"]
    # pprint(query)
    # print(fontName)
    # sys.exit()
    query["font"] = ImageFont.truetype(font=fontName, size=roundInt(query["size"]*a.RESOLUTION*a.RESIZE_RESOLUTION), layout_engine=ImageFont.LAYOUT_RAQM)
    return query

def getTextProperties(a):
    return {
        "h1": getTextProperty(a, a.H1_PROPS),
        "h2": getTextProperty(a, a.H2_PROPS),
        "h3": getTextProperty(a, a.H3_PROPS),
        "p": getTextProperty(a, a.P_PROPS),
        "li": getTextProperty(a, a.LI_PROPS),
        "table": getTextProperty(a, a.TABLE_PROPS)
    }

def linesToImage(lines, fn, width, height, color="#ffffff", bgColor="#000000", tblockYOffset=0, tblockXOffset=0, x="auto", y="auto", resizeResolution=1.0, overwrite=False, bgImage=None):
    if os.path.isfile(fn) and not overwrite:
        print("%s already exists." % fn)
        return

    tw, th = getBBoxFromLines(lines)

    if x=="auto":
        x = (width - tw) * 0.5 + tblockXOffset
    if y=="auto":
        y = (height - th) * 0.5 + tblockYOffset

    im = Image.new('RGB', (width, height), bgColor) if bgImage is None else bgImage.copy()
    draw = ImageDraw.Draw(im)

    ty = y
    for line in lines:
        talign = line["align"]
        tx = x
        if talign == "center":
            tx = x + (tw - line["width"]) * 0.5
        elif talign == "right":
            tx = x + (tw - line["width"])

        if line["type"] == "table":
            colW = 1.0 * line["width"] / len(line["cols"])
            for cindex, colRows in enumerate(line["cols"]):
                colX = tx + cindex * colW
                colY = ty
                for row in colRows:
                    drawLineToImage(draw, row, colX, colY, width, height, color)
                    colY += row["lineHeightValue"] + row["marginValue"]
        else:
            drawLineToImage(draw, line, tx, ty, width, height, color)

        ty += line["lineHeightValue"] + line["marginValue"]

    if resizeResolution > 1.0:
        rw = roundInt(1.0*width/resizeResolution)
        rh = roundInt(1.0*height/resizeResolution)
        im = im.resize((rw, rh), resample=Image.LANCZOS)

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
        elif line.startswith("_"):
            line = " "

        if line.startswith("="):
            creditLines = getCreditLines(line, a)
            parsedLines += creditLines

        elif includeBlankLines or len(line) > 0:
            parsedLines.append({
                "type": type,
                "text": line
            })
    return parsedLines

def normalizeText(text, toTitleCase=False):

    # normalize whitespace
    text = ' '.join(text.split())

    # convert all uppercase to title case
    # if text.isupper():
    #     text = text.title()
    if toTitleCase:
        text = text.title()

    return text
