# CHGNet Predictor

CHGNet predictor for EMOS, exposed through a dedicated Docker container in the same pattern as MatterSim.

## Public Output Contract

- energy
- forces
- stress
- num_atoms
- relaxed_energy
- relaxed_forces
- relaxed_stress
- relaxed_structure
- relaxed_cell
- relaxed_cif

CHGNet direct prediction returns energy in eV/atom upstream. EMOS normalizes this to total energy in eV to match the existing predictor contract.

## Service

Start the container with:

```bash
docker compose up -d --build chgnet
```