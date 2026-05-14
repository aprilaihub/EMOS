"""Carrier transport solve matching MATLAB ``driftdiff2d.m``."""

from __future__ import annotations

import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

try:
    from .constant import Q
    from .findij import findij
except ImportError:  # Allows direct script-style imports.
    from constant import Q
    from findij import findij


def driftdiff2d(
    kbT: float,
    Nx: int,
    Ny: int,
    dx: float,
    dy: float,
    Ec: np.ndarray,
    Efn: np.ndarray,
    Efp: np.ndarray,
    Eg: np.ndarray,
    un: np.ndarray,
    up: np.ndarray,
    vsat_n: np.ndarray,
    vsat_p: np.ndarray,
    pow_n: np.ndarray,
    pow_p: np.ndarray,
    Nc: np.ndarray,
    Nv: np.ndarray,
    Ef1: float,
    Ef2: float,
    Ef3: float,
    Ef4: float,
    tch1: int,
    tch2: int,
    lch1: int,
    lch2: int,
):
    q = Q
    nLHS = lil_matrix((Nx * Ny, Nx * Ny), dtype=float)
    nRHS = np.zeros(Nx * Ny, dtype=float)
    pLHS = lil_matrix((Nx * Ny, Nx * Ny), dtype=float)
    pRHS = np.zeros(Nx * Ny, dtype=float)
    Ev = Ec - Eg

    for i in range(Nx):
        for j in range(Ny):
            if i - 1 < 0:
                Ncmi = Nc[0, j]
                unmi = un[0, j] / (1 + (np.abs(Ec[0, j] - Ec[1, j]) / dx * un[0, j] / q / vsat_n[0, j]) ** pow_n[0, j]) ** (1 / pow_n[0, j])
                Ecmi = Ec[0, j]
                Nvmi = Nv[0, j]
                upmi = up[0, j] / (1 + (np.abs(Ec[0, j] - Ec[1, j]) / dx * up[0, j] / q / vsat_p[0, j]) ** pow_p[0, j]) ** (1 / pow_p[0, j])
                Evmi = Ev[0, j]
            else:
                Ncmi = (Nc[i - 1, j] + Nc[i, j]) / 2
                unmi = (un[i - 1, j] + un[i, j]) / 2
                unmi = unmi / (1 + (np.abs(Ec[i - 1, j] - Ec[i, j]) / dx * unmi / q / vsat_n[i, j]) ** pow_n[i, j]) ** (1 / pow_n[i, j])
                Ecmi = (Ec[i - 1, j] + Ec[i, j]) / 2
                Nvmi = (Nv[i - 1, j] + Nv[i, j]) / 2
                upmi = (up[i - 1, j] + up[i, j]) / 2
                upmi = upmi / (1 + (np.abs(Ec[i - 1, j] - Ec[i, j]) / dx * upmi / q / vsat_p[i, j]) ** pow_p[i, j]) ** (1 / pow_p[i, j])
                Evmi = (Ev[i - 1, j] + Ev[i, j]) / 2

            if i + 1 >= Nx:
                Ncpi = Nc[Nx - 1, j]
                unpi = un[Nx - 1, j] / (1 + (np.abs(Ec[Nx - 2, j] - Ec[Nx - 1, j]) / dx * un[Nx - 1, j] / q / vsat_n[Nx - 1, j]) ** pow_n[Nx - 1, j]) ** (1 / pow_n[Nx - 1, j])
                Ecpi = Ec[Nx - 1, j]
                Nvpi = Nv[Nx - 1, j]
                uppi = up[Nx - 1, j] / (1 + (np.abs(Ec[Nx - 2, j] - Ec[Nx - 1, j]) / dx * up[Nx - 1, j] / q / vsat_p[Nx - 1, j]) ** pow_p[Nx - 1, j]) ** (1 / pow_p[Nx - 1, j])
                Evpi = Ev[Nx - 1, j]
            else:
                Ncpi = (Nc[i + 1, j] + Nc[i, j]) / 2
                unpi = (un[i + 1, j] + un[i, j]) / 2
                unpi = unpi / (1 + (np.abs(Ec[i, j] - Ec[i + 1, j]) / dx * unpi / q / vsat_n[i, j]) ** pow_n[i, j]) ** (1 / pow_n[i, j])
                Ecpi = (Ec[i + 1, j] + Ec[i, j]) / 2
                Nvpi = (Nv[i + 1, j] + Nv[i, j]) / 2
                uppi = (up[i + 1, j] + up[i, j]) / 2
                uppi = uppi / (1 + (np.abs(Ec[i, j] - Ec[i + 1, j]) / dx * uppi / q / vsat_p[i, j]) ** pow_p[i, j]) ** (1 / pow_p[i, j])
                Evpi = (Ev[i + 1, j] + Ev[i, j]) / 2

            if j - 1 < 0:
                Ncmj = Nc[i, 0]
                unmj = un[i, 0] / (1 + (np.abs(Ec[i, 0] - Ec[i, 1]) / dy * un[i, 0] / q / vsat_n[i, 0]) ** pow_n[i, 0]) ** (1 / pow_n[i, 0])
                Ecmj = Ec[i, 0]
                Nvmj = Nv[i, 0]
                upmj = up[i, 0] / (1 + (np.abs(Ec[i, 0] - Ec[i, 1]) / dy * up[i, 0] / q / vsat_p[i, 0]) ** pow_p[i, 0]) ** (1 / pow_p[i, 0])
                Evmj = Ev[i, 0]
            else:
                Ncmj = (Nc[i, j - 1] + Nc[i, j]) / 2
                unmj = (un[i, j - 1] + un[i, j]) / 2
                unmj = unmj / (1 + (np.abs(Ec[i, j - 1] - Ec[i, j]) / dy * unmj / q / vsat_n[i, j]) ** pow_n[i, j]) ** (1 / pow_n[i, j])
                Ecmj = (Ec[i, j - 1] + Ec[i, j]) / 2
                Nvmj = (Nv[i, j - 1] + Nv[i, j]) / 2
                upmj = (up[i, j - 1] + up[i, j]) / 2
                # Keep parity with MATLAB source: denominator uses vsat_n in this branch.
                upmj = upmj / (1 + (np.abs(Ec[i, j - 1] - Ec[i, j]) / dy * upmj / q / vsat_n[i, j]) ** pow_p[i, j]) ** (1 / pow_p[i, j])
                Evmj = (Ev[i, j - 1] + Ev[i, j]) / 2

            if j + 1 >= Ny:
                Ncpj = Nc[i, Ny - 1]
                unpj = un[i, Ny - 1] / (1 + (np.abs(Ec[i, Ny - 2] - Ec[i, Ny - 1]) / dy * un[i, Ny - 1] / q / vsat_n[i, Ny - 1]) ** pow_n[i, Ny - 1]) ** (1 / pow_n[i, Ny - 1])
                Ecpj = Ec[i, Ny - 1]
                Nvpj = Nv[i, Ny - 1]
                uppj = up[i, Ny - 1] / (1 + (np.abs(Ec[i, Ny - 2] - Ec[i, Ny - 1]) / dy * up[i, Ny - 1] / q / vsat_p[i, Ny - 1]) ** pow_p[i, Ny - 1]) ** (1 / pow_p[i, Ny - 1])
                Evpj = Ev[i, Ny - 1]
            else:
                Ncpj = (Nc[i, j + 1] + Nc[i, j]) / 2
                unpj = (un[i, j + 1] + un[i, j]) / 2
                unpj = unpj / (1 + (np.abs(Ec[i, j] - Ec[i, j + 1]) / dy * unpj / q / vsat_n[i, j]) ** pow_n[i, j]) ** (1 / pow_n[i, j])
                Ecpj = (Ec[i, j + 1] + Ec[i, j]) / 2
                Nvpj = (Nv[i, j + 1] + Nv[i, j]) / 2
                uppj = (up[i, j + 1] + up[i, j]) / 2
                uppj = uppj / (1 + (np.abs(Ec[i, j] - Ec[i, j + 1]) / dy * uppj / q / vsat_p[i, j]) ** pow_p[i, j]) ** (1 / pow_p[i, j])
                Evpj = (Ev[i, j + 1] + Ev[i, j]) / 2

            napi = unpi * Ncpi * kbT * np.exp(-Ecpi / kbT)
            nami = unmi * Ncmi * kbT * np.exp(-Ecmi / kbT)
            napj = unpj * Ncpj * kbT * np.exp(-Ecpj / kbT)
            namj = unmj * Ncmj * kbT * np.exp(-Ecmj / kbT)
            papi = -uppi * Nvpi * kbT * np.exp(Evpi / kbT)
            pami = -upmi * Nvmi * kbT * np.exp(Evmi / kbT)
            papj = -uppj * Nvpj * kbT * np.exp(Evpj / kbT)
            pamj = -upmj * Nvmj * kbT * np.exp(Evmj / kbT)

            m = findij(i + 1, j + 1, Nx, Ny)
            if m <= 0:
                continue
            idx = m - 1

            nLHS[idx, idx] = nLHS[idx, idx] + (-napi - nami) / dx**2 + (-napj - namj) / dy**2
            pLHS[idx, idx] = pLHS[idx, idx] + (-papi - pami) / dx**2 + (-papj - pamj) / dy**2

            my = findij(i + 1, j + 2, Nx, Ny)
            if my > 0:
                nLHS[idx, my - 1] = nLHS[idx, my - 1] + napj / dy**2
                pLHS[idx, my - 1] = pLHS[idx, my - 1] + papj / dy**2
            elif my == -4:
                if i + 1 < lch1 or i + 1 > lch2:
                    nLHS[idx, idx] = nLHS[idx, idx] + napj / dy**2
                    pLHS[idx, idx] = pLHS[idx, idx] + papj / dy**2
                else:
                    nRHS[idx] = nRHS[idx] - napj / dy**2 * np.exp(Ef4 / kbT)
                    pRHS[idx] = pRHS[idx] - papj / dy**2 * np.exp(-Ef4 / kbT)

            my = findij(i + 1, j, Nx, Ny)
            if my > 0:
                nLHS[idx, my - 1] = nLHS[idx, my - 1] + namj / dy**2
                pLHS[idx, my - 1] = pLHS[idx, my - 1] + pamj / dy**2
            elif my == -3:
                if i + 1 < lch1 or i + 1 > lch2:
                    nLHS[idx, idx] = nLHS[idx, idx] + namj / dy**2
                    pLHS[idx, idx] = pLHS[idx, idx] + pamj / dy**2
                else:
                    nRHS[idx] = nRHS[idx] - namj / dy**2 * np.exp(Ef3 / kbT)
                    pRHS[idx] = pRHS[idx] - pamj / dy**2 * np.exp(-Ef3 / kbT)

            my = findij(i + 2, j + 1, Nx, Ny)
            if my > 0:
                nLHS[idx, my - 1] = nLHS[idx, my - 1] + napi / dx**2
                pLHS[idx, my - 1] = pLHS[idx, my - 1] + papi / dx**2
            elif my == -2:
                if j + 1 < tch1 or j + 1 > tch2:
                    nLHS[idx, idx] = nLHS[idx, idx] + napi / dx**2
                    pLHS[idx, idx] = pLHS[idx, idx] + papi / dx**2
                else:
                    nRHS[idx] = nRHS[idx] - napi / dx**2 * np.exp(Ef2 / kbT)
                    pRHS[idx] = pRHS[idx] - papi / dx**2 * np.exp(-Ef2 / kbT)

            my = findij(i, j + 1, Nx, Ny)
            if my > 0:
                nLHS[idx, my - 1] = nLHS[idx, my - 1] + nami / dx**2
                pLHS[idx, my - 1] = pLHS[idx, my - 1] + pami / dx**2
            elif my == -1:
                if j + 1 < tch1 or j + 1 > tch2:
                    nLHS[idx, idx] = nLHS[idx, idx] + nami / dx**2
                    pLHS[idx, idx] = pLHS[idx, idx] + pami / dx**2
                else:
                    nRHS[idx] = nRHS[idx] - nami / dx**2 * np.exp(Ef1 / kbT)
                    pRHS[idx] = pRHS[idx] - pami / dx**2 * np.exp(-Ef1 / kbT)

    phin = spsolve(nLHS.tocsc(), nRHS)
    Efn = np.real(kbT * np.log(phin)).reshape((Ny, Nx), order="F").T
    phip = spsolve(pLHS.tocsc(), pRHS)
    Efp = np.real(-kbT * np.log(phip)).reshape((Ny, Nx), order="F").T
    return Efn, Efp
