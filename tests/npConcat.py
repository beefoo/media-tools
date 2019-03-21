import numpy as np
from pprint import pprint

arr = np.zeros((2, 4, 3))

arr[0,:,:] = np.array([1,2,3])
arr[1,:,:] = np.array([4,5,6])
pprint(arr)

fillVals = np.full((2, 4, 1), 255)
arr = np.concatenate((arr, fillVals), axis=2)
pprint(arr)
