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
