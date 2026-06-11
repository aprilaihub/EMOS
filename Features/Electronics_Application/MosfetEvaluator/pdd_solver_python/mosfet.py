"""Top-level MOSFET sweep matching MATLAB ``mosfet.m``."""

from __future__ import annotations

import numpy as np

try:
    from .constant import EP0, KB, Q
    from .solve import solve_device
except ImportError:  # Allows direct script-style imports.
    from constant import EP0, KB, Q
    from solve import solve_device


def run_solver(inputs: dict) -> dict:
    q = Q
    kbT = KB * inputs["T"]

    dx = inputs["dx"]
    dy = inputs["dy"]
    L = inputs["L"]
    sd = inputs["sd"]
    Tox = inputs["Tox"]
    Tch = inputs["Tch"]

    Ns = int(np.ceil(sd / dx))
    Nc_grid = int(np.ceil(L / dx))
    Nd = int(np.ceil(sd / dx))
    Nx = Ns + Nc_grid + Nd
    lch1 = Ns + 1
    lch2 = Ns + Nc_grid

    No = int(np.ceil(Tox / dy))
    Nt = int(np.ceil(Tch / dy))
    Ny = No * 2 + Nt
    tch1 = No + 1
    tch2 = No + Nt

    x = dx * np.linspace(0, Nx, Nx)
    y = dy * np.linspace(0, Ny, Ny)

    Nc = np.ones((Nx, Ny), dtype=float) * inputs["ins_Nc"]
    Nc[:, tch1 - 1 : tch2] = inputs["ch_Nc"]
    Nv = np.ones((Nx, Ny), dtype=float) * inputs["ins_Nv"]
    Nv[:, tch1 - 1 : tch2] = inputs["ch_Nv"]
    un = np.ones((Nx, Ny), dtype=float) * inputs["ins_un"]
    un[:, tch1 - 1 : tch2] = inputs["ch_un"]
    up = np.ones((Nx, Ny), dtype=float) * inputs["ins_up"]
    up[:, tch1 - 1 : tch2] = inputs["ch_up"]
    vsat_n = np.ones((Nx, Ny), dtype=float) * inputs["ins_vsat_n"]
    vsat_n[:, tch1 - 1 : tch2] = inputs["ch_vsat_n"]
    vsat_p = np.ones((Nx, Ny), dtype=float) * inputs["ins_vsat_p"]
    vsat_p[:, tch1 - 1 : tch2] = inputs["ch_vsat_p"]
    pow_n = np.ones((Nx, Ny), dtype=float) * inputs["ins_pow_n"]
    pow_n[:, tch1 - 1 : tch2] = inputs["ch_pow_n"]
    pow_p = np.ones((Nx, Ny), dtype=float) * inputs["ins_pow_p"]
    pow_p[:, tch1 - 1 : tch2] = inputs["ch_pow_p"]
    Eg = np.ones((Nx, Ny), dtype=float) * q * inputs["ins_Eg"]
    Eg[:, tch1 - 1 : tch2] = q * inputs["ch_Eg"]
    EP = np.ones((Nx, Ny), dtype=float) * EP0 * inputs["ins_ep"]
    EP[:, tch1 - 1 : tch2] = EP0 * inputs["ch_ep"]
    xi = np.ones((Nx, Ny), dtype=float) * q * inputs["ins_xi"]
    xi[:, tch1 - 1 : tch2] = q * inputs["ch_xi"]

    NB = np.zeros((Nx, Ny), dtype=float)
    NB[lch1 - 1 : lch2, tch1 - 1 : tch2] = 1e6 * inputs["channel_doping"]
    NB[: lch1 - 1, tch1 - 1 : tch2] = 1e6 * inputs["sd_doping"]
    NB[lch2:, tch1 - 1 : tch2] = 1e6 * inputs["sd_doping"]

    Vgs = np.linspace(inputs["Vgs_start"], inputs["Vgs_stop"], int(inputs["Nvg"]))
    Vds = np.linspace(inputs["Vds_start"], inputs["Vds_stop"], int(inputs["Nvd"]))
    J = np.zeros((len(Vgs), len(Vds)), dtype=float)
    Qout = np.zeros((len(Vgs), len(Vds)), dtype=float)

    for i, vgs in enumerate(Vgs):
        for j, vds in enumerate(Vds):
            Ef1 = 0.0
            Ef2 = -q * vds
            Ef3 = -q * vgs
            Ef4 = -q * vgs
            Ec1 = q * inputs["phisd"] + Ef1
            Ec2 = q * inputs["phisd"] + Ef2
            Ec3 = q * inputs["phig"] + Ef3
            Ec4 = q * inputs["phig"] + Ef4

            Ec, Efn, Efp = solve_device(
                q,
                kbT,
                Nx,
                Ny,
                dx,
                dy,
                NB,
                EP,
                Eg,
                un,
                up,
                vsat_n,
                vsat_p,
                pow_n,
                pow_p,
                Nc,
                Nv,
                xi,
                tch1,
                tch2,
                lch1,
                lch2,
                Ec1,
                Ec2,
                Ec3,
                Ec4,
                Ef1,
                Ef2,
                Ef3,
                Ef4,
            )

            Ev = Ec - Eg
            n = Nc * np.exp((Efn - Ec) / kbT)
            p = Nv * np.exp((Ev - Efp) / kbT)
            grad_ec = gradient_transposed(Ec) / dx
            grad_efn = gradient_transposed(Efn) / dx
            grad_efp = gradient_transposed(Efp) / dx

            Jn = un / (1 + (np.abs(grad_ec) * un / q / vsat_n) ** pow_n) ** (1.0 / pow_n) * n * grad_efn
            Jp = up / (1 + (np.abs(grad_ec) * up / q / vsat_p) ** pow_p) ** (1.0 / pow_p) * p * grad_efp

            J[i, j] = -np.sum(Jn[Nx - 1, tch1 - 1 : tch2] + Jp[Nx - 1, tch1 - 1 : tch2]) * dy
            Qout[i, j] = -q * np.sum(
                n[lch1 - 1 : lch2, tch1 - 1 : tch2]
                - p[lch1 - 1 : lch2, tch1 - 1 : tch2]
                - NB[lch1 - 1 : lch2, tch1 - 1 : tch2]
            ) * dx * dy

    return {"J": J, "Q": Qout, "Vgs": Vgs, "Vds": Vds, "x": x, "y": y}


def gradient_transposed(matrix: np.ndarray) -> np.ndarray:
    # MATLAB expression: gradient(matrix.').'
    # With one output, MATLAB gradient on a matrix uses column-direction derivative.
    return np.gradient(matrix.T, axis=1).T
