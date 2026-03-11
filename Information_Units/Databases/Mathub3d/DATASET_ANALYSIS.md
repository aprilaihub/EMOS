# MatHub-3D Dataset Analysis

## Source Information

- **Full Name**: Materials Hub with Three-Dimensional Structures (MatHub-3d)
- **Article DOI**: [10.1002/mgea.21](https://onlinelibrary.wiley.com/doi/10.1002/mgea.21)
- **URL**: [https://www.mathub3d.net/](https://www.mathub3d.net/) (accessed 07/04/2025)
- **Description**: A first-principles repository established under the Materials Genome Initiative, serving as the foundation for high-throughput (HTP) calculations, property analysis, and design of thermoelectric materials.

> **Note**: The URL was accessible on 07/04/2025 but may no longer be considered "safe" by Chrome or institutional IT systems.

---

## File Inventory

The dataset is distributed as `MatHub-3d.zip` (9.7 MB compressed) containing three files:

| File | Uncompressed Size | Format | Entries |
|------|-------------------|--------|---------|
| MatHub-3d.json | 52 MB | JSON (list of dicts) | 74,177 |
| MatHub-3d.pkl | 839 KB | Joblib-serialized pandas DataFrame | 7,150 |
| electric_data.xlsx | 2.4 MB | Excel (3 sheets) | 10,195 |

---

## Are the Files Duplicated?

**No — they are complementary, not duplicated.** Each file serves a different purpose:

1. **MatHub-3d.json** — The **main/complete database** with 74,177 entries covering structural, energetic, electronic, and magnetic properties. This is the "basic dataset" (excluding band structures). ~40% of entries have full computed DFT results; the remainder have initial structural data (lattice parameters, spacegroup, formula, elements).

2. **MatHub-3d.pkl** — A **curated lightweight subset** of 7,150 materials with electrical transport properties (carrier concentrations, conductivity, mobility for both n-type and p-type). Serialized with `joblib` (not standard `pickle`). All 7,150 entries are a subset of the JSON.

3. **electric_data.xlsx** — The most complete **electrical/thermoelectric transport dataset** with 10,195 entries and detailed properties including Seebeck coefficients, power factors, and electronic thermal conductivity — properties found in **neither** the JSON nor PKL.

### Relationship Between Files

```
JSON (74,177) ⊃ XLSX (10,195) ⊃ PKL (7,150)
```

- 7,107 of the 7,150 PKL entries match JSON entries (by ICSD identifier)
- All 7,150 PKL entries are found in the XLSX
- 8,719 of the 10,195 XLSX entries match JSON entries

---

## Properties by File

### MatHub-3d.json — 54 Fields

| Category | Properties | Completeness |
|----------|-----------|-------------|
| **Identity** | `_id`, `name`, `name1`, `mip3d_name`, `folder`, `formula`, `elements`, `nelements` | 100% |
| **Lattice (before relaxation)** | `before_a`, `before_b`, `before_c`, `before_alpha`, `before_beta`, `before_gamma` | 100% |
| **Lattice (after relaxation)** | `after_a`, `after_b`, `after_c`, `after_alpha`, `after_beta`, `after_gamma` | ~40% |
| **Structure** | `spacegroup`, `spacegroup_type`, `natoms`, `mass`, `volume`, `density` | 40–100% |
| **Energetics** | `energy`, `energy_per_atom` | ~40% |
| **Electronic** | `gap`, `vbm`, `cbm`, `vbm_k`, `cbm_k`, `efermi`, `Eband_CBM`, `Eband_VBM` | 8.5–40% |
| **Magnetic** | `is_magnetic`, `total_magnetic_moment` | ~40% |
| **Mechanical** | `bulk_modulus` | ~22% |
| **Transport** | `dp_n`, `dp_p`, `dp_n_up`, `dp_n_down`, `dp_p_up`, `dp_p_down`, `trans` | 5–14% |
| **DFT Settings** | `LDAU`, `LDAUJ`, `LDAUL`, `LDAUU` | 28–40% |
| **Advanced** | `phonon`, `qha` | ~0.2% (130 entries) |

### MatHub-3d.pkl — 11 Columns

| Column | Description |
|--------|-------------|
| `formula` | Chemical formula |
| `spacegroup` | Space group number |
| `SourceID` | Source identifier (e.g., `1453_icsd-190991_Ni1Sn1Ti1`) |
| `energy_per_atom` | Energy per atom (eV) |
| `gap` | Band gap (eV) |
| `carr_n(10^20/cm3)` | n-type carrier concentration |
| `sigma_n(S/m)` | n-type electrical conductivity |
| `carr_p(10^20/cm3)` | p-type carrier concentration |
| `sigma_p(S/m)` | p-type electrical conductivity |
| `mob_n(cm2/Vs)` | n-type carrier mobility |
| `mob_p(cm2/Vs)` | p-type carrier mobility |

> **Note**: This file requires `joblib` to load (not standard `pickle`). Use `joblib.load('MatHub-3d.pkl')`.

### electric_data.xlsx — 3 Sheets

#### Sheet: `elecinfo` (10,195 rows × 20 columns)

| Column | Description |
|--------|-------------|
| `SourceID` | Source identifier |
| `MatHubID-compound` | MatHub-3d compound ID |
| `SS_1`, `SS_2` | Spin–orbit split-off values |
| `carr_n(10^20/cm3)` | n-type carrier concentration |
| `DP_n(eV)` | n-type deformation potential |
| `BM(GPa)` | Bulk modulus |
| `sigma_n(S/m)` | n-type electrical conductivity |
| `Seebeck_n(uV/K)` | n-type Seebeck coefficient |
| `Ke_n(Wm-1K-1)` | n-type electronic thermal conductivity |
| `PF_n(1E-4Wm-1K-2)` | n-type power factor |
| `carr_p(10^20/cm3)` | p-type carrier concentration |
| `DP_p(eV)` | p-type deformation potential |
| `sigma_p(S/m)` | p-type electrical conductivity |
| `Seebeck_p(uV/K)` | p-type Seebeck coefficient |
| `Ke_p(Wm-1K-1)` | p-type electronic thermal conductivity |
| `PF_p(1E-4Wm-1K-2)` | p-type power factor |
| `PF/Ke_N` | n-type power factor / thermal conductivity ratio |
| `PF/Ke_P` | p-type power factor / thermal conductivity ratio |

#### Sheet: `n` (10,173 rows × 1 column)

List of SourceIDs with Seebeck coefficient < -200 µV/K (good n-type thermoelectric candidates).

#### Sheet: `p` (10,163 rows × 1 column)

List of SourceIDs with Seebeck coefficient < 200 µV/K (good p-type thermoelectric candidates).

---

## Summary

The MatHub-3d dataset provides a comprehensive first-principles materials database focused on thermoelectric applications. The JSON file is the primary data source with broad structural/electronic coverage, while the XLSX and PKL files provide progressively focused subsets with detailed electrical transport and thermoelectric properties not available in the JSON.
