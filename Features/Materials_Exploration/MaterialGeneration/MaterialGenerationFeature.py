from Features.BaseFeature import BaseFeature
from Information_Units.Generators.GeneratorFactory import generator_factory, generator_registry
from Information_Units.Databases.DatabaseFactory import database_factory
from Information_Units.Predictors.PredictorFactory import predictor_factory


class MaterialGenerationFeature(BaseFeature):
    def __init__(self, logger=None):
        super().__init__("Material Generation", logger)
        # Cancel support: track the active generator and job_id during streaming
        self._active_generator = None
        self._active_job_id = None
    
    def info(self):
        return "Material Generation: Generate new material compositions using AI-powered algorithms and predictive models"
    
    def extract_inputs(self, input_data):
        return {
            'active_databases': input_data.get('active_databases', []),
            'active_generators': input_data.get('active_generators', []),
            'active_predictors': input_data.get('active_predictors', []),
            'generator_inputs': input_data.get('generator_inputs', {}),
        }
    
    def process_feature(self, inputs):
        if self.logger:
            self.logger.log('Initializing Material Generation...', 'info')

        # ── Collect results from all active generators ────────────────
        generator_inputs = inputs.get('generator_inputs', {})
        all_generation_results = {}

        active_generators = inputs.get('active_generators', [])
        if not active_generators:
            if self.logger:
                self.logger.log('No active generators selected.', 'warning')
        else:
            if self.logger:
                names = ', '.join(g['name'] for g in active_generators)
                self.logger.log(f'Active generators ({len(active_generators)}): {names}', 'info')

        for gen_info in active_generators:
            gen_key = gen_info['value']

            # Check if the generator is in the registry (instantiated)
            if gen_key in generator_registry:
                gen_instance = generator_registry[gen_key]
            elif gen_key in generator_factory:
                gen_instance = generator_factory[gen_key](gen_key, self.logger)
            else:
                if self.logger:
                    self.logger.log(f'Generator "{gen_key}" not found in factory — skipping.', 'warning')
                continue

            # Get the per-generator inputs collected by the JS ___Inputs class
            gen_params = generator_inputs.get(gen_key, {})

            if self.logger:
                self.logger.log(f'Calling {gen_key}.generate() with params: {gen_params}', 'info')

            try:
                result = gen_instance.generate(gen_params)
                all_generation_results[gen_key] = result

                status = result.get('status', 'unknown')
                n_structs = result.get('num_structures', 0)
                if self.logger:
                    self.logger.log(
                        f'{gen_key}: status={status}, {n_structs} structure(s) returned.', 'info'
                    )

                # Forward any debug_logs from the container
                for dl in result.get('debug_logs', []):
                    if self.logger:
                        self.logger.log(f'  [{gen_key}] {dl}', 'info')

            except Exception as exc:
                if self.logger:
                    self.logger.log(f'{gen_key}.generate() failed: {exc}', 'error')
                all_generation_results[gen_key] = {
                    'status': 'error',
                    'message': str(exc),
                }

        if self.logger:
            self.logger.log('Material Generation processing completed.', 'info')
        
        return {
            'status': 'completed',
            'generation_results': all_generation_results,
        }
    
    def format_outputs(self, results):
        """Return the raw generation results so the JS front-end can
        render them (structure dropdown, CIF viewer, etc.)."""
        return results

    # ── Cancel support ────────────────────────────────────────────────

    def cancel(self) -> dict:
        """Cancel the currently running generation, if any.

        Delegates to the active generator's ``cancel_generation()`` method
        which POSTs to the Docker container's ``/cancel/{job_id}`` endpoint.
        """
        gen = self._active_generator
        job_id = self._active_job_id

        if gen is None or job_id is None:
            return {"status": "error", "message": "No active generation to cancel."}

        if self.logger:
            self.logger.log(f"Cancelling generation job {job_id}...", "info")

        if hasattr(gen, 'cancel_generation'):
            result = gen.cancel_generation(job_id)
        else:
            result = {"status": "error", "message": f"Generator {type(gen).__name__} does not support cancellation."}

        # Clear tracking state regardless
        self._active_generator = None
        self._active_job_id = None
        return result

    # ── Streaming variant ─────────────────────────────────────────────

    def process_feature_stream(self, inputs):
        """Yield SSE-formatted strings while generators run.

        Each ``yield`` is a complete SSE block (``event: … \\n data: …\\n\\n``).
        The final ``event: result`` carries the same payload as the synchronous
        ``process_feature`` return value.
        """
        import json

        def _sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        if self.logger:
            self.logger.log('Initializing Material Generation (streaming)...', 'info')
        yield _sse("log", {"message": "Initializing Material Generation...", "level": "info"})

        generator_inputs = inputs.get('generator_inputs', {})
        all_generation_results = {}

        active_generators = inputs.get('active_generators', [])
        if not active_generators:
            if self.logger:
                self.logger.log('No active generators selected.', 'warning')
            yield _sse("log", {"message": "No active generators selected.", "level": "warning"})
        else:
            names = ', '.join(g['name'] for g in active_generators)
            msg = f'Active generators ({len(active_generators)}): {names}'
            if self.logger:
                self.logger.log(msg, 'info')
            yield _sse("log", {"message": msg, "level": "info"})

        for gen_info in active_generators:
            gen_key = gen_info['value']

            if gen_key in generator_registry:
                gen_instance = generator_registry[gen_key]
            elif gen_key in generator_factory:
                gen_instance = generator_factory[gen_key](gen_key, self.logger)
            else:
                msg = f'Generator "{gen_key}" not found in factory — skipping.'
                if self.logger:
                    self.logger.log(msg, 'warning')
                yield _sse("log", {"message": msg, "level": "warning"})
                continue

            gen_params = generator_inputs.get(gen_key, {})
            if self.logger:
                self.logger.log(f'Calling {gen_key}.generate_stream() with params: {gen_params}', 'info')
            yield _sse("log", {"message": f"Calling {gen_key}.generate_stream()...", "level": "info"})

            # Check if the generator supports streaming
            if hasattr(gen_instance, 'generate_stream'):
                try:
                    final_result = None
                    # Track active generator/job for cancel support
                    self._active_generator = gen_instance
                    for sse_event in gen_instance.generate_stream(gen_params):
                        evt = sse_event.get("event", "log")

                        # Capture job_id from any event that carries it
                        if "job_id" in sse_event and self._active_job_id is None:
                            self._active_job_id = sse_event["job_id"]

                        if evt == "result":
                            final_result = sse_event
                            # Forward final result info as a log
                            n = sse_event.get("num_structures", 0)
                            msg = f'{gen_key}: {n} structure(s) generated.'
                            yield _sse("log", {"message": msg, "level": "info"})
                            # Forward debug_logs
                            for dl in sse_event.get("debug_logs", []):
                                if self.logger:
                                    self.logger.log(f'  [{gen_key}] {dl}', 'info')
                        elif evt == "progress":
                            yield _sse("progress", {
                                "progress": sse_event.get("progress", 0),
                                "message": sse_event.get("message", ""),
                                "generator": gen_key,
                            })
                        elif evt == "error":
                            msg = sse_event.get("message", "Unknown error")
                            if self.logger:
                                self.logger.log(f'{gen_key}: {msg}', 'error')
                            yield _sse("log", {"message": f"{gen_key}: {msg}", "level": "error"})
                        elif evt == "cancelled":
                            msg = sse_event.get("message", "Generation cancelled.")
                            if self.logger:
                                self.logger.log(f'{gen_key}: {msg}', 'info')
                            yield _sse("cancelled", {"message": f"{gen_key}: {msg}"})
                        elif evt == "log":
                            yield _sse("log", {
                                "message": f"[{gen_key}] {sse_event.get('message', '')}",
                                "level": sse_event.get("level", "info"),
                            })
                        # "done" events are ignored — we handle end-of-stream ourselves

                    # Clear tracking after this generator finishes
                    self._active_generator = None
                    self._active_job_id = None

                    if final_result:
                        # Remove the "event" key before storing
                        final_result.pop("event", None)
                        all_generation_results[gen_key] = final_result
                    else:
                        all_generation_results[gen_key] = {
                            "status": "error",
                            "message": f"{gen_key}: No result received from stream",
                        }

                except Exception as exc:
                    msg = f'{gen_key}.generate_stream() failed: {exc}'
                    if self.logger:
                        self.logger.log(msg, 'error')
                    yield _sse("log", {"message": msg, "level": "error"})
                    all_generation_results[gen_key] = {
                        'status': 'error',
                        'message': str(exc),
                    }
                    # Clear tracking on failure
                    self._active_generator = None
                    self._active_job_id = None
            else:
                # Fallback: synchronous generate()
                yield _sse("log", {"message": f"{gen_key}: no streaming support, using sync generate()", "level": "info"})
                try:
                    result = gen_instance.generate(gen_params)
                    all_generation_results[gen_key] = result
                    status = result.get('status', 'unknown')
                    n_structs = result.get('num_structures', 0)
                    if self.logger:
                        self.logger.log(f'{gen_key}: status={status}, {n_structs} structure(s).', 'info')
                    for dl in result.get('debug_logs', []):
                        if self.logger:
                            self.logger.log(f'  [{gen_key}] {dl}', 'info')
                except Exception as exc:
                    if self.logger:
                        self.logger.log(f'{gen_key}.generate() failed: {exc}', 'error')
                    all_generation_results[gen_key] = {
                        'status': 'error',
                        'message': str(exc),
                    }

        if self.logger:
            self.logger.log('Material Generation processing completed.', 'info')
        yield _sse("log", {"message": "Material Generation processing completed.", "level": "info"})

        # Final result event with full payload
        final_payload = {
            'status': 'completed',
            'generation_results': all_generation_results,
        }
        yield _sse("result", final_payload)
