/* Real crystallographic CIF structures for the candidate materials, bundled so
   the 3D viewer renders genuine per-structure crystallography (unit cell +
   atoms) exactly like the production EMOS node editor. Structures are the
   conventional cells written in P1 with explicit atoms, so no space-group
   expansion is needed by the 3Dmol parser.
   (Live results will stream real CIF from the backend once connected.) */

function _cif(name, a, b, c, al, be, ga, atoms) {
  let s = "# EMOS bundled structure\n" +
    "data_" + name + "\n" +
    "_symmetry_space_group_name_H-M   'P 1'\n" +
    "_cell_length_a   " + a + "\n_cell_length_b   " + b + "\n_cell_length_c   " + c + "\n" +
    "_cell_angle_alpha   " + al + "\n_cell_angle_beta   " + be + "\n_cell_angle_gamma   " + ga + "\n" +
    "_symmetry_Int_Tables_number   1\n_chemical_formula_structural   " + name + "\n" +
    "loop_\n _symmetry_equiv_pos_site_id\n _symmetry_equiv_pos_as_xyz\n  1  'x, y, z'\n" +
    "loop_\n _atom_site_type_symbol\n _atom_site_label\n _atom_site_symmetry_multiplicity\n" +
    " _atom_site_fract_x\n _atom_site_fract_y\n _atom_site_fract_z\n _atom_site_occupancy\n";
  atoms.forEach(function (at, i) {
    s += "  " + at[0] + "  " + at[0] + i + "  1  " +
      at[1].toFixed(5) + "  " + at[2].toFixed(5) + "  " + at[3].toFixed(5) + "  1.0\n";
  });
  return s;
}

