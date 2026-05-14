"""
MosfetSolver.py
---------------
Python wrapper around the 2D drift-diffusion MATLAB solver (mosfet_wrapper.m).

Workflow
--------
1. Pack all simulation inputs into a temporary ``inputs.mat`` file.
2. Launch MATLAB in headless mode via subprocess, pointing it at
   ``mosfet_wrapper.m``.
3. Read the ``outputs.mat`` file produced by MATLAB.
4. Return ``J``, ``Q``, ``Vgs``, ``Vds`` (and ``x``, ``y`` grids) as
   plain NumPy arrays inside a dict.

Requirements
------------
- MATLAB (or MATLAB Runtime + compiled script) reachable on PATH, or
  its full path passed via ``matlab_executable``.
- scipy  (``pip install scipy``)  for .mat I/O.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import scipy.io

from ..pdd_solver_python.MosfetSolver import run as _python_run


# Default material parameters — Silicon channel / SiO2 insulator
# (mirror of constant.m; override via the ``channel_material`` /
#  ``insulator_material`` dicts passed to run())
_SI_DEFAULTS = dict(
    Nc=2.8e25,       # m^-3  (2.8e19 cm^-3)
    Nv=1.04e25,
    ep=11.9,
    un=0.1500,       # m^2/V/s  (1500 cm^2/V/s)
    up=0.0475,
    xi=4.05,         # eV
    Eg=1.12,         # eV
    vsat_n=2e5,      # m/s
    vsat_p=2e5,
    pow_n=2.0,
    pow_p=1.0,
)

_INS_DEFAULTS = dict(
    Nc=1.0,
    Nv=1.0,
    ep=3.9,
    un=1e-3,
    up=1e-3,
    xi=0.9,
    Eg=9.0,
    vsat_n=2e5,
    vsat_p=2e5,
    pow_n=2.0,
    pow_p=1.0,
)

# Directory that contains this file and mosfet_wrapper.m
_SOLVER_DIR = Path(__file__).resolve().parent


def run(
    # ── Geometry ──────────────────────────────────────────────────────────
    channel_length_m: float = 14e-9,
    source_drain_length_m: float = 4e-9,
    oxide_thickness_m: float = 1e-9,
    channel_thickness_m: float = 4e-9,
    dx: float = 5e-10,
    dy: float = 5e-10,
    # ── Temperature ───────────────────────────────────────────────────────
    temperature_K: float = 300.0,
    # ── Contacts / work functions ─────────────────────────────────────────
    gate_work_function_eV: float = 3.65,
    sd_work_function_eV: float = 0.0,
    # ── Doping ────────────────────────────────────────────────────────────
    channel_doping_cm3: float = -1e15,   # negative → p-type
    sd_doping_cm3: float = 1e20,         # positive → n+
    # ── Bias sweeps ───────────────────────────────────────────────────────
    Vgs_start: float = 0.0,
    Vgs_stop: float = 0.7,
    Nvg: int = 14,
    Vds_start: float = 0.0,
    Vds_stop: float = 0.7,
    Nvd: int = 13,
    # ── Material parameters ───────────────────────────────────────────────
    channel_material: dict = None,
    insulator_material: dict = None,
    # ── Runtime ───────────────────────────────────────────────────────────
    matlab_executable: str = "matlab",
    timeout_s: int = 3600,
) -> dict:
    """Run the 2D PDD MOSFET solver and return results as NumPy arrays.

    Parameters
    ----------
    channel_length_m : float
        Channel length in metres (default 14 nm).
    source_drain_length_m : float
        Source/drain extension length in metres (default 4 nm).
    oxide_thickness_m : float
        Gate oxide thickness in metres (default 1 nm).
    channel_thickness_m : float
        Semiconductor channel thickness in metres (default 4 nm).
    dx, dy : float
        Grid spacings in x and y in metres (default 0.5 nm each).
    temperature_K : float
        Simulation temperature in Kelvin (default 300 K).
    gate_work_function_eV : float
        Gate metal work function in eV (default 3.65 eV).
    sd_work_function_eV : float
        Source/drain metal work function in eV (default 0.0 eV).
    channel_doping_cm3 : float
        Channel background doping in cm^-3.  Negative = p-type (default -1e15).
    sd_doping_cm3 : float
        Source and drain doping in cm^-3. Positive = n+ (default 1e20).
    Vgs_start, Vgs_stop : float
        Gate voltage sweep range in Volts.
    Nvg : int
        Number of gate voltage points.
    Vds_start, Vds_stop : float
        Drain voltage sweep range in Volts.
    Nvd : int
        Number of drain voltage points.
    channel_material : dict, optional
        Override any key from _SI_DEFAULTS for the channel semiconductor.
        Keys: Nc, Nv, ep, un, up, xi, Eg, vsat_n, vsat_p, pow_n, pow_p.
    insulator_material : dict, optional
        Override any key from _INS_DEFAULTS for the gate insulator.
    matlab_executable : str
        Path or name of the MATLAB executable (default ``"matlab"``).
    timeout_s : int
        Maximum wall-clock time in seconds before the subprocess is killed.

    Returns
    -------
    dict with keys:
        ``J``    – drain current density (A/m)  shape (Nvg, Nvd)
        ``Q``    – channel charge (C/m)          shape (Nvg, Nvd)
        ``Vgs``  – gate voltage sweep (V)        shape (Nvg,)
        ``Vds``  – drain voltage sweep (V)       shape (Nvd,)
        ``x``    – x-grid coordinates (m)        shape (Nx,)
        ``y``    – y-grid coordinates (m)        shape (Ny,)
    """
    ch  = {**_SI_DEFAULTS,  **(channel_material  or {})}
    ins = {**_INS_DEFAULTS, **(insulator_material or {})}

    inputs = {
        # temperature
        "T":               float(temperature_K),
        # grid
        "dx":              float(dx),
        "dy":              float(dy),
        # geometry
        "L":               float(channel_length_m),
        "sd":              float(source_drain_length_m),
        "Tox":             float(oxide_thickness_m),
        "Tch":             float(channel_thickness_m),
        # contacts
        "phig":            float(gate_work_function_eV),
        "phisd":           float(sd_work_function_eV),
        # doping
        "channel_doping":  float(channel_doping_cm3),
        "sd_doping":       float(sd_doping_cm3),
        # bias sweep
        "Vgs_start":       float(Vgs_start),
        "Vgs_stop":        float(Vgs_stop),
        "Nvg":             float(Nvg),   # MATLAB reads scalars as double
        "Vds_start":       float(Vds_start),
        "Vds_stop":        float(Vds_stop),
        "Nvd":             float(Nvd),
        # channel material
        "ch_Nc":           float(ch["Nc"]),
        "ch_Nv":           float(ch["Nv"]),
        "ch_ep":           float(ch["ep"]),
        "ch_un":           float(ch["un"]),
        "ch_up":           float(ch["up"]),
        "ch_xi":           float(ch["xi"]),
        "ch_Eg":           float(ch["Eg"]),
        "ch_vsat_n":       float(ch["vsat_n"]),
        "ch_vsat_p":       float(ch["vsat_p"]),
        "ch_pow_n":        float(ch["pow_n"]),
        "ch_pow_p":        float(ch["pow_p"]),
        # insulator material
        "ins_Nc":          float(ins["Nc"]),
        "ins_Nv":          float(ins["Nv"]),
        "ins_ep":          float(ins["ep"]),
        "ins_un":          float(ins["un"]),
        "ins_up":          float(ins["up"]),
        "ins_xi":          float(ins["xi"]),
        "ins_Eg":          float(ins["Eg"]),
        "ins_vsat_n":      float(ins["vsat_n"]),
        "ins_vsat_p":      float(ins["vsat_p"]),
        "ins_pow_n":       float(ins["pow_n"]),
        "ins_pow_p":       float(ins["pow_p"]),
    }

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        inputs_path  = tmp / "inputs.mat"
        outputs_path = tmp / "outputs.mat"

        # Write inputs
        scipy.io.savemat(str(inputs_path), inputs)

        # Build MATLAB command:
        #   addpath to solver dir, inject file paths, run wrapper, exit
        matlab_script = (
            f"addpath('{_SOLVER_DIR}'); "
            f"inputs_mat_path  = '{inputs_path}'; "
            f"outputs_mat_path = '{outputs_path}'; "
            f"mosfet_wrapper; "
            f"exit;"
        )
        cmd = [
            matlab_executable,
            "-nodisplay", "-nosplash", "-nodesktop",
            "-r", matlab_script,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                cwd=str(_SOLVER_DIR),
            )
        except FileNotFoundError:
            return run_python(
                channel_length_m=channel_length_m,
                source_drain_length_m=source_drain_length_m,
                oxide_thickness_m=oxide_thickness_m,
                channel_thickness_m=channel_thickness_m,
                dx=dx,
                dy=dy,
                temperature_K=temperature_K,
                gate_work_function_eV=gate_work_function_eV,
                sd_work_function_eV=sd_work_function_eV,
                channel_doping_cm3=channel_doping_cm3,
                sd_doping_cm3=sd_doping_cm3,
                Vgs_start=Vgs_start,
                Vgs_stop=Vgs_stop,
                Nvg=Nvg,
                Vds_start=Vds_start,
                Vds_stop=Vds_stop,
                Nvd=Nvd,
                channel_material=channel_material,
                insulator_material=insulator_material,
            )
        except subprocess.TimeoutExpired:
            return run_python(
                channel_length_m=channel_length_m,
                source_drain_length_m=source_drain_length_m,
                oxide_thickness_m=oxide_thickness_m,
                channel_thickness_m=channel_thickness_m,
                dx=dx,
                dy=dy,
                temperature_K=temperature_K,
                gate_work_function_eV=gate_work_function_eV,
                sd_work_function_eV=sd_work_function_eV,
                channel_doping_cm3=channel_doping_cm3,
                sd_doping_cm3=sd_doping_cm3,
                Vgs_start=Vgs_start,
                Vgs_stop=Vgs_stop,
                Nvg=Nvg,
                Vds_start=Vds_start,
                Vds_stop=Vds_stop,
                Nvd=Nvd,
                channel_material=channel_material,
                insulator_material=insulator_material,
            )

        if result.returncode != 0:
            return run_python(
                channel_length_m=channel_length_m,
                source_drain_length_m=source_drain_length_m,
                oxide_thickness_m=oxide_thickness_m,
                channel_thickness_m=channel_thickness_m,
                dx=dx,
                dy=dy,
                temperature_K=temperature_K,
                gate_work_function_eV=gate_work_function_eV,
                sd_work_function_eV=sd_work_function_eV,
                channel_doping_cm3=channel_doping_cm3,
                sd_doping_cm3=sd_doping_cm3,
                Vgs_start=Vgs_start,
                Vgs_stop=Vgs_stop,
                Nvg=Nvg,
                Vds_start=Vds_start,
                Vds_stop=Vds_stop,
                Nvd=Nvd,
                channel_material=channel_material,
                insulator_material=insulator_material,
            )

        if not outputs_path.exists():
            return run_python(
                channel_length_m=channel_length_m,
                source_drain_length_m=source_drain_length_m,
                oxide_thickness_m=oxide_thickness_m,
                channel_thickness_m=channel_thickness_m,
                dx=dx,
                dy=dy,
                temperature_K=temperature_K,
                gate_work_function_eV=gate_work_function_eV,
                sd_work_function_eV=sd_work_function_eV,
                channel_doping_cm3=channel_doping_cm3,
                sd_doping_cm3=sd_doping_cm3,
                Vgs_start=Vgs_start,
                Vgs_stop=Vgs_stop,
                Nvg=Nvg,
                Vds_start=Vds_start,
                Vds_stop=Vds_stop,
                Nvd=Nvd,
                channel_material=channel_material,
                insulator_material=insulator_material,
            )

        raw = scipy.io.loadmat(str(outputs_path))

    return {
        "J":   np.array(raw["J"],   dtype=float),
        "Q":   np.array(raw["Q"],   dtype=float),
        "Vgs": np.array(raw["Vgs"], dtype=float).ravel(),
        "Vds": np.array(raw["Vds"], dtype=float).ravel(),
        "x":   np.array(raw["x"],   dtype=float).ravel(),
        "y":   np.array(raw["y"],   dtype=float).ravel(),
    }


def run_python(
    # ── Geometry ──────────────────────────────────────────────────────────
    channel_length_m: float = 14e-9,
    source_drain_length_m: float = 4e-9,
    oxide_thickness_m: float = 1e-9,
    channel_thickness_m: float = 4e-9,
    dx: float = 5e-10,
    dy: float = 5e-10,
    # ── Temperature ───────────────────────────────────────────────────────
    temperature_K: float = 300.0,
    # ── Contacts / work functions ─────────────────────────────────────────
    gate_work_function_eV: float = 3.65,
    sd_work_function_eV: float = 0.0,
    # ── Doping ────────────────────────────────────────────────────────────
    channel_doping_cm3: float = -1e15,
    sd_doping_cm3: float = 1e20,
    # ── Bias sweeps ───────────────────────────────────────────────────────
    Vgs_start: float = 0.0,
    Vgs_stop: float = 0.7,
    Nvg: int = 14,
    Vds_start: float = 0.0,
    Vds_stop: float = 0.7,
    Nvd: int = 13,
    # ── Material parameters ───────────────────────────────────────────────
    channel_material: dict = None,
    insulator_material: dict = None,
) -> dict:
    return _python_run(
        channel_length_m=channel_length_m,
        source_drain_length_m=source_drain_length_m,
        oxide_thickness_m=oxide_thickness_m,
        channel_thickness_m=channel_thickness_m,
        dx=dx,
        dy=dy,
        temperature_K=temperature_K,
        gate_work_function_eV=gate_work_function_eV,
        sd_work_function_eV=sd_work_function_eV,
        channel_doping_cm3=channel_doping_cm3,
        sd_doping_cm3=sd_doping_cm3,
        Vgs_start=Vgs_start,
        Vgs_stop=Vgs_stop,
        Nvg=Nvg,
        Vds_start=Vds_start,
        Vds_stop=Vds_stop,
        Nvd=Nvd,
        channel_material=channel_material,
        insulator_material=insulator_material,
    )
