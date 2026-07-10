import pytest
from app.predictor import _compute_confidence


class TestConfidence:
    def test_certain_prediction(self):
        import numpy as np
        probs = np.array([0.95, 0.02, 0.02, 0.01])
        features = {"a": 1.0, "b": 2.0, "c": 3.0}
        confidence = _compute_confidence(probs, features)
        assert 80 <= confidence <= 100

    def test_uncertain_prediction(self):
        import numpy as np
        probs = np.array([0.25, 0.25, 0.25, 0.25])
        features = {"a": 1.0, "b": 2.0}
        confidence = _compute_confidence(probs, features)
        assert 0 <= confidence <= 60

    def test_empty_features(self):
        import numpy as np
        probs = np.array([1.0, 0.0, 0.0, 0.0])
        features = {}
        confidence = _compute_confidence(probs, features)
        assert 0 <= confidence <= 100

    def test_null_features(self):
        import numpy as np
        probs = np.array([0.8, 0.1, 0.05, 0.05])
        features = {"a": None, "b": 1.0}
        confidence = _compute_confidence(probs, features)
        assert 0 <= confidence <= 100


class TestSchemas:
    def test_predict_request_valid(self):
        from app.schemas import PredictRequest
        req = PredictRequest(customer_id="CUST00001", business_type="retail", gst_filing_regularity=0.95)
        assert req.customer_id == "CUST00001"
        assert req.business_type == "retail"
        assert req.gst_filing_regularity == 0.95

    def test_predict_request_defaults(self):
        from app.schemas import PredictRequest
        req = PredictRequest(customer_id="CUST00001", business_type="retail")
        assert req.business_type == "retail"
