"""Integration tests for the PddPredictor entry points (predict and screen)."""

from pathlib import Path

import amd
import numpy as np
import pytest
from pymatgen.io.cif import CifParser

from Information_Units.Predictors.Pdd.PddPredictor import PddPredictor

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "cif_files"
CIF_TEXT = (FIXTURES / "mp" / "mp-2229.cif").read_text(encoding="utf-8")


def test_predict_returns_weighted_amd_and_pdd_with_weights_column():
    k = 20
    output = PddPredictor(k=k).predict([CIF_TEXT])
    result = output["results"][0]
    assert result["status"] == "ok"
    vector = np.asarray(result["properties"]["pdd_vector"])
    matrix = np.asarray(result["properties"]["pdd_matrix"])
    assert vector.shape == (k,)
    assert matrix.shape[1] == k + 1  # column 0 = row weights
    assert abs(matrix[:, 0].sum() - 1.0) < 1e-9

    structure = CifParser.from_str(CIF_TEXT, frac_tolerance=0).parse_structures(primitive=False)[0]
    expected = amd.AMD(amd.PeriodicSet(structure.cart_coords, structure.lattice.matrix), k)
    assert np.allclose(vector, expected, atol=1e-3)


def test_predict_keeps_the_emos_output_contract():
    output = PddPredictor(k=5).predict([CIF_TEXT, "not a cif"])
    assert output["source"] == "pdd" and len(output["results"]) == 2
    assert [r["status"] for r in output["results"]] == ["ok", "error"]
    assert output["results"][1]["error"]


def test_screen_accepts_a_plain_dict_and_returns_a_json_safe_summary(tmp_path):
    summary = PddPredictor().screen(
        {
            "input_dirs": [str(FIXTURES / "mp")],
            "output_dir": str(tmp_path),
            "k_amd": 5,
            "k_pdd": 10,
            "k_max": 10,
            "tau": 0.1,
        }
    )
    assert summary["stage_counts"]["n_structures"] == len(list((FIXTURES / "mp").glob("*.cif")))
    assert Path(summary["run_dir"], "run_info.json").exists()
