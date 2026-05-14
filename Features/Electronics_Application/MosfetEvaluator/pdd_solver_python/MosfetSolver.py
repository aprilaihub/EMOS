"""Public entry point for the pure-Python MOSFET PDD solver."""

from __future__ import annotations

try:
    from .constant import INS_DEFAULTS, SI_DEFAULTS
    from .mosfet import run_solver
except ImportError:  # Allows `from MosfetSolver import run` in local notebooks.
    from constant import INS_DEFAULTS, SI_DEFAULTS
    from mosfet import run_solver


def run(
    channel_length_m: float = 14e-9,
    source_drain_length_m: float = 4e-9,
    oxide_thickness_m: float = 1e-9,
    channel_thickness_m: float = 4e-9,
    dx: float = 5e-10,
    dy: float = 5e-10,
    temperature_K: float = 300.0,
    gate_work_function_eV: float = 3.65,
    sd_work_function_eV: float = 0.0,
    channel_doping_cm3: float = -1e15,
    sd_doping_cm3: float = 1e20,
    Vgs_start: float = 0.0,
    Vgs_stop: float = 0.7,
    Nvg: int = 14,
    Vds_start: float = 0.0,
    Vds_stop: float = 0.7,
    Nvd: int = 13,
    channel_material: dict | None = None,
    insulator_material: dict | None = None,
) -> dict:
    ch = {**SI_DEFAULTS, **(channel_material or {})}
    ins = {**INS_DEFAULTS, **(insulator_material or {})}

    inputs = {
        "T": float(temperature_K),
        "dx": float(dx),
        "dy": float(dy),
        "L": float(channel_length_m),
        "sd": float(source_drain_length_m),
        "Tox": float(oxide_thickness_m),
        "Tch": float(channel_thickness_m),
        "phig": float(gate_work_function_eV),
        "phisd": float(sd_work_function_eV),
        "channel_doping": float(channel_doping_cm3),
        "sd_doping": float(sd_doping_cm3),
        "Vgs_start": float(Vgs_start),
        "Vgs_stop": float(Vgs_stop),
        "Nvg": float(Nvg),
        "Vds_start": float(Vds_start),
        "Vds_stop": float(Vds_stop),
        "Nvd": float(Nvd),
        "ch_Nc": float(ch["Nc"]),
        "ch_Nv": float(ch["Nv"]),
        "ch_ep": float(ch["ep"]),
        "ch_un": float(ch["un"]),
        "ch_up": float(ch["up"]),
        "ch_xi": float(ch["xi"]),
        "ch_Eg": float(ch["Eg"]),
        "ch_vsat_n": float(ch["vsat_n"]),
        "ch_vsat_p": float(ch["vsat_p"]),
        "ch_pow_n": float(ch["pow_n"]),
        "ch_pow_p": float(ch["pow_p"]),
        "ins_Nc": float(ins["Nc"]),
        "ins_Nv": float(ins["Nv"]),
        "ins_ep": float(ins["ep"]),
        "ins_un": float(ins["un"]),
        "ins_up": float(ins["up"]),
        "ins_xi": float(ins["xi"]),
        "ins_Eg": float(ins["Eg"]),
        "ins_vsat_n": float(ins["vsat_n"]),
        "ins_vsat_p": float(ins["vsat_p"]),
        "ins_pow_n": float(ins["pow_n"]),
        "ins_pow_p": float(ins["pow_p"]),
    }
    return run_solver(inputs)
