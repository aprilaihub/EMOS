"""t-SNE embedding of a precomputed EMD matrix."""

from __future__ import annotations

import inspect
from dataclasses import dataclass

import numpy as np


@dataclass
class TsneResult:
    coords: np.ndarray
    perplexity: float
    kl_divergence: float


def tsne_perplexity(n: int) -> float:
    """``min(30, (N - 1) / 3)``: keeps perplexity well below the number of points."""
    return min(30.0, (n - 1) / 3.0)


def embed_tsne(emd_matrix: np.ndarray, random_state: int = 42, max_iter: int = 2000) -> TsneResult:
    """Embed a symmetric EMD matrix in 2-D.

    The input is a metric distance matrix, so the embedding is invariant to cell
    choice (unlike flattened, zero-padded PDDs).  ``init='pca'`` is not allowed with
    ``metric='precomputed'``, hence ``init='random'``.
    """
    from sklearn.manifold import TSNE

    perplexity = tsne_perplexity(len(emd_matrix))
    kwargs = dict(
        n_components=2,
        metric="precomputed",
        init="random",
        perplexity=perplexity,
        learning_rate="auto",
        random_state=random_state,
    )
    iteration_key = "max_iter" if "max_iter" in inspect.signature(TSNE.__init__).parameters else "n_iter"
    kwargs[iteration_key] = max_iter
    model = TSNE(**kwargs)
    coords = model.fit_transform(emd_matrix)
    return TsneResult(coords, perplexity, float(model.kl_divergence_))
