"""Index helper matching MATLAB ``findij.m`` semantics."""


def findij(i: int, j: int, Nx: int, Ny: int) -> int:
    m = (i - 1) * Ny + j
    if i < 1:
        m = -1
    elif i > Nx:
        m = -2

    if j < 1:
        m = -3
    elif j > Ny:
        m = -4

    return m
