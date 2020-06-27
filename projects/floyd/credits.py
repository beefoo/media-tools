# -*- coding: utf-8 -*-

import argparse
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

parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="", help="Input video csv file")
a = parser.parse_args()

# Read files
fieldNames, rows = readCsv(a.INPUT_FILE)

rows = sorted(rows, key=lambda r: r['city'])
rows = [r for r in rows if r['priority'] < 2]

for r in rows:
    print('<li><a href="%s" target="_blank">%s, %s</a> by <a href="%s" target="_blank">@%s</a></li>' % (r["url"], r["city"], r["state"], r["userUrl"], r["user"]))
