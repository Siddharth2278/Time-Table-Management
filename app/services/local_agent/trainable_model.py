"""Actually-fitted local timetable model, persisted with joblib.

Preferred backend is scikit-learn HistGradientBoostingClassifier. On
machines where sklearn's compiled extensions are unavailable, training
falls back to a deterministic pure-stdlib regularized logistic
regression. Both backends are genuinely fitted on historical
positives vs. sampled negatives and predict P(suitable placement |
structural features). The active backend is recorded in metadata.

The model never sees subject names/codes — only the structural feature
vector from training_dataset. Validation refuses to persist a model
that cannot beat chance, so the application can never claim "trained"
without an actual fit.
"""
import math
from typing import Any, Dict, List, Tuple

from app.services.local_agent.schemas import LearningError
from app.services.local_agent.training_dataset import FEATURES_V1, FEATURE_SCHEMA_VERSION

MODEL_VERSION = 1
MIN_SEPARATION = 0.01


def feature_names() -> List[str]:
    return list(FEATURES_V1)


def _check_matrix(X: List[List[float]], y: List[int]):
    if len(set(y)) < 2:
        raise LearningError("Training needs both positive and negative examples.")
    for row in X:
        if len(row) != len(FEATURES_V1):
            raise LearningError("Feature vector length does not match schema.")
        for value in row:
            if not isinstance(value, (int, float)) or value != value:
                raise LearningError("Non-finite feature value in training data.")


def _metrics(y: List[int], proba: List[float]) -> Dict[str, Any]:
    mean_pos = sum(p for p, label in zip(proba, y) if label == 1) / max(1, sum(y))
    mean_neg = sum(p for p, label in zip(proba, y) if label == 0) / max(1, len(y) - sum(y))
    separation = mean_pos - mean_neg
    return {
        "train_accuracy": round(sum(
            (1 if p >= 0.5 else 0) == label for p, label in zip(proba, y)
        ) / max(1, len(y)), 4),
        "mean_positive_score": round(mean_pos, 4),
        "mean_negative_score": round(mean_neg, 4),
        "separation": round(separation, 4),
    }


def _fit_sklearn(X: List[List[float]], y: List[int]):
    from sklearn.ensemble import HistGradientBoostingClassifier
    model = HistGradientBoostingClassifier(
        max_iter=200, learning_rate=0.08, max_leaf_nodes=15,
        min_samples_leaf=5, l2_regularization=1.0, random_state=42,
        monotonic_cst=[0] * 10 + [1, 1, 1])
    model.fit(X, y)
    return model


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    hacked = math.exp(z)
    return hacked / (1.0 + hacked)


def _fit_stdlib_logreg(X: List[List[float]], y: List[int]) -> Dict[str, Any]:
    """Deterministic batch gradient-descent logistic regression."""
    n = len(X)
    dim = len(FEATURES_V1)
    means = [sum(row[j] for row in X) / n for j in range(dim)]
    variances = [sum((row[j] - means[j]) ** 2 for row in X) / n for j in range(dim)]
    scales = [(v ** 0.5) if v > 1e-12 else 1.0 for v in variances]
    weights = [0.0] * dim
    bias = 0.0
    rate, decay = 0.5, 0.001
    for _ in range(1500):
        grad_w = [0.0] * dim
        grad_b = 0.0
        for row, label in zip(X, y):
            z = bias + sum(
                weights[j] * (row[j] - means[j]) / scales[j] for j in range(dim))
            pred = _sigmoid(max(-60.0, min(60.0, z)))
            err = pred - label
            for j in range(dim):
                grad_w[j] += err * (row[j] - means[j]) / scales[j]
            grad_b += err
        for j in range(dim):
            weights[j] -= rate * (grad_w[j] / n + decay * weights[j])
        bias -= rate * grad_b / n
    return {"weights": weights, "bias": bias, "mean": means, "scale": scales}


def _predict_stdlib(bundle: Dict[str, Any], rows: List[List[float]]) -> List[float]:
    weights, bias = bundle["weights"], bundle["bias"]
    means, scales = bundle["mean"], bundle["scale"]
    out = []
    for row in rows:
        z = bias + sum(
            weights[j] * (row[j] - means[j]) / scales[j] for j in range(len(row)))
        out.append(_sigmoid(max(-60.0, min(60.0, z))))
    return out


def train_model(X: List[List[float]], y: List[int]) -> Tuple[Any, Dict[str, Any]]:
    """Fit the classifier. Returns (bundle, metrics).

    bundle = {"backend": ..., "payload": ...} so persistence and
    prediction stay backend-agnostic.
    """
    _check_matrix(X, y)
    try:
        estimator = _fit_sklearn(X, y)
        bundle = {"backend": "sklearn-hgb", "payload": estimator}
        proba = [float(p[1]) for p in estimator.predict_proba(X)]
    except ImportError:
        payload = _fit_stdlib_logreg(X, y)
        bundle = {"backend": "stdlib-logreg", "payload": payload}
        proba = _predict_stdlib(payload, X)
    metrics = {
        "samples": len(y),
        "positives": int(sum(y)),
        "negatives": int(len(y) - sum(y)),
        "feature_schema": FEATURE_SCHEMA_VERSION,
        "model_version": MODEL_VERSION,
        "backend": bundle["backend"],
        **_metrics(y, proba),
    }
    if metrics["separation"] <= MIN_SEPARATION:
        raise LearningError(
            "Training failed validation: the fitted model cannot distinguish "
            "used placements from alternatives (separation "
            f"{metrics['separation']:.4f}). More varied history is needed.")
    return bundle, metrics


def predict_scores(bundle: Any, rows: List[List[float]]) -> List[float]:
    """Suitability scores in [0, 1]. Finite output guaranteed or error."""
    if not isinstance(bundle, dict) or "backend" not in bundle or "payload" not in bundle:
        raise LearningError("Stored model bundle is not usable.")
    for row in rows:
        if len(row) != len(FEATURES_V1):
            raise LearningError("Feature vector length does not match schema.")
    try:
        if bundle["backend"] == "sklearn-hgb":
            scores = [float(p[1]) for p in bundle["payload"].predict_proba(rows)]
        elif bundle["backend"] == "stdlib-logreg":
            scores = _predict_stdlib(bundle["payload"], rows)
        else:
            raise LearningError(f"Unknown model backend '{bundle['backend']}'.")
    except LearningError:
        raise
    except Exception as e:
        raise LearningError(f"Model prediction failed: {e}")
    for score in scores:
        if not 0.0 <= score <= 1.0 or score != score:
            raise LearningError("Model returned a non-finite score.")
    return scores
