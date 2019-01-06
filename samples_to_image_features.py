# -*- coding: utf-8 -*-

# python3 samples_to_image_features.py -in "tmp/ia_politicaladarchive_samples.csv" -dir "E:/landscapes/downloads/ia_politicaladarchive/" -out "tmp/ia_politicaladarchive_image_features.p"

import argparse
import keras
from keras.applications.imagenet_utils import preprocess_input
from keras.models import Model
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from moviepy.editor import VideoFileClip
import numpy as np
import pickle
from PIL import Image
from sklearn.decomposition import PCA

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/sample/", help="Input file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/samples_image_features.p", help="CSV output file")
a = parser.parse_args()

# Read files
fieldNames, samples = readCsv(a.INPUT_FILE, encoding=False)
sampleCount = len(samples)
samples = addIndices(samples)

# load videos
filenames = list(set([s["filename"] for s in samples]))
fileCount = len(filenames)

model = keras.applications.VGG16(weights='imagenet', include_top=True)
feat_extractor = Model(inputs=model.input, outputs=model.get_layer("fc2").output)

print("Extracting features from each clip...")
features = []
indices = []
for i, fn in enumerate(filenames):
    filePath = a.MEDIA_DIRECTORY + fn
    video = VideoFileClip(filePath, audio=False)
    vsamples = [s for s in samples if fn==s["filename"]]

    # extract frames from videos
    for s in vsamples:
        # sample from middle of clip
        t = (s["start"] + roundInt(s["dur"] * 0.5)) / 1000.0
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

print("Reducing features with PCA...")
features = np.array(features)
pca = PCA(n_components=300)
pca.fit(features)
pca_features = pca.transform(features)

print("Writing data to file")
filenames = [samples[i]["filename"] for i in indices]
pickle.dump([filenames, pca_features], open(a.OUTPUT_FILE, 'wb'))

print("Done.")
