# MOSFET evaluator

**Type:** Feature  
**ID:** `4`  
**Implementation:** `Features/Electronics_Application/MosfetEvaluator/MosfetEvaluatorFeature.py`

Evaluates MOSFET performance from crystal structures and device parameters.

## Inputs

- Device and geometry values such as `channelLengthNm`, `oxideThicknessNm`, `channelThicknessNm`, `temperatureK`, and doping values
- Voltage sweep values such as `drainVoltageVd`, `gateVoltageSweepStartV`, `gateVoltageSweepStopV`, and `numberOfGatePoints`
- Channel material parameters such as `channelNc`, `channelNv`, `channelEpsRel`, `channelUn`, and `channelEgEv`
- Insulator material parameters such as `insulatorNc`, `insulatorNv`, `insulatorEpsRel`, `insulatorUn`, and `insulatorEgEv`

## Outputs

- `status: "success"`
- `key_metrics: dict` with on-current, off-current, threshold voltage, and current ratio
- `J_uA_per_um: list[list[float]]`, `Vgs_V: list[float]`, `Vds_V: list[float]`, and `Q_C_per_m: list[list[float]]`
- `json_filename: str` and `json_path: str`
