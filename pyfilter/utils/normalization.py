import numpy as np
import torch


def _vector(w):
    """
    Normalizes a 1D array of log weights.
    :param w: The weights
    :type w: np.ndarray
    :return: Normalized weights
    :rtype: np.ndarray
    """

    reweighed = torch.exp(w - w.max())

    normalized = reweighed / reweighed.sum()
    normalized[torch.isnan(normalized)] = 0

    # ===== Remove Nans from normalized ===== #

    if normalized.sum() == 0:
        n = w.shape[0]
        normalized = torch.ones(n) / n

    return normalized


def _matrix(w):
    """
    Normalizes a 2D array of log weights along the second axis.
    :param w: The weights
    :type w: np.ndarray
    :return: Normalized weights
    :rtype: np.ndarray
    """

    reweighed = torch.exp(w - w.max(-1)[0][..., None])
    normalized = reweighed / reweighed.sum(-1)[..., None]
    normalized[torch.isnan(normalized)] = 0

    # ===== Remove Nans from normalized ===== #

    mask = normalized.sum(-1) == 0
    n = w.shape[-1]
    normalized[mask] = torch.ones(n) / n

    return normalized


def normalize(w):
    """
    Normalizes a 1D or 2D array of log weights.
    :param w: The weights
    :type w: np.ndarray
    :return: Normalized weights
    :rtype: np.ndarray
    """

    if w.dim() > 1:
        return _matrix(w)

    return _vector(w)