# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import os
from pprint import pprint
from sklearn.cluster import KMeans
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples_tsne.csv", help="Input file")
parser.add_argument('-props', dest="PROPS", default="tsne,tsne2", help="X and Y properties")
parser.add_argument('-sort', dest="SORT", default="flatness=desc=0.5&power=desc", help="Query string to sort by")
parser.add_argument('-lim', dest="LIMIT", default=-1, type=int, help="Target total sample count, -1 for everything")
parser.add_argument('-clusters', dest="CLUSTERS", default=8, type=int, help="Number of clusters?")
parser.add_argument('-plot', dest="PLOT", default=0, type=int, help="Plot the result?")
parser.add_argument('-write', dest="WRITE_TO_FILE", default=0, type=int, help="Write the result to file?")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
PROP1, PROP2 = tuple([p for p in args.PROPS.strip().split(",")])
SORT = args.SORT
LIMIT = args.LIMIT
CLUSTERS = args.CLUSTERS
PLOT = args.PLOT > 0
WRITE_TO_FILE = args.WRITE_TO_FILE > 0

# Read files
fieldNames, samples = readCsv(INPUT_FILE)
sCount = len(samples)
print("Found %s samples" % sCount)

# Sort and limit
if LIMIT > 0 and len(samples) > LIMIT:
    samples = sortByQueryString(samples, SORT)
    samples = samples[:LIMIT]

print("Performing k-means clustering...")
xy = np.array([(s[PROP1], s[PROP2]) for s in samples])
kmeans = KMeans(n_clusters=CLUSTERS)
kmeans.fit(xy)
y_kmeans = kmeans.predict(xy)
print("Done.")

# Add cluster back to samples
for i, s in enumerate(samples):
    samples[i]["cluster"] = y_kmeans[i]

# Write to file
if WRITE_TO_FILE:
    if "cluster" not in set(fieldNames):
        fieldNames.append("cluster")
    writeCsv(INPUT_FILE, samples, headings=fieldNames)

# Plot result
if PLOT:
    from matplotlib import pyplot as plt
    plt.figure(figsize = (10,10))
    plt.scatter(xy[:, 0], xy[:, 1], c=y_kmeans, s=10, cmap='viridis')
    centers = kmeans.cluster_centers_
    plt.scatter(centers[:, 0], centers[:, 1], c='black', s=40, alpha=0.5)
    plt.show()
