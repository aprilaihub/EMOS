"""
Integration tests for MatterGen generator with real Docker container calls.

These tests call the actual MatterGen Docker container API (port 8100) and
verify real-world behaviour, mirroring the pattern used by Alexandria and COD
integration tests.  The container must be running:

    docker compose up mattergen --build

Markers:
    @pytest.mark.integration — always applied
    @pytest.mark.network     — requires live container
    @pytest.mark.slow        — generation tests may take minutes on CPU

Run with:  pytest tests/integration/test_mattergen_integration.py -v
Skip slow:  pytest tests/integration/test_mattergen_integration.py -v -m "not slow"

Test plan
---------
1. Container reachability (health, info, available models)
2. Demo generation — full round-trip through /demo/generate; validates
   response shape, CIF content, and pymatgen structure dict.
3. Demo generation via the host-side MattergenGenerator (same as real path).
4. Demo generation via the Flask /api/process/<id> endpoint (full stack).
5. Demo streaming via the Flask /api/process/<id>/stream endpoint.
6. Real unconditional generation START — sends a real /generate/stream
   request with batch_size=1 to mattergen_base, asserts that SSE log
   and progress events arrive within a reasonable time, then closes the
   connection (does NOT wait for full generation to complete).
7. Real conditional generation START — same approach with the
   dft_band_gap model and a target band-gap property, verifying that
   the container accepts conditional payloads and begins streaming.
8. Feature factory wiring, toggle endpoint, interface contract.
9. Error-handling for unknown feature IDs.


1	TestContainerReachability (6 tests)	Real calls to /health, /info endpoints + MattergenGenerator.is_healthy(), .get_available_models(), .info()	PASS: Container returns status: ok, lists ≥1 models including mattergen_base and dft_band_gap, info string contains live metadata (not fallback). FAIL: Connection refused, missing models, or fallback string.	
2	TestDemoGenerationDirect (6 tests)	Real POST /demo/generate to container — validates response shape, structure dicts, CIF format, element content (Cs/Sr/I), debug_logs, and /results/{job_id} retrieval	PASS: status completed, num_structures ≥ 1, CIF has data_, _cell_length_a, _atom_site, expected elements. FAIL: Missing fields, malformed CIF, or job ID not retrievable.	
3	TestDemoGenerationViaGenerator (2 tests)	MattergenGenerator.generate() and .generate_stream() with pretrained_name='demo' — exercises the host-side client talking to the real container	PASS: Sync returns completed + CIF strings; stream yields result and done events with completed status. FAIL: Error status or missing events.	
4	TestDemoGenerationViaFlask (5 tests)	Full stack: Flask test client → /api/process/<id> and /api/process/<id>/stream → Feature → Generator → Docker container, using demo model	PASS: 200 response, result has generation_results.mattergen with structures; stream has event: result + event: done; correct Cache-Control: no-cache headers. FAIL: Non-200, missing generation data, wrong headers.	
5	TestRealUnconditionalGenerationStart (1 test, @slow)	Real POST /generate/stream with mattergen_base, batch_size=1 — verifies stream opens, ≥3 log events arrive (job creation, model loading), and at least 1 progress event arrives (diffusion started). Closes connection early.	PASS: Log messages include lifecycle events AND progress event received. FAIL: Timeout before logs or progress — container may be stuck or model failed to load.	
6	TestRealConditionalGenerationStart (1 test, @slow)	Real POST /generate/stream with dft_band_gap model + properties_to_condition_on: {dft_band_gap: 2.0} — same approach: verifies logs mention conditioning/properties AND progress event arrives.	PASS: Conditioning acknowledged in logs AND progress event received. FAIL: Timeout, or no conditioning message — container may reject conditional payload.	
7	TestFeatureFactoryWiring (3 tests)	Feature factory creates MaterialGenerationFeature, has process_feature_stream(), toggle endpoint activates/deactivates generator in registry	PASS: Feature created, streaming method callable, toggle 200s. FAIL: ValueError, missing method, or toggle errors.	
8	TestGeneratorInterfaceContract (2 tests)	MattergenGenerator has all required BaseGenerator methods, info() returns non-empty string	PASS: All methods callable, non-empty string. FAIL: Missing method or empty result.	
9	TestErrorHandling (5 tests)	Flask health, unknown feature 404, unknown feature stream error event, container rejects invalid payload (400/422), unknown job ID 404	PASS: Correct HTTP status codes and SSE error events. FAIL: Wrong status codes or crashes.	
"""

