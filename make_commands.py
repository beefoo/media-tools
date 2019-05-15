# -*- coding: utf-8 -*-

import argparse
import os
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="TEMPLATE_FILE", default="command_template.txt", help="Input template file")
parser.add_argument('-query', dest="QUERY", default="collection:(FedFlix) AND mediatype:(movies) AND creator:(national archives and records administration)", help="Search query for downloading assets from Internet Archive")
parser.add_argument('-uid', dest="UNIQUE_ID", default="ia_fedflixnara", help="Unique identifier")
parser.add_argument('-ddir', dest="DOWNLOAD_DIR", default="D:/landscapes/downloads/", help="Media download directory")
parser.add_argument('-sdir', dest="SHARED_DIR", default="E:/Dropbox/landscapes/", help="For sample data to be saved and synced")
parser.add_argument('-tdir', dest="TEMP_DIR", default="tmp/", help="Directory for temporary files")
parser.add_argument('-odir', dest="OUTPUT_DIR", default="output/", help="Output directory")
a = parser.parse_args()

replacers = {
    "uid": a.UNIQUE_ID,
    "query": a.QUERY,
    "downloadDir": a.DOWNLOAD_DIR,
    "sharedDir": a.SHARED_DIR,
    "tempDir": a.TEMP_DIR,
    "outputDir": a.OUTPUT_DIR
}

fileContents = ""
with open(a.TEMPLATE_FILE, 'r') as f:
    fileContents = f.read()

for key in replacers:
    findValue = "{"+key+"}"
    replaceValue = replacers[key]
    fileContents = fileContents.replace(findValue, replaceValue)

print("==================\n")
print(fileContents)
print("==================")
