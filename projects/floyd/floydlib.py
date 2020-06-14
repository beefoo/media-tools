
from bs4 import BeautifulSoup
import inspect
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

def parseLayoutFile(svgFile):
    contents = readTextFile(svgFile)
    soup = BeautifulSoup(contents, 'html.parser')
    groups = soup.find("svg").find_all("g", recursive=False)

    items = []
    for g in groups:
        if not g.has_attr("id"):
            continue

        id = g["id"]
        shapes = []

        # parse rectangles
        for rect in g.find_all("rect"):
            x = y = width = height = 0
            if rect.has_attr("x"):
                x = float(rect["x"])
            if rect.has_attr("y"):
                y = float(rect["y"])
            if rect.has_attr("width"):
                width = float(rect["width"])
            if rect.has_attr("height"):
                height = float(rect["height"])
            shapes.append({
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "x2": x+width,
                "y2": y+height
            })

        # parse polygons
        for polygon in g.find_all("polygon"):
            if not polygon.has_attr("points"):
                continue
            points = [float(p) for p in polygon["points"].split(" ")]
            points = listToTupleList(points)
            x, y, x2, y2 = bboxFromPoints(points)
            shapes.append({
                "x": x,
                "y": y,
                "width": x2-x,
                "height": y2-y,
                "x2": x2,
                "y2": y2
            })

        if len(shapes) < 1:
            continue

        if len(shapes) == 1:
            item = shapes[0]
            item["id"] = id

        else:
            x = min([s["x"] for s in shapes])
            y = min([s["y"] for s in shapes])
            x2 = max([s["x2"] for s in shapes])
            y2 = max([s["y2"] for s in shapes])
            item = {
                "id": id,
                "x": x,
                "y": y,
                "width": x2-x,
                "height": y2-y,
                "x2": x2,
                "y2": y2
            }

        items.append(item)

    return items
