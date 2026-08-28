"""
Mock data for testing.

Contains reusable mock data structures that represent real API responses
and structure data.
"""

# COD OPTIMADE API Response samples
COD_FE_RESPONSE = {
    "data": [
        {
            "id": "1000000",
            "type": "structure",
            "attributes": {
                "chemical_formula_reduced": "Fe",
                "lattice_vectors": [[2.87, 0, 0], [0, 2.87, 0], [0, 0, 2.87]],
                "species": [
                    {
                        "name": "Fe",
                        "chemical_symbols": ["Fe"],
                        "concentration": [1.0]
                    }
                ],
                "species_at_sites": ["Fe", "Fe"],
                "cartesian_site_positions": [[0, 0, 0], [1.435, 1.435, 1.435]],
                "fractional_site_positions": [[0, 0, 0], [0.5, 0.5, 0.5]],
                "nelements": 1,
                "natoms": 2,
                "volume": 23.6,
                "spacegroup_number": 229,
                "spacegroup_symbol": "Im-3m"
            }
        }
    ]
}

COD_AL2O3_RESPONSE = {
    "data": [
        {
            "id": "2000000",
            "type": "structure",
            "attributes": {
                "chemical_formula_reduced": "Al2O3",
                "lattice_vectors": [[4.76, 0, 0], [0, 4.76, 0], [0, 0, 13.0]],
                "species": [
                    {"name": "Al", "chemical_symbols": ["Al"], "concentration": [0.4]},
                    {"name": "O", "chemical_symbols": ["O"], "concentration": [0.6]}
                ],
                "species_at_sites": ["Al", "Al", "O", "O", "O"],
                "cartesian_site_positions": [
                    [0, 0, 0],
                    [2.38, 2.38, 6.5],
                    [1.0, 2.0, 3.0],
                    [0.5, 1.5, 9.0],
                    [2.0, 0.5, 12.0]
                ],
                "fractional_site_positions": [
                    [0, 0, 0],
                    [0.5, 0.5, 0.5],
                    [0.2, 0.4, 0.23],
                    [0.1, 0.3, 0.69],
                    [0.42, 0.1, 0.92]
                ],
                "nelements": 2,
                "natoms": 5,
                "volume": 294.9,
                "spacegroup_number": 155,
                "spacegroup_symbol": "R32/m"
            }
        }
    ]
}

COD_EMPTY_RESPONSE = {
    "data": []
}

# Property mapping samples
STANDARD_PROPERTIES = {
    "nelements": 2,
    "natoms": 10,
    "volume": [50, 200],
    "spacegroup_number": 225
}

# API Filter samples
OPTIMADE_FILTERS = {
    "single_element": 'elements HAS "Fe"',
    "formula": '(elements HAS "Al" AND elements HAS "O")',
    "with_nelements": 'elements HAS "Fe" AND nelements = 2',
    "with_range": 'elements HAS "Fe" AND nelements >= 1 AND nelements <= 3'
}

# MatHub-3d JSON entry samples (matching structure of MatHub-3d.json)
MATHUB3D_FE_ENTRY = {
    "_id": "12345",
    "name": "icsd-100001-Fe2O3",
    "folder": "icsd-100001",
    "formula": "Fe2O3",
    "elements": ["Fe", "O"],
    "nelements": 2,
    "spacegroup": 167,
    "spacegroup_type": "R-3c",
    "before_a": 5.035, "before_b": 5.035, "before_c": 13.747,
    "before_alpha": 90.0, "before_beta": 90.0, "before_gamma": 120.0,
    "after_a": 5.10, "after_b": 5.10, "after_c": 13.85,
    "after_alpha": 90.0, "after_beta": 90.0, "after_gamma": 120.0,
    "energy": -44.5, "energy_per_atom": -4.45,
    "gap": 1.8, "efermi": 3.2, "vbm": 2.1, "cbm": 3.9,
    "is_magnetic": True, "total_magnetic_moment": 10.0,
    "natoms": 10, "volume": 310.5, "density": 5.27, "mass": 159.69,
    "bulk_modulus": 200.0,
    "dp_n": None, "dp_p": None,
}

MATHUB3D_AL2O3_ENTRY = {
    "_id": "67890",
    "name": "icsd-100002-Al2O3",
    "folder": "icsd-100002",
    "formula": "Al2O3",
    "elements": ["Al", "O"],
    "nelements": 2,
    "spacegroup": 167,
    "spacegroup_type": "R-3c",
    "before_a": 4.759, "before_b": 4.759, "before_c": 12.993,
    "before_alpha": 90.0, "before_beta": 90.0, "before_gamma": 120.0,
    "after_a": 4.80, "after_b": 4.80, "after_c": 13.10,
    "after_alpha": 90.0, "after_beta": 90.0, "after_gamma": 120.0,
    "energy": -55.0, "energy_per_atom": -5.5,
    "gap": 6.3, "efermi": 1.5, "vbm": None, "cbm": None,
    "is_magnetic": False, "total_magnetic_moment": 0.0,
    "natoms": 10, "volume": 260.0, "density": 3.95, "mass": 101.96,
    "bulk_modulus": 252.0,
    "dp_n": None, "dp_p": None,
}

MATHUB3D_NI_ENTRY = {
    "_id": "11111",
    "name": "icsd-100003-Ni3Sn1",
    "folder": "icsd-100003",
    "formula": "Ni3Sn",
    "elements": ["Ni", "Sn"],
    "nelements": 2,
    "spacegroup": 194,
    "spacegroup_type": "P6_3/mmc",
    "before_a": 5.28, "before_b": 5.28, "before_c": 4.24,
    "before_alpha": 90.0, "before_beta": 90.0, "before_gamma": 120.0,
    "after_a": None, "after_b": None, "after_c": None,
    "after_alpha": None, "after_beta": None, "after_gamma": None,
    "energy": None, "energy_per_atom": None,
    "gap": 0.0, "efermi": None,
    "is_magnetic": True, "total_magnetic_moment": 2.5,
    "natoms": None, "volume": None, "density": None, "mass": None,
    "bulk_modulus": None,
    "dp_n": None, "dp_p": None,
}
