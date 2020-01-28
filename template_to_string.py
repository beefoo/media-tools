# -*- coding: utf-8 -*-

import argparse
import os
import sys

from lib.collection_utils import *
from lib.io_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="TEMPLATE_FILE", default="command_template.txt", help="Input template file")
parser.add_argument('-query', dest="QUERY", default="key=value&key2=value2", help="Query string")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="Output file")
a = parser.parse_args()

fileContents = ""
with open(a.TEMPLATE_FILE, 'r') as f:
    fileContents = f.read()

params = parseQueryString(a.QUERY)

outString = fileContents.format(**params)

if len(a.OUTPUT_FILE) < 1:
    print("==================\n")
    print(outString)
    print("==================")

else:
    with open(a.OUTPUT_FILE, "w") as f:
        f.write(outString)
    print("Wrote commands to: %s" % a.OUTPUT_FILE)
