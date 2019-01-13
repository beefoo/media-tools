# -*- coding: utf-8 -*-

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

def getKMeansClusters(xy, nClusters=8):
    xy = np.array(xy)
    kmeans = KMeans(n_clusters=nClusters)
    kmeans.fit(xy)
    y_kmeans = kmeans.predict(xy)
    centers = kmeans.cluster_centers_

    return y_kmeans, centers
