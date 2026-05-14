from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS
import os
import sys
import pathlib
import json
import requests

# Get absolute paths regardless of where the script is run from
BACKEND_DIR = pathlib.Path(__file__).parent.resolve()  # /home/soe/EMOS/backend
PROJECT_ROOT = BACKEND_DIR.parent.resolve()  # /home/soe/EMOS

# Add the project root to Python path
sys.path.append(str(PROJECT_ROOT))

#information units creators & destroyers
from Information_Units.Generators.GeneratorFactory import generator_factory, generator_registry
from Information_Units.Databases.DatabaseFactory import database_factory, database_registry
from Information_Units.Predictors.PredictorFactory import predictor_factory, predictor_registry

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


@app.route('/api/debug/mattergen', methods=['GET'])
def debug_mattergen_connectivity():
    """Temporary diagnostics for Render deployment issues."""
    api_url = os.getenv("MATTERGEN_API_URL", "http://localhost:8100").strip().rstrip("/")
    if api_url and "://" not in api_url:
        api_url = f"http://{api_url}"
    health_url = f"{api_url}/health"

    result = {
        "configured_api_url": api_url,
        "health_url": health_url,
        "health_reachable": False,
    }
    try:
        resp = requests.get(health_url, timeout=8)
        result["health_reachable"] = resp.status_code == 200
        result["health_status_code"] = resp.status_code
        try:
            result["health_response"] = resp.json()
        except Exception:
            result["health_response"] = resp.text[:500]
    except Exception as exc:
        result["health_error"] = str(exc)

    return jsonify(result), 200


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
