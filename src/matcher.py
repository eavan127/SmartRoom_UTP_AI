"""Matching logic: compare a live face only against the booked students.

Gallery layout (not in git):  data/gallery/<Student X>/*.jpg
Embeddings are cached in data/embeddings.npz.
"""
from pathlib import Path
import json

import cv2
import numpy as np

from src.face_model import FaceModel, cosine

ROOT = Path(__file__).resolve().parents[1]
GALLERY_DIR = ROOT / "data" / "gallery"
CACHE = ROOT / "data" / "embeddings.npz"
CONFIG = ROOT / "mock" / "config.json"

# SFace's published cosine threshold; overwritten by evaluate.py via mock/config.json
DEFAULT_THRESHOLD = 0.363


def load_threshold():
    if CONFIG.exists():
        return json.loads(CONFIG.read_text()).get("threshold", DEFAULT_THRESHOLD)
    return DEFAULT_THRESHOLD


def build_gallery(model: FaceModel, gallery_dir=GALLERY_DIR):
    """Return {code: [embedding, ...]} from images on disk."""
    gallery = {}
    if not gallery_dir.exists():
        return gallery
    for student_dir in sorted(p for p in gallery_dir.iterdir() if p.is_dir()):
        for img_path in student_dir.glob("*.*"):
            img = cv2.imread(str(img_path))
            emb = model.embed(img) if img is not None else None
            if emb is not None:
                gallery.setdefault(student_dir.name, []).append(emb)
    return gallery


def load_gallery(model: FaceModel, rebuild=False):
    if CACHE.exists() and not rebuild:
        data = np.load(CACHE, allow_pickle=True)
        return data["gallery"].item()
    gallery = build_gallery(model)
    if gallery:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        np.savez(CACHE, gallery=np.array(gallery, dtype=object))
    return gallery


def match_face(emb, gallery, candidates, threshold):
    """Best match among `candidates` only. Returns (code or None, score)."""
    best_code, best_score = None, -1.0
    for code in candidates:
        for ref in gallery.get(code, []):
            s = cosine(emb, ref)
            if s > best_score:
                best_code, best_score = code, s
    if best_score >= threshold:
        return best_code, best_score
    return None, best_score


class Verification:
    """Tracks one booking's verification session: each student counted once."""

    def __init__(self, members, min_required=None):
        self.members = list(members)
        self.min_required = min_required or len(self.members)
        self.verified = {}      # code -> score
        self.attempts = 0
        self.rejects = 0

    def submit(self, emb, gallery, threshold):
        self.attempts += 1
        if emb is None:
            self.rejects += 1
            return {"status": "no_face"}
        code, score = match_face(emb, gallery, self.members, threshold)
        if code is None:
            self.rejects += 1
            return {"status": "no_match", "score": score}
        if code in self.verified:
            return {"status": "duplicate", "code": code, "score": score}
        self.verified[code] = score
        return {"status": "verified", "code": code, "score": score}

    @property
    def approved(self):
        return len(self.verified) >= self.min_required

    @property
    def pending(self):
        return [m for m in self.members if m not in self.verified]
