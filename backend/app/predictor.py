"""Dependency-light inference for the trained model.

The scikit-learn pipeline is exported by train.py to artifacts/model.json
(scaler statistics, one-hot columns, coefficients, intercept). Serving from that
spec needs only numpy + pandas, which keeps the deployed API far below Vercel's
500 MB function limit (scikit-learn + scipy alone are ~150 MB).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd


class LinearValueModel:
    def __init__(self, spec: dict):
        if spec.get("type") != "log1p_linear_regression":
            raise ValueError(f"Unsupported model spec type: {spec.get('type')!r}")
        self.spec = spec
        self.numeric_features = spec["numeric_features"]
        self.categorical_feature = spec["categorical_feature"]
        self.categories = spec["categories"]
        self.mean = np.asarray(spec["scaler_mean"], dtype=float)
        self.scale = np.asarray(spec["scaler_scale"], dtype=float)
        self.coef_numeric = np.asarray(spec["coef_numeric"], dtype=float)
        self.coef_categorical = np.asarray(spec["coef_categorical"], dtype=float)
        self.intercept = float(spec["intercept"])

    @classmethod
    def load(cls, path: Path) -> "LinearValueModel":
        return cls(json.loads(Path(path).read_text()))

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        """Predicted market value in EUR (same maths as the sklearn pipeline)."""
        scaled = (frame[self.numeric_features].to_numpy(dtype=float) - self.mean) / self.scale
        onehot = np.array(
            [[1.0 if value == category else 0.0 for category in self.categories]
             for value in frame[self.categorical_feature]],
            dtype=float,
        ).reshape(len(frame), len(self.categories))
        log_value = self.intercept + scaled @ self.coef_numeric + onehot @ self.coef_categorical
        return np.expm1(log_value)
