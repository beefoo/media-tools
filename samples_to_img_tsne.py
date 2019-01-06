# -*- coding: utf-8 -*-

# python3 samples_to_image_features.py -in "tmp/ia_politicaladarchive_samples.csv" -dir "E:/landscapes/downloads/ia_politicaladarchive/" -out "tmp/ia_politicaladarchive_samples.csv"

# Adapted from:
# https://github.com/ml4a/ml4a-guides/blob/master/notebooks/image-search.ipynb
# https://github.com/ml4a/ml4a-guides/blob/master/notebooks/image-tsne.ipynb

import argparse
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from moviepy.editor import VideoFileClip
import numpy as np
import os
import pickle
from PIL import Image
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/sample/", help="Input file")
parser.add_argument('-cf', dest="CACHE_FILE", default="tmp/tmp_features.p", help="Pickle cache file")
parser.add_argument('-components', dest="COMPONENTS", default=2, type=int, help="Number of components (1, 2, or 3)")
parser.add_argument('-rate', dest="LEARNING_RATE", default=150, type=int, help="Learning rate: increase if too dense, decrease if too uniform")
parser.add_argument('-angle', dest="ANGLE", default=0.2, type=float, help="Angle: increase to make faster, decrease to make more accurate")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/samples.csv", help="CSV output file")
a = parser.parse_args()

PCA_COMPONENTS = 300
DO_CACHE = len(a.CACHE_FILE) > 0
PCA_CACHE_FILE = a.CACHE_FILE.replace(".p", "_pca.p")
DIMS = ["img_tsne", "img_tsne2", "img_tsne3"]
FEATURES_TO_ADD = DIMS[:a.COMPONENTS]
PRECISION = 5

features = []
pca_features = []
indices = []

# Read files
fieldNames, samples = readCsv(a.INPUT_FILE, encoding=False)
sampleCount = len(samples)
samples = addIndices(samples)

# Already did PCA features, just load that
if DO_CACHE and os.path.isfile(PCA_CACHE_FILE):
    indices, pca_features = pickle.load(open(PCA_CACHE_FILE, 'rb'))
    print("Loaded %s PCA features" % len(indices))

# Otherwise, extract features
else:
    import keras
    from keras.applications.imagenet_utils import preprocess_input
    from keras.models import Model

    # load videos
    filenames = list(set([s["filename"] for s in samples]))
    fileCount = len(filenames)

    # Load model, feature extractor
    model = keras.applications.VGG16(weights='imagenet', include_top=True)
    feat_extractor = Model(inputs=model.input, outputs=model.get_layer("fc2").output)

    if DO_CACHE and os.path.isfile(a.CACHE_FILE):
        indices, features = pickle.load(open(a.CACHE_FILE, 'rb'))
        print("Loaded %s features" % len(indices))

    print("Extracting features from each clip...")
    for i, fn in enumerate(filenames):
        vsamples = [s for s in samples if fn==s["filename"]]

        # Check if we already did these
        vindices = [s["index"] for s in vsamples]
        if containsList(indices, vindices):
            printProgress(i+1, fileCount)
            continue

        filePath = a.MEDIA_DIRECTORY + fn
        video = VideoFileClip(filePath, audio=False)
        videoDur = video.duration

        # extract frames from videos
        for s in vsamples:
            if s["index"] in set(indices):
                continue
            # sample from middle of clip
            t = (s["start"] + roundInt(s["dur"] * 0.5)) / 1000.0
            delta = videoDur - t
            if delta < 0.5:
                t = videoDur - 0.5
            try:
                videoPixels = video.get_frame(t)
            except IOError:
                print("I/O error %s at %s. Skipping..." % (fn, t))
                continue
            except OSError:
                print("OS error %s at %s. Skipping..." % (fn, t))
                continue
            x = video.get_frame(t)
            im = Image.fromarray(x, mode="RGB")
            im = im.resize((224, 224))
            x = np.array(im)
            x = np.expand_dims(x, axis=0)
            x = preprocess_input(x)
            feat = feat_extractor.predict(x)[0]
            features.append(feat)
            indices.append(s["index"])

        video.reader.close()
        del video
        printProgress(i+1, fileCount)

        if DO_CACHE:
            pickle.dump([indices, features], open(a.CACHE_FILE, 'wb'))

    print("Reducing features with PCA...")
    features = np.array(features)
    pca = PCA(n_components=PCA_COMPONENTS)
    pca.fit(features)
    pca_features = pca.transform(features)

    if DO_CACHE:
        print("Writing PCA data to file")
        pickle.dump([indices, pca_features], open(PCA_CACHE_FILE, 'wb'))

print("Doing TSNE...")
x = np.array(pca_features)
tsne = TSNE(n_components=a.COMPONENTS, learning_rate=a.LEARNING_RATE, angle=a.ANGLE, verbose=2).fit_transform(x)
# pickle.dump(tsne, open("tmp/tmp_tsne.p", 'wb'))
# tsne = pickle.load(open("tmp/tmp_tsne.p", 'rb'))

print("Writing data to file...")
headings = fieldNames[:]
modelNorm = []

for i in range(a.COMPONENTS):
    if DIMS[i] not in headings:
        headings.append(DIMS[i])
    # normalize model between 0 and 1
    if a.COMPONENTS > 1:
        values = tsne[:,i]
    else:
        values = tsne[:]
    minValue = np.min(values)
    maxValue = np.max(values)
    valuesNorm = (values - minValue) / (maxValue - minValue)
    modelNorm.append(valuesNorm)

with open(a.OUTPUT_FILE, 'w') as f:
    writer = csv.writer(f)
    writer.writerow(headings)
    for i, d in enumerate(samples):
        row = []
        for h in headings:
            if h in DIMS:
                j = DIMS.index(h)
                row.append(round(modelNorm[j][i], PRECISION))
            else:
                row.append(d[h])
        writer.writerow(row)
print("Wrote %s rows to %s" % (len(samples), a.OUTPUT_FILE))
