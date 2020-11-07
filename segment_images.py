# -*- coding: utf-8 -*-

import argparse
from gluoncv import model_zoo, data, utils
from matplotlib import pyplot as plt
import os
from PIL import Image
from pprint import pprint
import sys

from lib.image_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="media/*.jpg", help="Input file pattern; can be a single file or a glob string")
parser.add_argument('-out', dest="OUTPUT_DIR", default="output/segments/", help="Segment data output directory")
# parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-blur', dest="BLUR_RADIUS", default=0.0, type=float, help="Guassian blur radius, e.g. 2.0")
parser.add_argument('-thresh', dest="THRESHOLD", default=0.99, type=float, help="Only include segments with at least this score")
parser.add_argument('-validate', dest="VALIDATE", action="store_true", help="Validate images?")
parser.add_argument('-debug', dest="DEBUG", action="store_true", help="Display plot of first result?")
a = parser.parse_args()

OUTPUT_FILE = a.OUTPUT_DIR + "segments.csv"
filenames = getFilenames(a.INPUT_FILE)
# filenames = filenames[:2]

if a.VALIDATE:
    filenames = validateImages(filenames)

# Make sure output dirs exist
makeDirectories(a.OUTPUT_DIR)

net = model_zoo.get_model('mask_rcnn_resnet50_v1b_coco', pretrained=True)

xs, orig_imgs = data.transforms.presets.rcnn.load_test(filenames)
results = zip(xs, orig_imgs)
segmentRows = []
for i, result in enumerate(results):
    x, orig_img = result
    # get the original image
    originalImage = Image.fromarray(orig_img, mode="RGB")
    originalImage = originalImage.convert("RGBA")
    originalFilename = filenames[i]
    ids, scores, bboxes, masks = [xx[0].asnumpy() for xx in net(x)]

    # paint segmentation mask on images directly
    width, height = orig_img.shape[1], orig_img.shape[0]
    masks, _ = utils.viz.expand_mask(masks, bboxes, (width, height), scores, thresh=a.THRESHOLD)
    orig_img = utils.viz.plot_mask(orig_img, masks)

    # pprint(ids.shape)
    # pprint(scores.shape)
    # pprint(bboxes.shape)
    # pprint(masks.shape)

    validCount, mHeight, mWidth = masks.shape
    if validCount < 1:
        print("No valid segments for %s" % originalFilename)
        continue
    else:
        print("Found %s segments for %s" % (validCount, originalFilename))

    for j in range(validCount):
        label = net.classes[int(ids[j, 0])]
        score = scores[j, 0]
        x0, y0, x1, y1 = tuple(bboxes[j].tolist())
        print(" - Found %s: %s" % (label, score))
        y0 = max(0, floorInt(y0))
        x0 = max(0, floorInt(x0))
        y1 = min(mHeight-1, ceilInt(y1))
        x1 = min(mWidth-1, ceilInt(x1))
        segmentW = x1 - x0
        segmentH = y1 - y0
        if segmentW <= 0 or segmentH <= 0:
            continue
        segmentFilename = getBasename(originalFilename) + "_" + str(j).zfill(3) + "_" + label + ".png"
        segmentFilepath = a.OUTPUT_DIR + segmentFilename
        segmentRows.append({
            "sourceFilename": os.path.basename(originalFilename),
            "filename": segmentFilename,
            "label": label,
            "score": score,
            "x": x0,
            "y": y0,
            "width": segmentW,
            "height": segmentH
        })
        # make the mask
        mask = masks[j] * 255
        maskImage = Image.fromarray(mask, mode="L")
        if a.BLUR_RADIUS > 0:
            maskImage = blurImage(maskImage, radius=a.BLUR_RADIUS)
        maskedImage = alphaMask(originalImage, maskImage)
        maskedImage = maskedImage.crop((x0, y0, x1, y1))
        maskedImage.save(segmentFilepath)

    if a.DEBUG:
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(1, 1, 1)
        ax = utils.viz.plot_bbox(orig_img, bboxes, scores, ids,
                                 class_names=net.classes, ax=ax)
        plt.show()
        break

writeCsv(OUTPUT_FILE, segmentRows)
