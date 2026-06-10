"""Coupled Poisson + drift-diffusion loop matching MATLAB ``solve.m``."""

from __future__ import annotations

import numpy as np

try:
    from .driftdiff2d import driftdiff2d
    from .getA2d import getA2d
    from .poisson2d import poisson2d
except ImportError:  # Allows direct script-style imports.
    from driftdiff2d import driftdiff2d
    from getA2d import getA2d
    from poisson2d import poisson2d


def solve_device(
    q: float,
    kbT: float,
    Nx: int,
    Ny: int,
    dx: float,
    dy: float,
    NB: np.ndarray,
    EP: np.ndarray,
    Eg: np.ndarray,
    un: np.ndarray,
    up: np.ndarray,
    vsat_n: np.ndarray,
    vsat_p: np.ndarray,
    pow_n: np.ndarray,
    pow_p: np.ndarray,
    Nc: np.ndarray,
    Nv: np.ndarray,
    xi: np.ndarray,
    tch1: int,
    tch2: int,
    lch1: int,
    lch2: int,
    Ec1: float,
    Ec2: float,
    Ec3: float,
    Ec4: float,
    Ef1: float,
    Ef2: float,
    Ef3: float,
    Ef4: float,
):
    error = 1.0
    Ec = np.zeros((Nx, Ny), dtype=float)
    Efn = np.zeros((Nx, Ny), dtype=float)
    Efp = np.zeros((Nx, Ny), dtype=float)

    A, bd = getA2d(Nx, Ny, dx, dy, EP, xi, tch1, tch2, lch1, lch2, Ec1, Ec2, Ec3, Ec4)

    while error > 1e-6:
        Ec, error = poisson2d(q, kbT, Nx, Ny, A, bd, Ec, Efn, Efp, Eg, Nc, Nv, NB)
        Efn, Efp = driftdiff2d(
            kbT,
            Nx,
            Ny,
            dx,
            dy,
            Ec,
            Efn,
            Efp,
            Eg,
            un,
            up,
            vsat_n,
            vsat_p,
            pow_n,
            pow_p,
            Nc,
            Nv,
            Ef1,
            Ef2,
            Ef3,
            Ef4,
            tch1,
            tch2,
            lch1,
            lch2,
        )

    return Ec, Efn, Efp
