"""Deterministic Lloyd iterations, with every teaching step preserved."""
from dataclasses import dataclass
import numpy as np

POINT_NAMES = list("ABCDEFGH")
DEFAULT_POINTS = [[2, 10], [2, 5], [8, 4], [5, 8], [7, 5], [6, 4], [1, 2], [4, 9]]
COLORS = ["#139778", "#6667CE", "#E99A37", "#D85C83"]


@dataclass
class Frame:
    kind: str
    iteration: int
    centers: np.ndarray
    labels: np.ndarray | None
    distances: np.ndarray | None = None
    previous_centers: np.ndarray | None = None
    inertia: float | None = None
    converged: bool = False


def validate_config(points, k, seeds):
    x = np.asarray(points, dtype=float)
    if x.shape != (8, 2) or not np.isfinite(x).all():
        raise ValueError("Provide exactly eight points with finite X and Y coordinates.")
    if np.max(np.abs(x)) > 10000:
        raise ValueError("Use coordinates between -10,000 and 10,000.")
    if len(np.unique(x, axis=0)) != 8:
        raise ValueError("Each of the eight points must have distinct coordinates.")
    if k not in (2, 3, 4) or len(seeds) != k or len(set(seeds)) != k:
        raise ValueError("Choose 2–4 clusters and one distinct starting point per cluster.")
    if any(type(i) is not int or i not in range(8) for i in seeds):
        raise ValueError("Starting centers must be selected from points A–H.")
    return x


def kmeans_steps(points, k=3, seeds=None, max_iter=100):
    seeds = seeds if seeds is not None else [0, 3, 6, 2][:k]
    x = validate_config(points, k, seeds)
    centers = x[seeds].copy()
    frames = [Frame("initialize", 0, centers.copy(), None)]
    for iteration in range(1, max_iter + 1):
        distances = np.linalg.norm(x[:, None, :] - centers[None, :, :], axis=2)
        labels = np.argmin(distances, axis=1)
        inertia = float(np.sum((x - centers[labels]) ** 2))
        frames.append(Frame("assign", iteration, centers.copy(), labels.copy(), distances, inertia=inertia))
        updated = np.array([x[labels == j].mean(axis=0) if np.any(labels == j) else centers[j] for j in range(k)])
        converged = bool(np.allclose(centers, updated, atol=1e-10, rtol=0))
        inertia = float(np.sum((x - updated[labels]) ** 2))
        frames.append(Frame("update", iteration, updated.copy(), labels.copy(),
                            previous_centers=centers.copy(), inertia=inertia, converged=converged))
        centers = updated
        if converged:
            frames.append(Frame("finish", iteration, centers.copy(), labels.copy(), inertia=inertia, converged=True))
            break
    else:
        raise RuntimeError("K-means did not converge within the iteration limit.")
    return frames
