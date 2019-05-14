# -*- coding: utf-8 -*-

import argparse
import os
import subprocess
import sys

from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/ia_fedflixnara_subset_128x128.csv", help="Input sample csv file")
parser.add_argument('-seq', dest="SEQUENCE", default="proliferation,waves,falling,orbits,shuffle,stretch,flow,splice", help="Comma separated list of compositions")
parser.add_argument('-pyv', dest="PYTHON_NAME", default="python3", help="Name of python command")
a = parser.parse_args()

SEQUENCE = a.SEQUENCE.strip().split(",")

runningTotalMs = 0
for comp in SEQUENCE:
    command = [a.PYTHON_NAME, 'compositions/%s.py' % comp, '-in', a.INPUT_FILE, '-probe']
    print(" ".join(command))
    result = subprocess.check_output(command).strip()
    lines = [line.strip() for line in result.splitlines()]
    lastLine = lines[-1].decode("utf-8")
    compMs = int(lastLine.split(":")[-1].strip())
    runningTotalMs += compMs
    print("Running total: %s (%s)" % (runningTotalMs, formatSeconds(runningTotalMs/1000.0)))
    print("------")
