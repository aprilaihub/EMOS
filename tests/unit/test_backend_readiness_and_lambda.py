import json
from unittest.mock import patch

import pytest

import backend.app as backend
from backend.lambda_sandbox import LambdaSandboxError, run_sandboxed_lambda, validate_lambda_code


def _service_statuses(available=True):
    return {
        name: {
            "available": available,
            "service": name,
            "models": ["mattergen_base"] if name == "mattergen" else [name],
        }
        for name in ("mattergen", "mattersim", "chgnet", "gbfs", "gbfs_2d")
    }


def test_readiness_is_200_when_dependencies_are_available():
    with patch.object(backend, "_model_service_availability", return_value=_service_statuses()):
        response = backend.app.test_client().get("/api/ready")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ready"


def test_readiness_is_503_but_availability_remains_queryable():
    services = _service_statuses()
    services["gbfs"] = {
        "available": False,
        "service": "gbfs",
        "models": [],
        "error": "offline",
    }
    with patch.object(backend, "_model_service_availability", return_value=services):
        ready = backend.app.test_client().get("/api/ready")
        availability = backend.app.test_client().get("/api/availability")

    assert ready.status_code == 503
    assert availability.status_code == 200
    assert availability.get_json()["information_units"]["predictors"]["gbfs"]["available"] is False


def test_sandboxed_lambda_preserves_pipeline_contract():
    result = run_sandboxed_lambda(
        "output_cifs = [cif for cif in cif_list if cif.startswith('data_')]\n"
        "output_results = {'count': len(output_cifs)}",
        ["data_a", "skip", "data_b"],
        {},
    )
    assert result == {
        "cif_out": ["data_a", "data_b"],
        "result_out": {"count": 2},
    }


@pytest.mark.parametrize(
    "code",
    [
        "import os\noutput_results = dict(os.environ)",
        "output_results = __import__('os').environ",
        "output_results = (1).__class__.__mro__",
        "output_results = open('/etc/passwd').read()",
    ],
)
def test_lambda_rejects_environment_and_runtime_escape_paths(code):
    with pytest.raises(LambdaSandboxError):
        validate_lambda_code(code)


def test_backend_lambda_reports_sandbox_rejection_as_sse_error():
    events = list(
        backend._run_lambda(
            {"code": "import os\noutput_results = dict(os.environ)"},
            {"cif_in": [], "result_in": {}},
        )
    )
    parsed = [
        (chunk.splitlines()[0], json.loads(chunk.splitlines()[1][6:]))
        for chunk in events
    ]
    assert parsed[-1][0] == "event: error"
    assert "Import is not allowed" in parsed[-1][1]["message"]