"""Evaluate the pretrained model with mock 4-student bookings.

- Enrol: first image of each student (the ID photo).  Probe: remaining images.
- Threshold is chosen on the validation split, results are reported on the test split.
- Genuine trial: a booked student's probe must match that student.
- Impostor trial: a non-booked student's probe must be rejected.

Usage: python -m src.evaluate [--bookings 200] [--target-far 0.01]
"""
import argparse
import json
import random
import time
from pathlib import Path

import cv2
import numpy as np

from src.face_model import FaceModel
from src.matcher import CONFIG, match_face

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ROOT / "data" / "splits"


def load_split(model, split):
    enrol, probes = {}, {}
    for d in sorted((SPLITS / split).iterdir()):
        embs = [model.embed(cv2.imread(str(p))) for p in sorted(d.glob("*.jpg"))]
        embs = [e for e in embs if e is not None]
        if len(embs) >= 2:
            enrol[d.name] = [embs[0]]
            probes[d.name] = embs[1:]
    return enrol, probes


def trials(enrol, probes, n_bookings, rng):
    """Return list of (score, is_genuine, seconds) over mock bookings of 4."""
    codes = list(enrol)
    out = []
    for _ in range(n_bookings):
        booked = rng.sample(codes, 4)
        outsiders = [c for c in codes if c not in booked]
        for code in booked:
            for emb in probes[code]:
                t = time.perf_counter()
                hit, score = match_face(emb, enrol, booked, -1.0)
                out.append((score if hit == code else -1.0, True, time.perf_counter() - t))
        for code in rng.sample(outsiders, min(4, len(outsiders))):
            emb = rng.choice(probes[code])
            t = time.perf_counter()
            _, score = match_face(emb, enrol, booked, -1.0)
            out.append((score, False, time.perf_counter() - t))
    return out


def rates(results, thr):
    gen = [s for s, g, _ in results if g]
    imp = [s for s, g, _ in results if not g]
    frr = float(np.mean([s < thr for s in gen])) if gen else 0.0
    far = float(np.mean([s >= thr for s in imp])) if imp else 0.0
    correct = sum(s >= thr for s in gen) + sum(s < thr for s in imp)
    return far, frr, correct / len(results)


def main(n_bookings, target_far, seed=0):
    rng = random.Random(seed)
    model = FaceModel()

    val = trials(*load_split(model, "val"), n_bookings, rng)
    grid = np.linspace(0.0, 1.0, 201)
    ok = [t for t in grid if rates(val, t)[0] <= target_far]
    thr = float(min(ok)) if ok else 0.5
    print(f"Chosen threshold on validation (FAR <= {target_far:.0%}): {thr:.3f}")

    # Time the full pipeline (detect + embed + match) on one test image
    sample = next((SPLITS / "test").rglob("*.jpg"))
    img = cv2.imread(str(sample))
    t = time.perf_counter()
    for _ in range(10):
        model.embed(img)
    embed_s = (time.perf_counter() - t) / 10

    test = trials(*load_split(model, "test"), n_bookings, rng)
    far, frr, acc = rates(test, thr)
    match_s = float(np.mean([s for _, _, s in test]))
    report = {
        "threshold": thr, "far": far, "frr": frr, "accuracy": acc,
        "seconds_per_verification": embed_s + match_s, "test_trials": len(test),
    }
    print(json.dumps(report, indent=2))

    cfg = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    cfg["threshold"] = thr
    CONFIG.write_text(json.dumps(cfg, indent=2))
    print(f"Saved threshold to {CONFIG.relative_to(ROOT)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bookings", type=int, default=200)
    ap.add_argument("--target-far", type=float, default=0.01)
    a = ap.parse_args()
    main(a.bookings, a.target_far)
