"""RxR trajectory metric using the VLN-CE nDTW definition."""

import math

import numpy as np
from numba import njit


@njit(cache=True)
def _dtw_distance(actual, reference):
    previous = np.full(len(reference) + 1, np.inf)
    current = np.full(len(reference) + 1, np.inf)
    previous[0] = 0.0
    for i in range(len(actual)):
        current[0] = np.inf
        for j in range(len(reference)):
            delta = actual[i] - reference[j]
            distance = math.sqrt(np.dot(delta, delta))
            current[j + 1] = distance + min(
                previous[j], previous[j + 1], current[j]
            )
        previous, current = current, previous
    return previous[len(reference)]


def normalized_dtw(actual_locations, reference_locations, success_distance=3.0):
    """Return exp(-DTW(path, reference) / (len(reference) * radius))."""
    actual = np.asarray(actual_locations, dtype=np.float64)
    reference = np.asarray(reference_locations, dtype=np.float64)
    if actual.ndim != 2 or reference.ndim != 2 or actual.shape[1] != 3 or reference.shape[1] != 3:
        raise ValueError("Both trajectories must be nonempty lists of 3D positions")
    if len(actual) == 0 or len(reference) == 0 or success_distance <= 0:
        raise ValueError("Trajectories and success distance must be nonempty and positive")
    return math.exp(-_dtw_distance(actual, reference) / (len(reference) * success_distance))
