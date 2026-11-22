"""Evaluate face matching with mock 4-student bookings, and compare the two scorers:
  cosine  = SFace embeddings + cosine similarity (pretrained only)
  trained = SFace embeddings + our trained verification model (src/train_verifier.py)

- Enrol: 1.jpg of each person (the ID card face, or the first face photo).  Probe: the other images.
- People with a single photo are enrolled but never probed (they still make the matching harder).
- Threshold is chosen on the validation split, results are reported on the test split.
- Genuine trial: a booked student's probe must match that student.
- Impostor trial: a non-booked student's probe must be rejected.
- Both scorers see exactly the same bookings. The one with the lower validation FRR (at the target FAR)
  is saved to mock/config.json as "matcher", with its threshold, for the kiosk.

Usage: python -m src.evaluate [--bookings 200] [--target-far 0.01] [--matcher both|cosine|trained]
"""
import argparse
import json
import random
import time
from pathlib import Path

import cv2
import numpy as np

from src.face_model import FaceModel
from src.matcher import CONFIG, load_scorer, match_face
from src.verifier import MODEL_PATH

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ROOT / "data" / "splits"


def load_split(model, split):
    enrol, probes, source = {}, {}, {}
    for d in sorted((SPLITS / split).iterdir()):
        embs = [model.embed(cv2.imread(str(p))) for p in sorted(d.glob("*.jpg"), key=lambda p: int(p.stem))]
        embs = [e for e in embs if e is not None]
        if not embs:
            continue
        enrol[d.name] = [embs[0]]
        if len(embs) >= 2:
            probes[d.name] = embs[1:]
        source[d.name] = json.loads((d / "info.json").read_text()).get("source", "")
    return enrol, probes, source


def trials(enrol, probes, source, n_bookings, rng, scorer):
    """Return list of (score, is_genuine, seconds, source of the probed person) over mock bookings of 4."""
    codes = list(enrol)
    out = []
    for _ in range(n_bookings):
        booked = rng.sample(codes, 4)
        outsiders = [c for c in codes if c not in booked and c in probes]
        for code in booked:
            for emb in probes.get(code, []):
                t = time.perf_counter()
                hit, score = match_face(emb, enrol, booked, -1.0, scorer)
                out.append((score if hit == code else -1.0, True, time.perf_counter() - t, source[code]))
        for code in rng.sample(outsiders, min(4, len(outsiders))):
            emb = rng.choice(probes[code])
            t = time.perf_counter()
            _, score = match_face(emb, enrol, booked, -1.0, scorer)
            out.append((score, False, time.perf_counter() - t, source[code]))
    return out


def rates(results, thr, only=None):
    results = [r for r in results if only is None or r[3] == only]
    gen = [s for s, g, _, _ in results if g]
    imp = [s for s, g, _, _ in results if not g]
    frr = float(np.mean([s < thr for s in gen])) if gen else 0.0
    far = float(np.mean([s >= thr for s in imp])) if imp else 0.0
    correct = sum(s >= thr for s in gen) + sum(s < thr for s in imp)
    return far, frr, correct / len(results)


def choose_threshold(val, target_far):
    grid = np.linspace(0.0, 1.0, 201)
    ok = [t for t in grid if rates(val, t)[0] <= target_far]
    return float(min(ok)) if ok else 0.5


def main(n_bookings, target_far, which="both", seed=0):
    model = FaceModel()
    names = ["cosine", "trained"] if which == "both" else [which]
    if "trained" in names and not MODEL_PATH.exists():
        print("No trained model yet (python -m src.train_verifier); evaluating cosine only.")
        names = ["cosine"]
    val_data, test_data = load_split(model, "val"), load_split(model, "test")

    # Time detection + embedding on one test image (the same for both scorers)
    sample = next((SPLITS / "test").rglob("*.jpg"))
    img = cv2.imread(str(sample))
    t = time.perf_counter()
    for _ in range(10):
        model.embed(img)
    embed_s = (time.perf_counter() - t) / 10

    results = {}
    for name in names:
        scorer = load_scorer(name)
        rng = random.Random(seed)  # same bookings for every scorer
        val = trials(*val_data, n_bookings, rng, scorer)
        # Our model outputs a probability and already learned its boundary (0.5) from ~19,000 pairs;
        # the 15-person validation set is too small to move it (both scorers separate it perfectly).
        thr = 0.5 if name == "trained" else choose_threshold(val, target_far)
        test = trials(*test_data, n_bookings, rng, scorer)
        results[name] = dict(thr=thr, val_frr=rates(val, thr)[1], test=test,
                             seconds=embed_s + float(np.mean([s for _, _, s, _ in test])))

    for name, r in results.items():
        print(f"\n[{name}] threshold {r['thr']:.3f} (validation FAR <= {target_far:.0%}, validation FRR {r['val_frr']:.1%})")
        print(f"Test set ({len(r['test'])} trials)")
        print(f"{'':16}{'accuracy':>10}{'FAR':>8}{'FRR':>8}")
        for label, only in (("All 100 people", None), ("UTP students", "UTP survey"), ("LFW (public)", "LFW (public)")):
            far_s, frr_s, acc_s = rates(r["test"], r["thr"], only)
            print(f"{label:16}{acc_s:>10.1%}{far_s:>8.1%}{frr_s:>8.1%}")
        print(f"Seconds per verification: {r['seconds']:.3f}")
    print("\nFAR = stranger let in, FRR = booked student rejected")

    best = min(results, key=lambda n: (results[n]["val_frr"], n != "cosine"))
    cfg = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    cfg.update(matcher=best, threshold=results[best]["thr"])
    CONFIG.write_text(json.dumps(cfg, indent=2))
    print(f"Kiosk will use '{best}' (lower validation FRR). Saved to {CONFIG.relative_to(ROOT)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bookings", type=int, default=200)
    ap.add_argument("--target-far", type=float, default=0.01)
    ap.add_argument("--matcher", choices=["both", "cosine", "trained"], default="both")
    a = ap.parse_args()
    main(a.bookings, a.target_far, a.matcher)
