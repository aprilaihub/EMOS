from abc import ABC, abstractmethod


class BaseFeature(ABC):
    """Simple base class for all Features - minimal implementation"""
    
    def __init__(self, feature_name, logger=None):
        self.feature_name = feature_name
        self.logger = logger
    
    @abstractmethod
    def info(self):
        """Return feature description"""
        pass
    
    @abstractmethod
    def extract_inputs(self, input_data):
        """Extract and validate inputs from input_data"""
        pass
    
    @abstractmethod
    def process_feature(self, inputs):
        """Core feature processing logic"""
        pass
    
    @abstractmethod
    def format_outputs(self, results):
        """Format results to expected output format"""
        pass
    
    def process(self, input_data):
        """Main process method - template pattern"""
        # Step 1: Extract inputs
        inputs = self.extract_inputs(input_data)
        
        # Step 2: Process feature
        results = self.process_feature(inputs)
        
        # Step 3: Format outputs
        outputs = self.format_outputs(results)
        
        return outputs

    # ── Streaming ─────────────────────────────────────────────────────

    def process_feature_stream(self, inputs):
        """Yield SSE-formatted strings while the feature processes.

        Each ``yield`` should be a complete SSE block
        (``event: <type>\\ndata: <json>\\n\\n``).

        The default implementation falls back to the synchronous
        ``process_feature`` and emits a single ``event: result`` with the
        full payload.  Subclasses should override this to provide real
        incremental progress updates.
        """
        import json

        results = self.process_feature(inputs)
        yield f"event: result\ndata: {json.dumps(results)}\n\n"

    # ── Cancellation ──────────────────────────────────────────────────

    def cancel(self) -> dict:
        """Cancel the currently running processing, if supported.

        The default implementation returns an error indicating that the
        feature does not support cancellation.  Subclasses should override
        this to wire up feature-specific cancel logic.
        """
        return {
            "status": "error",
            "message": f"{self.feature_name} does not support cancellation.",
        }