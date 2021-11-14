# -*- coding: utf-8 -*-

import argparse
import inspect
import os
from pprint import pprint
import sys

from lib.color_utils import *
from lib.math_utils import *


# input
parser = argparse.ArgumentParser()
parser.add_argument('-name', dest="GRADIENT_NAME", default="magma", help="Color gradient name")
parser.add_argument('-to', dest="CONVERT_TO", default="rgb255", help="rgb255, hexstring, hex")
a = parser.parse_args()

arr = getColorGradient(name="magma", multiply=255, toInt=True)
string = ""

if a.CONVERT_TO == "rgb255":
    for item in arr:
        string += f"'rgb({item[0]},{item[1]},{item[2]})', "

elif a.CONVERT_TO == "hexstring":
    for item in arr:
        hexString = rgbToHex(item, prefix="#")
        string += f"'{hexString}', "

else:
    for item in arr:
        hex = rgbToHex(item, prefix="0x")
        string += f"{hex}, "


print(string)
