"""Poisson matrix assembly matching MATLAB ``getA2d.m``."""

from __future__ import annotations

import numpy as np
from scipy.sparse import lil_matrix

try:
    from .findij import findij
except ImportError:  # Allows direct script-style imports.
    from findij import findij


def getA2d(
    Nx: int,
    Ny: int,
    dx: float,
    dy: float,
    EP: np.ndarray,
    xi: np.ndarray,
    tch1: int,
    tch2: int,
    lch1: int,
    lch2: int,
    Ec1: float,
    Ec2: float,
    Ec3: float,
    Ec4: float,
):
    A = lil_matrix((Nx * Ny, Nx * Ny), dtype=float)
    bd = np.zeros(Nx * Ny, dtype=float)

    for i in range(Nx):
        for j in range(Ny):
            if i - 1 < 0:
                EPmi = EP[i, j]
                DEcmi = 0.0
            else:
                EPmi = (EP[i - 1, j] + EP[i, j]) / 2
                DEcmi = -xi[i, j] + xi[i - 1, j]

            if j - 1 < 0:
                EPmj = EP[i, j]
                DEcmj = 0.0
            else:
                EPmj = (EP[i, j - 1] + EP[i, j]) / 2
                DEcmj = -xi[i, j] + xi[i, j - 1]

            if i + 1 >= Nx:
                EPpi = EP[i, j]
                DEcpi = 0.0
            else:
                EPpi = (EP[i + 1, j] + EP[i, j]) / 2
                DEcpi = -xi[i + 1, j] + xi[i, j]

            if j + 1 >= Ny:
                EPpj = EP[i, j]
                DEcpj = 0.0
            else:
                EPpj = (EP[i, j + 1] + EP[i, j]) / 2
                DEcpj = -xi[i, j + 1] + xi[i, j]

            m = findij(i + 1, j + 1, Nx, Ny)
            if m > 0:
                idx = m - 1
                A[idx, idx] = A[idx, idx] + (-EPmi - EPpi) / dx**2 + (-EPmj - EPpj) / dy**2
                bd[idx] = bd[idx] - EPmi * DEcmi / dx**2 + EPpi * DEcpi / dx**2 - EPmj * DEcmj / dy**2 + EPpj * DEcpj / dy**2
            else:
                continue

            my = findij(i + 1, j + 2, Nx, Ny)
            if my > 0:
                A[idx, my - 1] = A[idx, my - 1] + EPpj / dy**2
            elif my == -4:
                if lch1 <= i + 1 <= lch2:
                    bd[idx] = bd[idx] - Ec4 / dy**2 * EPpj
                else:
                    A[idx, idx] = A[idx, idx] + EPpj / dy**2

            my = findij(i + 1, j, Nx, Ny)
            if my > 0:
                A[idx, my - 1] = A[idx, my - 1] + EPmj / dy**2
            elif my == -3:
                if lch1 <= i + 1 <= lch2:
                    bd[idx] = bd[idx] - Ec3 / dy**2 * EPmj
                else:
                    A[idx, idx] = A[idx, idx] + EPmj / dy**2

            my = findij(i + 2, j + 1, Nx, Ny)
            if my > 0:
                A[idx, my - 1] = A[idx, my - 1] + EPpi / dx**2
            elif my == -2:
                if tch1 <= j + 1 <= tch2:
                    bd[idx] = bd[idx] - Ec2 / dx**2 * EPpi
                else:
                    A[idx, idx] = A[idx, idx] + EPpi / dx**2

            my = findij(i, j + 1, Nx, Ny)
            if my > 0:
                A[idx, my - 1] = A[idx, my - 1] + EPmi / dx**2
            elif my == -1:
                if tch1 <= j + 1 <= tch2:
                    bd[idx] = bd[idx] - Ec1 / dx**2 * EPmi
                else:
                    A[idx, idx] = A[idx, idx] + EPmi / dx**2

    return A, bd
