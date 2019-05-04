# -*- coding: utf-8 -*-

import argparse
from pprint import pprint
import sys

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