import json
import time

import pytest
import requests as http_requests  # alias to avoid conflict with pytest-requests

import sys
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import app, logger as app_logger

# ---------------------------------------------------------------------------
# Configuration — matches MattergenGenerator defaults
# ---------------------------------------------------------------------------
MATTERGEN_API_URL = "http://localhost:8100"

# How long to wait (seconds) before concluding the container is down
_HEALTH_TIMEOUT = 10

# How long to watch a real generation stream before declaring "it started"
_STREAM_START_TIMEOUT = 120  # model loading can take up to ~60s on first call


# ============================================================================
# Helpers
# ============================================================================

def _container_is_healthy() -> bool:
    """Return True if the MatterGen container is reachable."""
    try:
        resp = http_requests.get(f"{MATTERGEN_API_URL}/health", timeout=_HEALTH_TIMEOUT)
        return resp.status_code == 200
    except Exception:
        return False


def _find_material_generation_feature_id():
    """Return the FeatureFactory ID for MaterialGeneration, or None."""
    from Features.FeatureFactory import get_available_features, get_feature_info
    for fid in get_available_features():
        try:
            if "Material Generation" in str(get_feature_info(fid)):
                return fid
        except Exception:
            continue
    return None


def _parse_sse_blocks(body: str) -> list[dict]:
    """Parse an SSE text body into a list of {event, **data} dicts."""
    blocks = body.split("\n\n")
    parsed = []
    for block in blocks:
        lines = block.strip().split("\n")
        event_type = "log"
        data_str = ""
        for line in lines:
            if line.startswith("event: "):
                event_type = line[7:].strip()
            elif line.startswith("data: "):
                data_str += line[6:]
        if data_str:
            try:
                data = json.loads(data_str)
                if isinstance(data, dict):
                    data["event"] = event_type
                    parsed.append(data)
                else:
                    parsed.append({"event": event_type, "data": data})
            except json.JSONDecodeError:
                parsed.append({"event": event_type, "raw": data_str})
    return parsed


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def _clear_logger():
    """Clear app logger between tests."""
    app_logger.clear_logs()


@pytest.fixture(autouse=True)
def _clear_health_cache():
    """Reset health cache so every test starts with a fresh check."""
    from Information_Units.Generators.Mattergen.MattergenGenerator import MattergenGenerator
    MattergenGenerator._health_cache = {"healthy": None, "checked_at": 0.0}
    yield
    MattergenGenerator._health_cache = {"healthy": None, "checked_at": 0.0}


@pytest.fixture
def _register_mattergen():
    """Ensure mattergen is in the generator_registry so the feature can find it."""
    from Information_Units.Generators.GeneratorFactory import generator_registry
    from Information_Units.Generators.Mattergen.MattergenGenerator import MattergenGenerator

    gen = MattergenGenerator(generator_name="mattergen", logger=app_logger)
    generator_registry["mattergen"] = gen
    yield gen
    generator_registry.pop("mattergen", None)


