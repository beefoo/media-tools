# -*- coding: utf-8 -*-

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

def addClustersToList(arr, keyX, keyY, nClusters=8, outKey="cluster"):
    xy = [(item[keyX], item[keyY]) for item in arr]
    y_kmeans, centers = getKMeansClusters(xy, nClusters)
    for i, item in enumerate(arr):
        arr[i][outKey] = y_kmeans[i]
    return arr, centers

def getKMeansClusters(xy, nClusters=8, nRuns=20, randomState=8, nJobs=1):
    xy = np.array(xy)
    kmeans = KMeans(
        n_clusters=nClusters,
        n_init=nRuns,
        random_state=randomState, # make results deterministic
        n_jobs=nJobs
    )
    kmeans.fit(xy)
    y_kmeans = kmeans.predict(xy)
    centers = kmeans.cluster_centers_

    return y_kmeans, centers