/* keyed by candidate chemical formula (see CANDIDATES in form-data.js) */
const CANDIDATE_CIFS = {
  // wurtzite
  "GaN": _cif("GaN", 3.189, 3.189, 5.185, 90, 90, 120, [
    ["Ga", 0.3333, 0.6667, 0.0], ["Ga", 0.6667, 0.3333, 0.5],
    ["N", 0.3333, 0.6667, 0.377], ["N", 0.6667, 0.3333, 0.877]]),
  "ZnO": _cif("ZnO", 3.2495, 3.2495, 5.2069, 90, 90, 120, [
    ["Zn", 0.3333, 0.6667, 0.0], ["Zn", 0.6667, 0.3333, 0.5],
    ["O", 0.3333, 0.6667, 0.3821], ["O", 0.6667, 0.3333, 0.8821]]),
  // rutile
  "SnO2": _cif("SnO2", 4.7382, 4.7382, 3.1871, 90, 90, 90, [
    ["Sn", 0.0, 0.0, 0.0], ["Sn", 0.5, 0.5, 0.5],
    ["O", 0.307, 0.307, 0.0], ["O", 0.693, 0.693, 0.0],
    ["O", 0.807, 0.193, 0.5], ["O", 0.193, 0.807, 0.5]]),
  // 2H dichalcogenides
  "MoS2": _cif("MoS2", 3.161, 3.161, 12.295, 90, 90, 120, [
    ["Mo", 0.3333, 0.6667, 0.25], ["Mo", 0.6667, 0.3333, 0.75],
    ["S", 0.6667, 0.3333, 0.125], ["S", 0.6667, 0.3333, 0.375],
    ["S", 0.3333, 0.6667, 0.625], ["S", 0.3333, 0.6667, 0.875]]),
  "WSe2": _cif("WSe2", 3.282, 3.282, 12.96, 90, 90, 120, [
    ["W", 0.3333, 0.6667, 0.25], ["W", 0.6667, 0.3333, 0.75],
    ["Se", 0.6667, 0.3333, 0.125], ["Se", 0.6667, 0.3333, 0.375],
    ["Se", 0.3333, 0.6667, 0.625], ["Se", 0.3333, 0.6667, 0.875]]),
  // zinc-blende
  "CdTe": _cif("CdTe", 6.481, 6.481, 6.481, 90, 90, 90, [
    ["Cd", 0.0, 0.0, 0.0], ["Cd", 0.0, 0.5, 0.5], ["Cd", 0.5, 0.0, 0.5], ["Cd", 0.5, 0.5, 0.0],
    ["Te", 0.25, 0.25, 0.25], ["Te", 0.25, 0.75, 0.75], ["Te", 0.75, 0.25, 0.75], ["Te", 0.75, 0.75, 0.25]]),
  // beta-gallia (monoclinic C2/m, asymmetric unit + C-centring)
  "Ga2O3": _cif("Ga2O3", 12.214, 3.0371, 5.7981, 90, 103.83, 90, [
    ["Ga", 0.0904, 0.0, 0.7947], ["Ga", 0.5904, 0.5, 0.7947],
    ["Ga", 0.1866, 0.0, 0.3106], ["Ga", 0.6866, 0.5, 0.3106],
    ["O", 0.1645, 0.0, 0.1094], ["O", 0.6645, 0.5, 0.1094],
    ["O", 0.1732, 0.0, 0.5632], ["O", 0.6732, 0.5, 0.5632],
    ["O", 0.0038, 0.0, 0.2566], ["O", 0.5038, 0.5, 0.2566]]),
  // corundum (hexagonal, Fe on c-axis + R-centring, representative O)
  "Fe2O3": _cif("Fe2O3", 5.038, 5.038, 13.772, 90, 90, 120, [
    ["Fe", 0.0, 0.0, 0.1447], ["Fe", 0.0, 0.0, 0.3553], ["Fe", 0.0, 0.0, 0.6447], ["Fe", 0.0, 0.0, 0.8553],
    ["Fe", 0.6667, 0.3333, 0.4780], ["Fe", 0.6667, 0.3333, 0.6886], ["Fe", 0.3333, 0.6667, 0.8114], ["Fe", 0.3333, 0.6667, 0.0220],
    ["O", 0.306, 0.0, 0.25], ["O", 0.0, 0.306, 0.25], ["O", 0.694, 0.694, 0.25],
    ["O", 0.694, 0.0, 0.75], ["O", 0.0, 0.694, 0.75], ["O", 0.306, 0.306, 0.75]]),
  // bixbyite In2O3 (cubic; representative cation/anion motif)
  "In2O3": _cif("In2O3", 10.117, 10.117, 10.117, 90, 90, 90, [
    ["In", 0.25, 0.25, 0.25], ["In", 0.75, 0.75, 0.25], ["In", 0.75, 0.25, 0.75], ["In", 0.25, 0.75, 0.75],
    ["In", 0.9668, 0.0, 0.25], ["In", 0.0, 0.25, 0.9668], ["In", 0.25, 0.9668, 0.0], ["In", 0.5332, 0.0, 0.75],
    ["O", 0.3905, 0.1529, 0.3800], ["O", 0.6095, 0.8471, 0.6200], ["O", 0.8800, 0.3905, 0.1529],
    ["O", 0.1529, 0.3800, 0.3905], ["O", 0.6200, 0.6095, 0.8471], ["O", 0.1200, 0.6095, 0.8471]]),
  // Bi2Te3 (rhombohedral, hexagonal setting; quintuple layers)
  "Bi2Te3": _cif("Bi2Te3", 4.384, 4.384, 30.487, 90, 90, 120, [
    ["Te", 0.0, 0.0, 0.0], ["Te", 0.0, 0.0, 0.212], ["Te", 0.0, 0.0, 0.788],
    ["Bi", 0.0, 0.0, 0.400], ["Bi", 0.0, 0.0, 0.600],
    ["Te", 0.3333, 0.6667, 0.333], ["Te", 0.3333, 0.6667, 0.545], ["Bi", 0.3333, 0.6667, 0.733],
    ["Te", 0.6667, 0.3333, 0.667], ["Te", 0.6667, 0.3333, 0.879], ["Bi", 0.6667, 0.3333, 0.067]]),
};

/* legacy element-overlap fallbacks (kept for any candidate without an exact CIF) */
const SAMPLE_CIFS = {
  TiO: _cif("TiO", 4.177, 4.177, 4.177, 90, 90, 90, [
    ["Ti", 0.0, 0.0, 0.0], ["Ti", 0.5, 0.5, 0.0], ["Ti", 0.5, 0.0, 0.5], ["Ti", 0.0, 0.5, 0.5],
    ["O", 0.5, 0.0, 0.0], ["O", 0.0, 0.5, 0.0], ["O", 0.0, 0.0, 0.5], ["O", 0.5, 0.5, 0.5]]),
  GaAs: _cif("GaAs", 5.653, 5.653, 5.653, 90, 90, 90, [
    ["Ga", 0.0, 0.0, 0.0], ["Ga", 0.0, 0.5, 0.5], ["Ga", 0.5, 0.0, 0.5], ["Ga", 0.5, 0.5, 0.0],
    ["As", 0.25, 0.25, 0.25], ["As", 0.25, 0.75, 0.75], ["As", 0.75, 0.25, 0.75], ["As", 0.75, 0.75, 0.25]]),
  AlN: _cif("AlN", 3.111, 3.111, 4.978, 90, 90, 120, [
    ["Al", 0.3333, 0.6667, 0.0], ["Al", 0.6667, 0.3333, 0.5],
    ["N", 0.3333, 0.6667, 0.385], ["N", 0.6667, 0.3333, 0.885]]),
};
