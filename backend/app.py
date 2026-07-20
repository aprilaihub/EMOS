from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import sys
import pathlib
import json
import tempfile
import traceback
import requests
import uuid
import threading

# Get absolute paths regardless of where the script is run from
BACKEND_DIR = pathlib.Path(__file__).parent.resolve()  # /home/soe/EMOS/backend
PROJECT_ROOT = BACKEND_DIR.parent.resolve()  # /home/soe/EMOS

# Add the project root to Python path
sys.path.append(str(PROJECT_ROOT))

#information units creators & destroyers
from Information_Units.Generators.GeneratorFactory import generator_factory, generator_registry
from Information_Units.Databases.DatabaseFactory import database_factory, database_registry
from Information_Units.Predictors.PredictorFactory import predictor_factory, predictor_registry
from backend.lambda_sandbox import LambdaSandboxError, run_sandboxed_lambda

# New Feature architecture - try to import, fallback if not available
try:
    from Features.FeatureFactory import create_feature, get_available_features, get_feature_info
    NEW_FEATURE_ARCHITECTURE = True
except ImportError:
    NEW_FEATURE_ARCHITECTURE = False


app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Ensure CORS headers even on errors
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


# Simple logger class
class SimpleLogger:
    def __init__(self):
        self.logs = []
    
    def log(self, message, level='info'):
        self.logs.append({
            'level': level,
            'message': message
        })
    
    def get_logs(self):
        return self.logs
    
    def clear_logs(self):
        self.logs = []

# Create universal logger
logger = SimpleLogger()


def _instantiate_iu(cls, iu_name, logger_obj):
    """Instantiate IU classes with logger passed safely by keyword when supported."""
    try:
        return cls(iu_name, logger=logger_obj)
    except TypeError:
        # Backward-compatible fallback for constructors that only support positional args
        return cls(iu_name, logger_obj)


