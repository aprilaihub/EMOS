"""Physical constants and default material parameters.

This mirrors ``constant.m`` from the original MATLAB implementation.
"""

SI_DEFAULTS = {
    "Nc": 2.8e25,
    "Nv": 1.04e25,
    "ep": 11.9,
    "un": 0.1500,
    "up": 0.0475,
    "xi": 4.05,
    "Eg": 1.12,
    "vsat_n": 2e5,
    "vsat_p": 2e5,
    "pow_n": 2.0,
    "pow_p": 1.0,
}

INS_DEFAULTS = {
    "Nc": 1.0,
    "Nv": 1.0,
    "ep": 3.9,
    "un": 1e-3,
    "up": 1e-3,
    "xi": 0.9,
    "Eg": 9.0,
    "vsat_n": 2e5,
    "vsat_p": 2e5,
    "pow_n": 2.0,
    "pow_p": 1.0,
}

Q = 1.6e-19
KB = 1.380649e-23
EP0 = 8.853e-12