# ============================================================================
# 1. Container reachability
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
class TestContainerReachability:
    """Tests that the MatterGen Docker container is up and its metadata
    endpoints return correct data."""

    def test_health_endpoint(self):
        """GET /health returns 200 with status 'ok'.

        PASS: HTTP 200, JSON body has status == 'ok' and service == 'mattergen'.
        FAIL: connection refused, timeout, or unexpected payload.
        """
        resp = http_requests.get(f"{MATTERGEN_API_URL}/health", timeout=_HEALTH_TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "mattergen"

    def test_info_endpoint_metadata(self):
        """GET /info returns model metadata with expected keys and models.

        PASS: JSON has name, version, pretrained_models (list ≥ 1),
              capabilities (list ≥ 1).
        FAIL: missing keys or empty lists.
        """
        resp = http_requests.get(f"{MATTERGEN_API_URL}/info", timeout=_HEALTH_TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "MatterGen"
        assert "version" in data
        models = data["pretrained_models"]
        assert isinstance(models, list) and len(models) >= 1
        assert "mattergen_base" in models
        caps = data["capabilities"]
        assert isinstance(caps, list) and len(caps) >= 1
        assert "unconditional_generation" in caps

    def test_info_lists_conditional_models(self):
        """GET /info lists at least one property-conditioned model.

        PASS: pretrained_models contains 'dft_band_gap'.
        FAIL: conditional model missing — conditional generation tests will fail.
        """
        resp = http_requests.get(f"{MATTERGEN_API_URL}/info", timeout=_HEALTH_TIMEOUT)
        data = resp.json()
        assert "dft_band_gap" in data["pretrained_models"]

    def test_generator_is_healthy(self):
        """MattergenGenerator.is_healthy() returns True when container is up.

        PASS: is_healthy() == True.
        FAIL: returns False — container may be down.
        """
        from Information_Units.Generators.Mattergen.MattergenGenerator import MattergenGenerator
        gen = MattergenGenerator()
        assert gen.is_healthy() is True

    def test_generator_get_available_models(self):
        """MattergenGenerator.get_available_models() returns real model list.

        PASS: non-empty list containing 'mattergen_base'.
        FAIL: empty list or exception.
        """
        from Information_Units.Generators.Mattergen.MattergenGenerator import MattergenGenerator
        gen = MattergenGenerator()
        models = gen.get_available_models()
        assert isinstance(models, list) and len(models) >= 1
        assert "mattergen_base" in models

    def test_generator_info_returns_live_metadata(self):
        """MattergenGenerator.info() returns metadata from the live container
        (not the fallback string).

        PASS: info string contains 'MatterGen v' and 'Pretrained models:'.
        FAIL: contains 'container unreachable' — container is down.
        """
        from Information_Units.Generators.Mattergen.MattergenGenerator import MattergenGenerator
        gen = MattergenGenerator()
        info = gen.info()
        assert "MatterGen v" in info, f"Got fallback info: {info[:80]}"
        assert "Pretrained models:" in info


# ============================================================================
# 2. Demo generation — direct container call
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
class TestDemoGenerationDirect:
    """Tests that hit the container's /demo/generate endpoint directly.
    These are fast (no model loading, no diffusion) and validate the
    response shape, CIF content, and structure dictionaries."""

    def test_demo_returns_completed_status(self):
        """POST /demo/generate returns status 'completed'.

        PASS: status == 'completed', job_id is non-empty.
        FAIL: status != 'completed' or missing fields.
        """
        resp = http_requests.post(f"{MATTERGEN_API_URL}/demo/generate", timeout=30)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["job_id"]
        assert data["num_structures"] >= 1

    def test_demo_response_has_structures(self):
        """POST /demo/generate returns at least one pymatgen structure dict.

        PASS: 'structures' list is non-empty, each entry has 'lattice' key.
        FAIL: empty list or malformed structure.
        """
        resp = http_requests.post(f"{MATTERGEN_API_URL}/demo/generate", timeout=30)
        data = resp.json()
        structs = data["structures"]
        assert isinstance(structs, list) and len(structs) >= 1
        for s in structs:
            assert "lattice" in s, "Structure dict missing 'lattice' key"

    def test_demo_response_has_valid_cif(self):
        """POST /demo/generate returns CIF strings with valid crystal data.

        PASS: each CIF string contains 'data_', '_cell_length_a', and
              '_atom_site' (basic CIF format validation).
        FAIL: missing CIF markers or empty strings.
        """
        resp = http_requests.post(f"{MATTERGEN_API_URL}/demo/generate", timeout=30)
        data = resp.json()
        cifs = data["cif_strings"]
        assert isinstance(cifs, list) and len(cifs) >= 1
        for cif in cifs:
            assert "data_" in cif, "CIF missing data block"
            assert "_cell_length_a" in cif, "CIF missing lattice parameter a"
            assert "_atom_site" in cif, "CIF missing atom site information"

    def test_demo_cif_contains_expected_elements(self):
        """Demo structure (CsSrI3) CIF contains Cs, Sr, and I.

        PASS: all three elements appear in the CIF text.
        FAIL: missing element — structure may have changed.
        """
        resp = http_requests.post(f"{MATTERGEN_API_URL}/demo/generate", timeout=30)
        data = resp.json()
        cif = data["cif_strings"][0]
        for elem in ("Cs", "Sr", "I"):
            assert elem in cif, f"Element {elem} not found in demo CIF"

    def test_demo_returns_debug_logs(self):
        """POST /demo/generate includes debug_logs.

        PASS: debug_logs is a non-empty list of strings.
        FAIL: missing or empty — logging pipeline broken.
        """
        resp = http_requests.post(f"{MATTERGEN_API_URL}/demo/generate", timeout=30)
        data = resp.json()
        assert isinstance(data["debug_logs"], list) and len(data["debug_logs"]) >= 1
        assert any("Demo" in log or "demo" in log.lower() for log in data["debug_logs"])

    def test_demo_result_retrievable_by_job_id(self):
        """GET /results/<job_id> returns the same demo result after generation.

        PASS: same job_id, status 'completed', same num_structures.
        FAIL: 404 or mismatched data — job store not persisting.
        """
        gen_resp = http_requests.post(f"{MATTERGEN_API_URL}/demo/generate", timeout=30)
        job_id = gen_resp.json()["job_id"]

        poll_resp = http_requests.get(f"{MATTERGEN_API_URL}/results/{job_id}", timeout=10)
        assert poll_resp.status_code == 200
        poll_data = poll_resp.json()
        assert poll_data["job_id"] == job_id
        assert poll_data["status"] == "completed"
        assert poll_data["num_structures"] == gen_resp.json()["num_structures"]


# ============================================================================
# 3. Demo generation — through MattergenGenerator (host-side client)
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
class TestDemoGenerationViaGenerator:
    """Tests that exercise the full MattergenGenerator.generate() and
    generate_stream() code paths using the demo shortcut, which calls
    the real container but returns instantly."""

    def test_sync_generate_demo(self):
        """MattergenGenerator.generate(pretrained_name='demo') returns
        a completed result via the container /demo/generate endpoint.

        PASS: status 'completed', num_structures >= 1, CIF strings present.
        FAIL: status 'error' or missing structure data.
        """
        from Information_Units.Generators.Mattergen.MattergenGenerator import MattergenGenerator
        gen = MattergenGenerator(generator_name="mattergen", logger=app_logger)
        result = gen.generate({"pretrained_name": "demo"})
        assert result["status"] == "completed"
        assert result["num_structures"] >= 1
        assert "structures" in result
        assert "cif_strings" in result
        assert len(result["cif_strings"]) >= 1

    def test_stream_generate_demo_yields_result(self):
        """MattergenGenerator.generate_stream(pretrained_name='demo') yields
        log, result, and done events.

        PASS: at least one 'result' event with status 'completed'.
        FAIL: no result event or status != 'completed'.
        """
        from Information_Units.Generators.Mattergen.MattergenGenerator import MattergenGenerator
        gen = MattergenGenerator(generator_name="mattergen", logger=app_logger)
        events = list(gen.generate_stream({"pretrained_name": "demo"}))

        event_types = [e["event"] for e in events]
        assert "result" in event_types, f"No result event, got: {event_types}"
        assert "done" in event_types

        result_evt = next(e for e in events if e["event"] == "result")
        assert result_evt["status"] == "completed"
        assert result_evt["num_structures"] >= 1


# ============================================================================
# 4. Demo generation — full stack through Flask endpoint
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
class TestDemoGenerationViaFlask:
    """Full-stack tests: browser → Flask /api/process → Feature →
    MattergenGenerator → Docker container, using the demo model."""

    def test_sync_process_endpoint_demo(self, client, _register_mattergen):
        """POST /api/process/<id> with demo model returns completed results.

        PASS: 200 response, results.status == 'completed',
              generation_results['mattergen'] has CIF strings.
        FAIL: non-200 or missing generation data.
        """
        mat_gen_id = _find_material_generation_feature_id()
        if mat_gen_id is None:
            pytest.skip("MaterialGeneration feature not registered")

        payload = {
            "active_generators": [{"name": "MatterGen", "value": "mattergen"}],
            "generator_inputs": {"mattergen": {"pretrained_name": "demo"}},
        }
        resp = client.post(
            f"/api/process/{mat_gen_id}",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "results" in data
        results = data["results"]
        assert results["status"] == "completed"
        assert "mattergen" in results["generation_results"]
        gen_res = results["generation_results"]["mattergen"]
        assert gen_res["num_structures"] >= 1
        assert "cif_strings" in gen_res

    def test_sync_process_returns_logs(self, client, _register_mattergen):
        """POST /api/process/<id> with demo model returns accumulated logs.

        PASS: response 'logs' array is non-empty.
        FAIL: logs missing or empty.
        """
        mat_gen_id = _find_material_generation_feature_id()
        if mat_gen_id is None:
            pytest.skip("MaterialGeneration feature not registered")

        payload = {
            "active_generators": [{"name": "MatterGen", "value": "mattergen"}],
            "generator_inputs": {"mattergen": {"pretrained_name": "demo"}},
        }
        resp = client.post(
            f"/api/process/{mat_gen_id}",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = resp.get_json()
        assert "logs" in data
        assert len(data["logs"]) > 0

    def test_stream_endpoint_demo_returns_sse(self, client, _register_mattergen):
        """POST /api/process/<id>/stream with demo model returns SSE events.

        PASS: Content-Type is text/event-stream, body contains 'event: result'
              and 'event: done'.
        FAIL: wrong content type or missing events.
        """
        mat_gen_id = _find_material_generation_feature_id()
        if mat_gen_id is None:
            pytest.skip("MaterialGeneration feature not registered")

        payload = {
            "active_generators": [{"name": "MatterGen", "value": "mattergen"}],
            "generator_inputs": {"mattergen": {"pretrained_name": "demo"}},
        }
        resp = client.post(
            f"/api/process/{mat_gen_id}/stream",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type

        body = resp.get_data(as_text=True)
        assert "event: result" in body
        assert "event: done" in body

    def test_stream_endpoint_demo_result_has_structures(self, client, _register_mattergen):
        """The result SSE block from the demo stream contains structure data.

        PASS: result event has generation_results.mattergen with structures.
        FAIL: result payload malformed or missing structures.
        """
        mat_gen_id = _find_material_generation_feature_id()
        if mat_gen_id is None:
            pytest.skip("MaterialGeneration feature not registered")

        payload = {
            "active_generators": [{"name": "MatterGen", "value": "mattergen"}],
            "generator_inputs": {"mattergen": {"pretrained_name": "demo"}},
        }
        resp = client.post(
            f"/api/process/{mat_gen_id}/stream",
            data=json.dumps(payload),
            content_type="application/json",
        )
        body = resp.get_data(as_text=True)
        events = _parse_sse_blocks(body)
        result_events = [e for e in events if e.get("event") == "result"]
        assert len(result_events) >= 1, "No result event in SSE stream"
        result = result_events[0]
        assert result["status"] == "completed"
        assert "generation_results" in result
        gen_res = result["generation_results"]["mattergen"]
        assert gen_res["num_structures"] >= 1

    def test_stream_endpoint_keepalive_headers(self, client, _register_mattergen):
        """Streaming endpoint sets correct Cache-Control headers.

        PASS: Cache-Control contains 'no-cache'.
        FAIL: caching headers allow buffering.
        """
        mat_gen_id = _find_material_generation_feature_id()
        if mat_gen_id is None:
            pytest.skip("MaterialGeneration feature not registered")

        resp = client.post(
            f"/api/process/{mat_gen_id}/stream",
            data=json.dumps({
                "active_generators": [{"name": "MatterGen", "value": "mattergen"}],
                "generator_inputs": {"mattergen": {"pretrained_name": "demo"}},
            }),
            content_type="application/json",
        )
        assert "no-cache" in resp.headers.get("Cache-Control", "")


# ============================================================================
# 5. Real unconditional generation START (mattergen_base)
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
class TestRealUnconditionalGenerationStart:
    """Send a real generation request to the container with the base model
    (unconditional, batch_size=1).  We do NOT wait for the full generation
    to complete (it can take 5–15 min on CPU).  Instead we verify that:
      - The SSE stream opens successfully
      - Initial log events arrive (model loading, job creation)
      - At least one progress event arrives (diffusion steps starting)
    Then we close the connection.

    Uses a single HTTP request to avoid overloading the container with
    concurrent CPU-bound generation threads.
    """

    def test_stream_starts_and_receives_progress(self):
        """POST /generate/stream with mattergen_base streams log events
        followed by at least one progress event.

        PASS: ≥3 log messages arrive (including job/model lifecycle messages)
              AND at least one 'event: progress' block is received, confirming
              the diffusion process has started.
        FAIL: timeout before receiving log or progress events.
        """
        payload = {
            "pretrained_name": "mattergen_base",
            "batch_size": 1,
            "num_batches": 1,
        }
        with http_requests.post(
            f"{MATTERGEN_API_URL}/generate/stream",
            json=payload,
            stream=True,
            timeout=_STREAM_START_TIMEOUT,
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")

            log_messages = []
            found_progress = False
            current_event = "log"
            lines_seen = 0

            for raw_line in resp.iter_lines(decode_unicode=True):
                if raw_line is None:
                    continue
                lines_seen += 1

                if raw_line.startswith("event: "):
                    current_event = raw_line[7:].strip()
                    continue

                if raw_line.startswith("data: "):
                    try:
                        data = json.loads(raw_line[6:])
                        if current_event == "log" and "message" in data:
                            log_messages.append(data["message"])
                        if current_event == "progress" or "progress" in data:
                            found_progress = True
                    except json.JSONDecodeError:
                        pass

                # Once we have both log evidence AND a progress event, stop
                if found_progress and len(log_messages) >= 3:
                    break

                # Safety limit: don't spin forever
                if lines_seen > 200:
                    break

            # Assert log messages arrived
            assert len(log_messages) >= 3, (
                f"Expected ≥3 log messages, got {len(log_messages)}: {log_messages}"
            )
            combined = " ".join(log_messages).lower()
            assert "job" in combined or "starting" in combined, (
                f"No job/starting message in: {log_messages}"
            )

            # Assert progress event arrived
            assert found_progress, (
                f"No progress event received after {lines_seen} lines — "
                "diffusion may not have started"
            )


# ============================================================================
# 6. Real conditional generation START (dft_band_gap model)
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
class TestRealConditionalGenerationStart:
    """Send a real conditional generation request: use the dft_band_gap model
    and condition on a target band gap of 2.0 eV.  Like the unconditional
    test, we only wait for the stream to start (log + progress events) and
    then close — we do NOT wait for full completion.

    Uses a single HTTP request to avoid overloading the container.
    """

    def test_conditional_stream_starts_and_receives_progress(self):
        """POST /generate/stream with dft_band_gap model and
        properties_to_condition_on={'dft_band_gap': 2.0} streams log events
        (including conditioning acknowledgement) and then a progress event.

        PASS: ≥3 log messages arrive, at least one mentions conditioning
              or the property name, AND at least one progress event arrives.
        FAIL: timeout, HTTP error, or container rejects the payload.
        """
        payload = {
            "pretrained_name": "dft_band_gap",
            "batch_size": 1,
            "num_batches": 1,
            "properties_to_condition_on": {"dft_band_gap": 2.0},
        }
        with http_requests.post(
            f"{MATTERGEN_API_URL}/generate/stream",
            json=payload,
            stream=True,
            timeout=_STREAM_START_TIMEOUT,
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")

            log_messages = []
            found_progress = False
            current_event = "log"
            lines_seen = 0

            for raw_line in resp.iter_lines(decode_unicode=True):
                if raw_line is None:
                    continue
                lines_seen += 1

                if raw_line.startswith("event: "):
                    current_event = raw_line[7:].strip()
                    continue

                if raw_line.startswith("data: "):
                    try:
                        data = json.loads(raw_line[6:])
                        if current_event == "log" and "message" in data:
                            log_messages.append(data["message"])
                        if current_event == "progress" or "progress" in data:
                            found_progress = True
                    except json.JSONDecodeError:
                        pass

                # Once we have both log evidence AND a progress event, stop
                if found_progress and len(log_messages) >= 3:
                    break

                if lines_seen > 200:
                    break

            # Assert log messages arrived
            assert len(log_messages) >= 3, (
                f"Expected ≥3 log messages, got {len(log_messages)}: {log_messages}"
            )
            combined = " ".join(log_messages).lower()
            assert "conditioning" in combined or "dft_band_gap" in combined or "properties" in combined, (
                f"No conditioning-related message in: {log_messages}"
            )

            # Assert progress event arrived
            assert found_progress, (
                f"No progress event from conditional generation after {lines_seen} lines"
            )


# ============================================================================
# 7. Feature factory wiring
# ============================================================================

@pytest.mark.integration
class TestFeatureFactoryWiring:
    """Tests that the Feature architecture correctly wires up
    MaterialGenerationFeature and MattergenGenerator."""

    def test_feature_factory_creates_material_generation(self):
        """FeatureFactory can create a MaterialGenerationFeature instance.

        PASS: create_feature returns a feature whose info() mentions
              'Material Generation'.
        FAIL: ValueError or wrong type.
        """
        from Features.FeatureFactory import create_feature
        mat_gen_id = _find_material_generation_feature_id()
        if mat_gen_id is None:
            pytest.skip("MaterialGeneration feature not registered")
        feature = create_feature(mat_gen_id, app_logger)
        assert feature is not None
        assert "Material Generation" in feature.info()

    def test_feature_has_streaming_support(self):
        """MaterialGenerationFeature exposes process_feature_stream().

        PASS: hasattr True and callable.
        FAIL: method missing — SSE streaming will not work.
        """
        from Features.FeatureFactory import create_feature
        mat_gen_id = _find_material_generation_feature_id()
        if mat_gen_id is None:
            pytest.skip("MaterialGeneration feature not registered")
        feature = create_feature(mat_gen_id, app_logger)
        assert hasattr(feature, "process_feature_stream")
        assert callable(feature.process_feature_stream)

    def test_toggle_iu_mattergen(self, client):
        """POST /api/process/toggle_IU can activate and deactivate
        MattergenGenerator in the registry.

        PASS: activate → 200 + in registry; deactivate → 200 + not in registry.
        FAIL: 404 (not in factory) or 500.
        """
        from Information_Units.Generators.GeneratorFactory import generator_factory, generator_registry

        if "mattergen" not in generator_factory:
            pytest.skip("mattergen not registered in generator_factory")

        # Activate
        resp = client.post(
            "/api/process/toggle_IU",
            data=json.dumps({"class_name": "mattergen", "active": True, "class_type": "generator"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert "mattergen" in generator_registry

        # Deactivate
        resp = client.post(
            "/api/process/toggle_IU",
            data=json.dumps({"class_name": "mattergen", "active": False, "class_type": "generator"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert "mattergen" not in generator_registry


# ============================================================================
# 8. MattergenGenerator interface contract
# ============================================================================

@pytest.mark.integration
class TestGeneratorInterfaceContract:
    """Verify that MattergenGenerator implements the BaseGenerator interface."""

    def test_interface_methods_exist(self):
        """MattergenGenerator has info, generate, generate_stream, is_healthy,
        get_available_models.

        PASS: all methods callable.
        FAIL: missing required method.
        """
        from Information_Units.Generators.Mattergen.MattergenGenerator import MattergenGenerator
        gen = MattergenGenerator()
        assert callable(gen.info)
        assert callable(gen.generate)
        assert callable(gen.generate_stream)
        assert callable(gen.is_healthy)
        assert callable(gen.get_available_models)

    def test_info_returns_non_empty_string(self):
        """MattergenGenerator.info() returns a non-empty string.

        PASS: non-empty string.
        FAIL: exception or empty string.
        """
        from Information_Units.Generators.Mattergen.MattergenGenerator import MattergenGenerator
        gen = MattergenGenerator()
        result = gen.info()
        assert isinstance(result, str)
        assert len(result) > 0


# ============================================================================
# 9. Error handling — unknown feature ID
# ============================================================================

@pytest.mark.integration
class TestErrorHandling:
    """Tests for error conditions and graceful degradation."""

    def test_flask_health(self, client):
        """Flask /api/health returns 200 OK.

        PASS: status 200, body has status 'ok'.
        FAIL: non-200 or missing status.
        """
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_process_unknown_feature_returns_404(self, client):
        """POST /api/process/99999 returns 404 for unknown feature ID.

        PASS: status code 404.
        FAIL: 200 or 500.
        """
        resp = client.post(
            "/api/process/99999",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_stream_unknown_feature_returns_error_event(self, client):
        """POST /api/process/99999/stream returns SSE error event.

        PASS: body contains 'event: error' and 'event: done'.
        FAIL: 500 or crash.
        """
        resp = client.post(
            "/api/process/99999/stream",
            data=json.dumps({}),
            content_type="application/json",
        )
        body = resp.get_data(as_text=True)
        assert "event: error" in body
        assert "event: done" in body

    @pytest.mark.network
    def test_container_rejects_invalid_payload(self):
        """POST /generate with no model name or path returns 400.

        PASS: HTTP 400 with detail message.
        FAIL: 200 (accepted invalid input) or 500 (unhandled crash).
        """
        resp = http_requests.post(
            f"{MATTERGEN_API_URL}/generate",
            json={"pretrained_name": None, "model_path": None},
            timeout=30,
        )
        # FastAPI returns 422 for validation errors
        assert resp.status_code in (400, 422), f"Expected 400/422, got {resp.status_code}"

    @pytest.mark.network
    def test_results_unknown_job_returns_404(self):
        """GET /results/<nonexistent> returns 404.

        PASS: HTTP 404.
        FAIL: 200 or 500.
        """
        resp = http_requests.get(
            f"{MATTERGEN_API_URL}/results/nonexistent_job_id",
            timeout=10,
        )
        assert resp.status_code == 404
