"""Vector operations and similarity metrics."""

import numpy as np

a = np.array([1, 0, 0])
b = np.array([1, 0, 0])
c = np.array([0, 1, 0])


def cosine_similarity(x, y):
    """Calculate the cosine similarity between two vectors."""
    return np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y))


print(cosine_similarity(a, b))
print(cosine_similarity(a, c))
