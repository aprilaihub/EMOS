"""Poisson Newton update matching MATLAB ``poisson2d.m``."""

from __future__ import annotations

import numpy as np
from scipy.sparse.linalg import spsolve

try:
    from .findij import findij
except ImportError:  # Allows direct script-style imports.
    from findij import findij


def poisson2d(
    q: float,
    kbT: float,
    Nx: int,
    Ny: int,
    A,
    bd: np.ndarray,
    Ec: np.ndarray,
    Efn: np.ndarray,
    Efp: np.ndarray,
    Eg: np.ndarray,
    Nc: np.ndarray,
    Nv: np.ndarray,
    NB: np.ndarray,
):
    LHS = A.copy().tolil()
    RHS = bd.copy()
    EcR = Ec.T.reshape(Nx * Ny, order="F")
    Ev = Ec - Eg
    n = Nc * np.exp((Efn - Ec) / kbT)
    p = Nv * np.exp((Ev - Efp) / kbT)

    for i in range(Nx):
        for j in range(Ny):
            m = findij(i + 1, j + 1, Nx, Ny)
            if m > 0:
                idx = m - 1
                RHS[idx] = RHS[idx] - q * q * (n[i, j] - p[i, j] - NB[i, j])
                LHS[idx, idx] = LHS[idx, idx] - q * q / kbT * (n[i, j] + p[i, j])

    RHS = RHS - A.dot(EcR)
    delta = np.real(spsolve(LHS.tocsc(), RHS))
    EcR = EcR + delta
    error = np.max(np.abs(delta)) / q
    Ec = EcR.reshape((Ny, Nx), order="F").T
    return Ec, error
