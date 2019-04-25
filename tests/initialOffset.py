# -*- coding: utf-8 -*-

import argparse
import inspect
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.composition_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
aa["OUTPUT_FILE"] = "output/ia_fedflixnara_05_shuffle.mp4"

offset = getInitialOffset(a)
print(offset)
