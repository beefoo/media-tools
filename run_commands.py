# -*- coding: utf-8 -*-

import argparse
import os
import subprocess
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="COMMANDS_FILE", default="commands.txt", help="Input text file where each line is a command")
parser.add_argument('-exclude', dest="IGNORE_LINES_STARTING_WITH", default="#,//", help="Ignore lines starting with this comma-separated list of characters")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just print commands?")
a = parser.parse_args()

lines = []
with open(a.COMMANDS_FILE, 'r', encoding="utf8") as f:
    lines = [line.strip() for line in f]
    lines = [line for line in lines if len(line) > 0]
    if len(a.IGNORE_LINES_STARTING_WITH) > 0:
        for string in a.IGNORE_LINES_STARTING_WITH.split(","):
            lines = [line for line in lines if not line.startswith(string.strip())]

for command in lines:
    print('-------------------------------')
    print(command)
    if a.PROBE:
        continue
    finished = subprocess.check_call(command, shell=True)
