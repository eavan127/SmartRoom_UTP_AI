"""Our trained verification model: decides if two face embeddings belong to the same person.

SFace (pretrained) turns each face into 128 numbers. This model is trained by us (src/train_verifier.py)
on pairs of those numbers and outputs the probability that the two faces are the same person.
The saved model lives in models/verifier.joblib (ignored by git, like all face data).
"""
from pathlib import Path

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "verifier.joblib"


def pair_features(a, b):
    """Symmetric features for a pair of L2-normalised embeddings: element-wise product and difference.

    The product sums to the cosine similarity, so the model starts from what SFace already knows
    and learns which of the 128 dimensions to trust more.
    """
    a, b = np.atleast_2d(a), np.atleast_2d(b)
    return np.hstack([a * b, np.abs(a - b)])


class Verifier:
    _cache = {}

    def __init__(self, clf, meta=None):
        self.clf = clf
        self.meta = meta or {}

    @classmethod
    def load(cls, path=MODEL_PATH):
        path = Path(path)
        if path not in cls._cache:
            if not path.exists():
                raise FileNotFoundError(f"{path} not found. Train it first: python -m src.train_verifier")
            data = joblib.load(path)
            cls._cache[path] = cls(data["model"], data.get("meta"))
        return cls._cache[path]

    def score(self, a, b):
        """Probability (0-1) that a and b are the same person."""
        return float(self.clf.predict_proba(pair_features(a, b))[0, 1])

    def save(self, path=MODEL_PATH):
        Path(path).parent.mkdir(exist_ok=True)
        joblib.dump({"model": self.clf, "meta": self.meta}, path)
