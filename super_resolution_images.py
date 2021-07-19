# -*- coding: utf-8 -*-

# Requires https://github.com/idealo/image-super-resolution

import argparse
from ISR.models import RDN, RRDN
import numpy as np
import os
from PIL import Image
import sys

from lib.io_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="media/small_images/*.jpg", help="Input file pattern")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/large_images/%s.png", help="Output file pattern")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing images?")
a = parser.parse_args()

files = getFilenames(a.INPUT_FILE)
makeDirectories(a.OUTPUT_FILE)

# model = RDN(weights='noise-cancel')
model = RRDN(weights='gans')
# model = RDN(weights='psnr-small')
# model = RDN(weights='psnr-large')

for fn in files:
    basename = getBasename(fn)
    filenameOut = a.OUTPUT_FILE % basename

    if not a.OVERWRITE and os.path.isfile(filenameOut):
        print(f'Already created {filenameOut}')
        continue

    img = Image.open(fn)
    sr_img = model.predict(np.array(img), by_patch_of_size=50)
    newImg = Image.fromarray(sr_img)

    newImg.save(filenameOut)
    print(f'Saved {filenameOut}')
print('Done.')