@app.route('/api/features/info', methods=['GET'])
def get_features_info():
    """Get information about available features and their architectures"""
    try:
        feature_info = {}
        
        if NEW_FEATURE_ARCHITECTURE:
            available_features = get_available_features()
            feature_info['new_architecture'] = {
                'available': True,
                'feature_count': len(available_features),
                'feature_ids': available_features,
                'feature_details': {}
            }
            
            # Get info for each feature
            for feature_id in available_features:
                try:
                    info = get_feature_info(feature_id)
                    feature_info['new_architecture']['feature_details'][feature_id] = info
                except Exception as e:
                    feature_info['new_architecture']['feature_details'][feature_id] = f"Error: {str(e)}"
        else:
            feature_info['new_architecture'] = {
                'available': False,
                'error': 'Feature factory import failed'
            }
        
        return jsonify(feature_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health():
    return jsonify({'status': 'ok'}), 200


def _model_service_availability():
    """Query model dependencies without running inference."""
    checks = {
        'mattergen': (generator_factory['mattergen_base_model'], 'mattergen_base_model'),
        'mattersim': (predictor_factory['mattersim'], 'mattersim'),
        'chgnet': (predictor_factory['chgnet'], 'chgnet'),
        'gbfs': (predictor_factory['gbfs'], 'gbfs'),
        'gbfs_2d': (predictor_factory['gbfs_2d'], 'gbfs_2d'),
    }
    def check_service(service_name, iu_cls, iu_name):
        try:
            instance = _instantiate_iu(iu_cls, iu_name, logger)
            return instance.availability()
        except Exception as exc:
            return {
                'available': False,
                'service': service_name,
                'models': [],
                'error': f'{type(exc).__name__}: service check failed',
            }

    services = {}
    with ThreadPoolExecutor(max_workers=len(checks), thread_name_prefix='readiness') as executor:
        futures = {
            executor.submit(check_service, service_name, iu_cls, iu_name): service_name
            for service_name, (iu_cls, iu_name) in checks.items()
        }
        for future in as_completed(futures):
            services[futures[future]] = future.result()
    return services


def _availability_payload():
    services = _model_service_availability()
    generators = {}
    mattergen = services['mattergen']
    advertised_models = set(mattergen.get('models', []))
    for key, generator_cls in generator_factory.items():
        model_name = getattr(generator_cls, 'PRETRAINED_NAME', None)
        generators[key] = {
            'available': bool(mattergen.get('available')) and (
                not model_name or not advertised_models or model_name in advertised_models
            ),
            'service': 'mattergen',
            'model': model_name,
        }

    predictors = {
        'mattersim': {'available': bool(services['mattersim'].get('available')), 'service': 'mattersim'},
        'chgnet': {'available': bool(services['chgnet'].get('available')), 'service': 'chgnet'},
        'gbfs': {'available': bool(services['gbfs'].get('available')), 'service': 'gbfs'},
        'gbfs_2d': {'available': bool(services['gbfs_2d'].get('available')), 'service': 'gbfs_2d'},
        'synthnn': {'available': True, 'service': 'local'},
    }
    all_dependencies_available = all(
        bool(service.get('available')) for service in services.values()
    )
    return {
        'status': 'ready' if all_dependencies_available else 'degraded',
        'services': services,
        'information_units': {
            'generators': generators,
            'predictors': predictors,
        },
    }


@app.route('/api/ready', methods=['GET', 'OPTIONS'])
def readiness():
    if request.method == 'OPTIONS':
        return ('', 204)
    payload = _availability_payload()
    return jsonify(payload), 200 if payload['status'] == 'ready' else 503


@app.route('/api/availability', methods=['GET', 'OPTIONS'])
def availability():
    if request.method == 'OPTIONS':
        return ('', 204)
    return jsonify(_availability_payload()), 200


@app.route('/api/process/toggle_IU', methods=["POST", "OPTIONS"])
def toggle_IU():
    if request.method == 'OPTIONS':
        return ('', 204)
    try:
        data = request.get_json() or {}
        class_name = data.get("class_name")
        active = data.get("active")
        ui_type = data.get("class_type")
        
        if not class_name:
            return jsonify({"message": "class_name required"}), 400
        if active is None:
            return jsonify({"message": "active flag required"}), 400
        if (class_name not in generator_factory) and (class_name not in database_factory) and (class_name not in predictor_factory):
            return jsonify({"message": f"Class {class_name} not found in any factory"}), 404

        if active:
            # Instantiate and store
            if ui_type=="generator":
                cls = generator_factory[class_name]
                instance = _instantiate_iu(cls, class_name, logger)  # will raise if factory mapped to an instance
                generator_registry[class_name] = instance
            elif ui_type=="database":
                cls = database_factory[class_name]
                instance = _instantiate_iu(cls, class_name, logger)  # will raise if factory mapped to an instance
                database_registry[class_name] = instance
            elif ui_type=="predictor":
                cls = predictor_factory[class_name]
                instance = _instantiate_iu(cls, class_name, logger)  # will raise if factory mapped to an instance
                predictor_registry[class_name] = instance
            else:
                return jsonify({"message": "Unknown type"}), 400
 
            return jsonify({"message": f"{class_name} instantiated"})
        else:
            if ui_type=="generator":
                generator_registry.pop(class_name, None)
            elif ui_type=="database":
                database_registry.pop(class_name, None)
            elif ui_type=="predictor":
                predictor_registry.pop(class_name, None)
            else:
                return jsonify({"message": "Unknown type"}), 400
            
            return jsonify({"message": f"{class_name} removed"})
    except TypeError as e:
        # Most common: factory mapped to an instance, not a class
        return jsonify({"message": f"Instantiation failed for {class_name}: {e}"}), 500
    except Exception as e:
        return jsonify({"message": f"Toggle failed: {e}"}), 500


@app.route('/api/process/<int:feature_id>', methods=['POST'])
def process_feature(feature_id):
    try:
        # Clear previous logs at the start of each request
        logger.clear_logs()
        
        # Get input data
        input_data = request.json or {}
        
        # Use new Feature architecture (processor.py files have been removed)
        if NEW_FEATURE_ARCHITECTURE:
            print(f"Using Feature architecture for feature {feature_id}")
            feature = create_feature(str(feature_id), logger)
            results = feature.process(input_data)
            
            return jsonify({
                'results': results,
                'logs': logger.get_logs(),
                'architecture': 'feature_class'
            })
        else:
            return jsonify({'error': 'Feature architecture not available'}), 500
        
    except ValueError as e:
        print(f"Feature {feature_id} not found: {str(e)}")
        return jsonify({'error': f'Feature {feature_id} not found'}), 404
    except Exception as e:
        print(f"Error in process_feature: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/process/iu/<iu_type>/<iu_id>', methods=['POST', 'OPTIONS'])
def process_information_unit(iu_type, iu_id):
    """Execute a single Information Unit with predefined contract semantics."""
    if request.method == 'OPTIONS':
        return ('', 204)

    try:
        logger.clear_logs()
        inputs = request.json or {}

        if iu_type == 'database':
            cls = database_factory.get(iu_id)
            if cls is None:
                return jsonify({'error': f'Unknown database IU: {iu_id}'}), 404

            # Reuse active instance if toggled on; otherwise instantiate transiently.
            instance = database_registry.get(iu_id)
            if instance is None:
                instance = _instantiate_iu(cls, iu_id, logger)

            results = instance.retrieve(inputs)
            return jsonify({
                'results': results,
                'logs': logger.get_logs(),
                'iu_type': iu_type,
                'iu_id': iu_id,
            })

        if iu_type == 'generator':
            cls = generator_factory.get(iu_id)
            if cls is None:
                return jsonify({'error': f'Unknown generator IU: {iu_id}'}), 404

            instance = generator_registry.get(iu_id)
            if instance is None:
                instance = _instantiate_iu(cls, iu_id, logger)

            if not hasattr(instance, 'generate'):
                return jsonify({'error': f'Generator IU {iu_id} does not expose generate()'}), 400

            results = instance.generate(inputs)
            return jsonify({
                'results': results,
                'logs': logger.get_logs(),
                'iu_type': iu_type,
                'iu_id': iu_id,
            })

        if iu_type == 'predictor':
            cls = predictor_factory.get(iu_id)
            if cls is None:
                return jsonify({'error': f'Unknown predictor IU: {iu_id}'}), 404

            instance = predictor_registry.get(iu_id)
            if instance is None:
                instance = _instantiate_iu(cls, iu_id, logger)

            if not hasattr(instance, 'predict'):
                return jsonify({'error': f'Predictor IU {iu_id} does not expose predict()'}), 400

            # Extract CIF strings from input
            cif_strings = inputs.get('cif_strings', [])
            if not cif_strings:
                return jsonify({'error': 'No CIF strings provided for prediction'}), 400

            results = instance.predict(cif_strings)
            return jsonify({
                'results': results,
                'logs': logger.get_logs(),
                'iu_type': iu_type,
                'iu_id': iu_id,
            })

        return jsonify({'error': f'Unsupported iu_type: {iu_type}'}), 400

    except Exception as e:
        print(f"Error in process_information_unit ({iu_type}/{iu_id}): {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/process/iu/<iu_type>/<iu_id>/stream', methods=['POST', 'OPTIONS'])
def process_information_unit_stream(iu_type, iu_id):
    """SSE streaming endpoint for Information Units.
    
    Yields SSE events as the IU processes:
    * ``event: log``     — ``{"message": "...", "level": "info"}``
    * ``event: progress`` — progress updates from streaming generators
    * ``event: result``  — final result payload
    * ``event: done``    — stream end
    """
    if request.method == 'OPTIONS':
        return ('', 204)

    try:
        logger.clear_logs()
        inputs = request.json or {}

        def _generate_sse():
            """Yield SSE blocks from the IU's streaming processor."""
            try:
                if iu_type == 'generator':
                    cls = generator_factory.get(iu_id)
                    if cls is None:
                        yield f"event: error\ndata: {json.dumps({'message': f'Unknown generator IU: {iu_id}'})}\n\n"
                        yield f"event: done\ndata: {json.dumps({'message': 'Stream ended'})}\n\n"
                        return

                    instance = generator_registry.get(iu_id)
                    if instance is None:
                        instance = _instantiate_iu(cls, iu_id, logger)

                    # Check if generator supports streaming
                    if hasattr(instance, 'generate_stream'):
                        # Use streaming generator
                        for sse_event in instance.generate_stream(inputs):
                            event_type = sse_event.get('event', 'log')
                            yield f"event: {event_type}\ndata: {json.dumps(sse_event)}\n\n"
                    else:
                        # Fallback to sync
                        yield f"event: log\ndata: {json.dumps({'message': 'No streaming support, using synchronous generation...', 'level': 'info'})}\n\n"
                        results = instance.generate(inputs)
                        results['event'] = 'result'
                        yield f"event: result\ndata: {json.dumps(results)}\n\n"

                elif iu_type == 'database':
                    cls = database_factory.get(iu_id)
                    if cls is None:
                        yield f"event: error\ndata: {json.dumps({'message': f'Unknown database IU: {iu_id}'})}\n\n"
                        yield f"event: done\ndata: {json.dumps({'message': 'Stream ended'})}\n\n"
                        return

                    instance = database_registry.get(iu_id)
                    if instance is None:
                        instance = _instantiate_iu(cls, iu_id, logger)

                    # Databases don't typically stream, so sync only
                    results = instance.retrieve(inputs)
                    results['event'] = 'result'
                    yield f"event: result\ndata: {json.dumps(results)}\n\n"

                elif iu_type == 'predictor':
                    cls = predictor_factory.get(iu_id)
                    if cls is None:
                        yield f"event: error\ndata: {json.dumps({'message': f'Unknown predictor IU: {iu_id}'})}\n\n"
                        yield f"event: done\ndata: {json.dumps({'message': 'Stream ended'})}\n\n"
                        return

                    instance = predictor_registry.get(iu_id)
                    if instance is None:
                        instance = _instantiate_iu(cls, iu_id, logger)

                    # Extract CIF strings from input
                    cif_strings = inputs.get('cif_strings', [])
                    if not cif_strings:
                        yield f"event: error\ndata: {json.dumps({'message': 'No CIF strings provided for prediction'})}\n\n"
                        yield f"event: done\ndata: {json.dumps({'message': 'Stream ended'})}\n\n"
                        return

                    # Predictors can stream or be sync
                    if hasattr(instance, 'predict_stream'):
                        # Use streaming predictor
                        for sse_event in instance.predict_stream(cif_strings):
                            event_type = sse_event.get('event', 'log')
                            yield f"event: {event_type}\ndata: {json.dumps(sse_event)}\n\n"
                    else:
                        # Fallback to sync
                        yield f"event: log\ndata: {json.dumps({'message': 'Running predictions...', 'level': 'info'})}\n\n"
                        results = instance.predict(cif_strings)
                        results['event'] = 'result'
                        yield f"event: result\ndata: {json.dumps(results)}\n\n"

                else:
                    yield f"event: error\ndata: {json.dumps({'message': f'Unsupported iu_type: {iu_type}'})}\n\n"

            except Exception as exc:
                print(f"Error in IU streaming: {exc}")
                yield f"event: error\ndata: {json.dumps({'message': str(exc), 'iu_type': iu_type, 'iu_id': iu_id})}\n\n"

            finally:
                yield f"event: done\ndata: {json.dumps({'message': 'Stream ended'})}\n\n"

        return Response(
            _generate_sse(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
            },
        )

    except Exception as e:
        print(f"Error in process_information_unit_stream ({iu_type}/{iu_id}): {str(e)}")
        def _err():
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
            yield f"event: done\ndata: {json.dumps({'message': 'Stream ended'})}\n\n"
        return Response(_err(), mimetype='text/event-stream')


# ── Active feature instances for cancel support ─────────────────────
# Keyed by feature_id (str), stores the feature object during streaming
# so the cancel endpoint can call its cancel() method.
_active_features: dict = {}


@app.route('/api/process/<int:feature_id>/cancel', methods=['POST', 'OPTIONS'])
def cancel_feature_processing(feature_id):
    """Ask a running feature to cancel its current processing."""
    if request.method == 'OPTIONS':
        return ('', 204)

    fid = str(feature_id)
    feature = _active_features.get(fid)
    if feature is None:
        return jsonify({'status': 'error', 'message': f'No active processing for feature {fid}'}), 404

    try:
        result = feature.cancel()
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/process/<int:feature_id>/stream', methods=['POST', 'OPTIONS'])
def process_feature_stream(feature_id):
    """SSE endpoint — streams progress events during feature processing.

    Returns ``text/event-stream`` with events:
    * ``event: log``       — ``{"message": "...", "level": "info"}``
    * ``event: progress``  — ``{"progress": 0.25, "message": "Batch 1/4"}``
    * ``event: result``    — final JSON result payload
    * ``event: done``      — stream end
    """
    if request.method == 'OPTIONS':
        return ('', 204)

    try:
        logger.clear_logs()
        input_data = request.json or {}

        if not NEW_FEATURE_ARCHITECTURE:
            def _err():
                yield f"event: error\ndata: {json.dumps({'message': 'Feature architecture not available'})}\n\n"
                yield f"event: done\ndata: {json.dumps({'message': 'Stream ended'})}\n\n"
            return Response(_err(), mimetype='text/event-stream')

        print(f"Using Feature architecture (streaming) for feature {feature_id}")
        feature = create_feature(str(feature_id), logger)

        # Register for cancel support
        _active_features[str(feature_id)] = feature

        # Extract inputs the same way the sync endpoint does
        inputs = feature.extract_inputs(input_data)

        def _generate_sse():
            """Yield SSE blocks from the feature's streaming processor."""
            try:
                # Check if the feature supports streaming
                if hasattr(feature, 'process_feature_stream'):
                    for sse_block in feature.process_feature_stream(inputs):
                        yield sse_block
                else:
                    # Fallback: run synchronously and wrap as SSE
                    yield f"event: log\ndata: {json.dumps({'message': 'No streaming support, running synchronously...', 'level': 'info'})}\n\n"
                    results = feature.process(input_data)
                    yield f"event: result\ndata: {json.dumps(results)}\n\n"

                # Always append accumulated logger logs as a final event
                logs = logger.get_logs()
                if logs:
                    yield f"event: logs\ndata: {json.dumps(logs)}\n\n"

            except Exception as exc:
                print(f"Error in streaming process: {exc}")
                yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"

            finally:
                # Unregister from cancel support
                _active_features.pop(str(feature_id), None)

            yield f"event: done\ndata: {json.dumps({'message': 'Stream ended'})}\n\n"

        return Response(
            _generate_sse(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
            },
        )

    except ValueError as e:
        print(f"Feature {feature_id} not found: {str(e)}")
        def _err():
            yield f"event: error\ndata: {json.dumps({'message': f'Feature {feature_id} not found'})}\n\n"
            yield f"event: done\ndata: {json.dumps({'message': 'Stream ended'})}\n\n"
        return Response(_err(), mimetype='text/event-stream')
    except Exception as e:
        print(f"Error in process_feature_stream: {str(e)}")
        def _err():
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
            yield f"event: done\ndata: {json.dumps({'message': 'Stream ended'})}\n\n"
        return Response(_err(), mimetype='text/event-stream')



@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download JSON results file"""
    try:
        import tempfile
        from pathlib import Path
        from io import BytesIO
        
        # Ensure filename is safe (no path traversal)
        if '/' in filename or '\\' in filename or '..' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        # Look for the file in temp directory
        temp_dir = Path(tempfile.gettempdir()) / 'emos_mosfet_results'
        file_path = temp_dir / filename
        
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        # Send file for download
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# Node Editor endpoint — execute a single Information Unit
# ═══════════════════════════════════════════════════════════════════

def _sse_event(event, data):
    """Format a single SSE event string."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ── Active node-run tracking for cancellation ────────────────────────
# Keyed by run_id (str).  Each entry holds:
#   generator : the MattergenGenerator instance (if applicable)
#   job_id    : the MatterGen Docker job_id (populated once the stream starts)
#   cancelled : threading.Event — set when the user requests cancellation
_active_node_runs: dict = {}
_node_runs_lock = threading.Lock()


@app.route('/api/node/cancel/<run_id>', methods=['POST', 'OPTIONS'])
def node_cancel(run_id):
    """Cancel a running node-editor IU execution.

    For MatterGen generators this forwards the cancel to the Docker
    container via ``cancel_generation(job_id)``.  For all IU types the
    ``cancelled`` event is set so the SSE generator can break early.
    """
    if request.method == 'OPTIONS':
        return ('', 204)

    with _node_runs_lock:
        entry = _active_node_runs.get(run_id)

    if entry is None:
        return jsonify({'status': 'not_found', 'message': f'No active run {run_id}'}), 404

    # Signal the SSE generator to stop
    entry['cancelled'].set()

    # Forward cancel to MatterGen Docker container if we have a job_id
    gen = entry.get('generator')
    job_id = entry.get('job_id')
    if gen and job_id and hasattr(gen, 'cancel_generation'):
        try:
            result = gen.cancel_generation(job_id)
            print(f"[node/cancel] Cancelled MatterGen job {job_id}: {result}")
            return jsonify({'status': 'cancelled', 'job_id': job_id, 'detail': result})
        except Exception as e:
            print(f"[node/cancel] Error cancelling job {job_id}: {e}")
            return jsonify({'status': 'cancel_sent', 'message': str(e)})

    return jsonify({'status': 'cancelled', 'message': f'Run {run_id} cancelled'})


@app.route('/api/node/run', methods=['POST', 'OPTIONS'])
def node_run():
    """Execute a single Information Unit (database/generator/predictor) and
    stream the results back as SSE events.

    Expected JSON body:
        {
            "type": "database" | "generator" | "predictor",
            "key":  "<factory key, e.g. cod, mattergen_base_model, gbfs>",
            "inputs": { <user-provided fields from the node UI> },
            "upstream": { <port_key: data_from_upstream_node> }
        }

    SSE events emitted:
        event: run_id   — { run_id }  (first event — used for cancellation)
        event: log      — { message, level }
        event: progress — { progress (0-1), message }
        event: result   — the final output payload
        event: error    — { message }
        event: done     — stream end
    """
    if request.method == 'OPTIONS':
        return ('', 204)

    try:
        body     = request.get_json(force=True) or {}
        iu_type  = body.get('type', '')
        iu_key   = body.get('key', '')
        inputs   = body.get('inputs', {})
        upstream = body.get('upstream', {})
    except Exception as e:
        return Response(
            _sse_event('error', {'message': f'Bad request: {e}'}) +
            _sse_event('done', {'message': 'Stream ended'}),
            mimetype='text/event-stream',
        )

    # Create a run entry for cancel support
    run_id = uuid.uuid4().hex[:12]
    cancel_event = threading.Event()
    run_entry = {
        'generator': None,
        'job_id': None,
        'cancelled': cancel_event,
    }
    with _node_runs_lock:
        _active_node_runs[run_id] = run_entry

    def _generate():
        try:
            # First event: tell the client our run_id so it can cancel us
            yield _sse_event('run_id', {'run_id': run_id})

            if iu_type == 'database':
                yield from _run_database(iu_key, inputs)
            elif iu_type == 'generator':
                yield from _run_generator(iu_key, inputs, run_entry)
            elif iu_type == 'predictor':
                yield from _run_predictor(iu_key, inputs, upstream, run_entry)
            elif iu_type == 'utility':
                if iu_key == 'lambda':
                    yield from _run_lambda(inputs, upstream)
                else:
                    yield _sse_event('error', {'message': f'Unknown utility node: {iu_key}'})
            else:
                yield _sse_event('error', {'message': f'Unknown IU type: {iu_type}'})
        except _NodeCancelledError:
            print(f"[node/run] Run {run_id} cancelled")
            yield _sse_event('error', {'message': 'Cancelled by user'})
        except Exception as exc:
            print(f"[node/run] Error: {exc}\n{traceback.format_exc()}")
            yield _sse_event('error', {'message': str(exc)})
        finally:
            with _node_runs_lock:
                _active_node_runs.pop(run_id, None)
        yield _sse_event('done', {'message': 'Stream ended'})

    return Response(
        _generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


class _NodeCancelledError(Exception):
    """Raised inside a node-run generator when the user cancels."""
    pass


def _check_node_cancelled(run_entry):
    """Raise _NodeCancelledError if this run has been cancelled."""
    if run_entry and run_entry['cancelled'].is_set():
        raise _NodeCancelledError("Cancelled by user")


# ── Database runner ──────────────────────────────────────────────────
def _run_database(key, inputs):
    yield _sse_event('log', {'message': f'Instantiating database: {key}', 'level': 'info'})

    if key not in database_factory:
        yield _sse_event('error', {'message': f'Database "{key}" not found in factory'})
        return

    db_cls = database_factory[key]
    db = db_cls(key, logger)

    # Build retrieve inputs — map node-editor field names to the database API keys
    retrieve_inputs = {}
    retrieve_inputs['target_compositions'] = inputs.get('target_compositions', inputs.get('query', ''))
    retrieve_inputs['batch_size'] = int(inputs.get('batch_size', inputs.get('limit', 10)))

    # Collect property filter fields (prefixed with "filter_")
    for k, v in inputs.items():
        if k.startswith('filter_') and v not in (None, '', []):
            prop_name = k[7:]  # strip "filter_"
            # Range fields end with _min or _max
            if prop_name.endswith('_min'):
                base = prop_name[:-4]
                if base not in retrieve_inputs:
                    retrieve_inputs[base] = [None, None]
                elif not isinstance(retrieve_inputs[base], list):
                    retrieve_inputs[base] = [None, None]
                retrieve_inputs[base][0] = v
            elif prop_name.endswith('_max'):
                base = prop_name[:-4]
                if base not in retrieve_inputs:
                    retrieve_inputs[base] = [None, None]
                elif not isinstance(retrieve_inputs[base], list):
                    retrieve_inputs[base] = [None, None]
                retrieve_inputs[base][1] = v
            else:
                retrieve_inputs[prop_name] = v

    yield _sse_event('log', {'message': f'Querying: {retrieve_inputs}', 'level': 'info'})
    yield _sse_event('progress', {'progress': 0.1, 'message': 'Sending query...'})

    raw_result = db.retrieve(retrieve_inputs)

    # Databases now return a dict: {"source": ..., "queries": ..., "cif_strings": [...]}
    if isinstance(raw_result, dict):
        cif_strings = raw_result.get('cif_strings', [])
    elif isinstance(raw_result, list):
        # Backward-compat: old implementations returned cif strings directly
        cif_strings = raw_result
    else:
        cif_strings = []

    if not cif_strings:
        yield _sse_event('log', {'message': 'No results returned', 'level': 'warning'})
        yield _sse_event('result', [])
        return

    yield _sse_event('log', {'message': f'Retrieved {len(cif_strings)} structures', 'level': 'info'})
    yield _sse_event('progress', {'progress': 1.0, 'message': 'Complete'})
    yield _sse_event('result', cif_strings)


# ── Generator runner ─────────────────────────────────────────────────
def _run_generator(key, inputs, run_entry=None):
    yield _sse_event('log', {'message': f'Instantiating generator: {key}', 'level': 'info'})

    if key not in generator_factory:
        yield _sse_event('error', {'message': f'Generator "{key}" not found in factory'})
        return

    gen_cls = generator_factory[key]
    gen = gen_cls(key, logger)

    # Store generator instance in the run entry so cancel can reach it
    if run_entry is not None:
        run_entry['generator'] = gen

    # Build generation inputs
    gen_inputs = {}
    gen_inputs['batch_size'] = int(inputs.get('batch_size', 10))

    # For MatterGen generators: set pretrained_name from the key
    # and collect properties_to_condition_on from prop_ fields
    if 'mattergen' in key:
        gen_inputs['pretrained_name'] = key
        props = {}
        for k, v in inputs.items():
            if k.startswith('prop_') and v not in (None, ''):
                prop_name = k[5:]  # strip "prop_"
                try:
                    props[prop_name] = float(v)
                except (ValueError, TypeError):
                    props[prop_name] = v
        if props:
            gen_inputs['properties_to_condition_on'] = props

    yield _sse_event('progress', {'progress': 0.05, 'message': 'Starting generation...'})

    # Prefer streaming if available
    if hasattr(gen, 'generate_stream'):
        yield _sse_event('log', {'message': 'Using streaming generation', 'level': 'info'})
        cif_strings = []
        for event_dict in gen.generate_stream(gen_inputs):
            # Check cancellation between each streamed event
            _check_node_cancelled(run_entry)

            ev = event_dict.get('event', 'log')

            # Capture MatterGen job_id so we can cancel it later
            if ev == 'job_id' and run_entry is not None:
                run_entry['job_id'] = event_dict.get('job_id')
                yield _sse_event('log', {'message': f'Generation job started: {run_entry["job_id"]}', 'level': 'info'})
                continue

            if ev == 'log':
                yield _sse_event('log', {'message': event_dict.get('message', ''), 'level': event_dict.get('level', 'info')})
            elif ev == 'progress':
                yield _sse_event('progress', {'progress': event_dict.get('progress', 0), 'message': event_dict.get('message', '')})
            elif ev == 'result':
                # Extract CIF strings from the result
                cif_strings = _extract_cif_strings(event_dict)
                yield _sse_event('log', {'message': f'Generated {len(cif_strings)} structures', 'level': 'info'})
            elif ev == 'cancelled':
                yield _sse_event('log', {'message': 'Generation cancelled by user', 'level': 'warning'})
                raise _NodeCancelledError("Cancelled by user")
            elif ev == 'error':
                yield _sse_event('error', {'message': event_dict.get('message', 'Generation error')})
                return
        yield _sse_event('progress', {'progress': 1.0, 'message': 'Complete'})
        yield _sse_event('result', cif_strings)
    else:
        yield _sse_event('log', {'message': 'Using synchronous generation', 'level': 'info'})
        result = gen.generate(gen_inputs)
        cif_strings = _extract_cif_strings(result)
        yield _sse_event('log', {'message': f'Generated {len(cif_strings)} structures', 'level': 'info'})
        yield _sse_event('progress', {'progress': 1.0, 'message': 'Complete'})
        yield _sse_event('result', cif_strings)


def _extract_cif_strings(result):
    """Normalise generator output to a list of CIF strings."""
    if isinstance(result, dict):
        # MatterGen format: result may have 'cif_strings' key
        if 'cif_strings' in result:
            return result['cif_strings']
        # Or 'structures' with pymatgen dict — convert
        if 'structures' in result:
            cifs = []
            for s in result['structures']:
                try:
                    from pymatgen.core import Structure as PmgStructure
                    struct = PmgStructure.from_dict(s) if isinstance(s, dict) else s
                    cifs.append(struct.to(fmt='cif'))
                except Exception:
                    cifs.append(str(s))
            return cifs
        return [json.dumps(result)]
    elif isinstance(result, str):
        return [result]
    elif isinstance(result, list):
        return result
    return [str(result)]


# ── Predictor runner ─────────────────────────────────────────────────
def _run_predictor(key, inputs, upstream, run_entry=None):
    yield _sse_event('log', {'message': f'Preparing predictor: {key}', 'level': 'info'})

    if key not in predictor_factory:
        yield _sse_event('error', {'message': f'Predictor "{key}" not found in factory'})
        return

    # Get CIF data from upstream
    cif_data = upstream.get('cif_in')
    if cif_data is None:
        yield _sse_event('error', {'message': 'No CIF data connected to predictor input'})
        return

    cif_array = cif_data if isinstance(cif_data, list) else [cif_data]
    cif_array = [c for c in cif_array if isinstance(c, str) and c.strip()]

    if not cif_array:
        yield _sse_event('error', {'message': 'No valid CIF strings in upstream data'})
        return

    yield _sse_event('log', {'message': f'Predicting for {len(cif_array)} structure(s)', 'level': 'info'})
    yield _sse_event('progress', {'progress': 0.1, 'message': 'Running prediction...'})

    _check_node_cancelled(run_entry)

    # All predictors accept a list[str] of CIF strings in a single batch call
    pred_cls = predictor_factory[key]
    pred = pred_cls(key, logger)
    result = pred.predict(cif_array)

    yield _sse_event('log', {'message': f'Prediction complete for {len(cif_array)} structure(s)', 'level': 'info'})
    yield _sse_event('progress', {'progress': 1.0, 'message': 'Complete'})
    yield _sse_event('result', result)
    

# ── Lambda runner (utility node) ─────────────────────────────────────
def _run_lambda(inputs, upstream):
    code = inputs.get('code', '').strip()
    if not code:
        yield _sse_event('error', {'message': 'Lambda node: no code provided'})
        return

    cif_list = upstream.get('cif_in', [])
    if not isinstance(cif_list, list):
        cif_list = []

    results = upstream.get('result_in', {})
    if not isinstance(results, dict):
        results = {}

    yield _sse_event('log', {'message': f'Lambda: executing on {len(cif_list)} CIF(s)…', 'level': 'info'})

    try:
        result = run_sandboxed_lambda(code, cif_list, results)
    except LambdaSandboxError as exc:
        yield _sse_event('error', {'message': f'Lambda error: {exc}'})
        return

    output_cifs = result['cif_out']
    output_results = result['result_out']

    yield _sse_event('log', {'message': f'Lambda produced {len(output_cifs)} CIF(s)', 'level': 'info'})
    yield _sse_event('progress', {'progress': 1.0, 'message': 'Complete'})
    yield _sse_event('result', {'cif_out': output_cifs, 'result_out': output_results})


if __name__ == '__main__':
    print("Starting Flask server for all EMOS features...")
    print(f"Project root: {PROJECT_ROOT}")
    print("Available endpoints:")
    
    if NEW_FEATURE_ARCHITECTURE:
        try:
            available_features = get_available_features()
            for feature_id in available_features:
                print(f"  ✅ Feature {feature_id}: /api/process/{feature_id}")
        except Exception as e:
            print(f"  ❌ Error loading features: {e}")
    else:
        print("  ❌ Feature architecture not available")
    
    # Get port from environment variable for deployment
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)
