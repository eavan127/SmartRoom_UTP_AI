"""Train our own face verification model on top of SFace embeddings.

Training data (none of it is in the val/test splits, so evaluation stays fair):
  1. LFW people with 2+ photos, minus the 44 LFW people we use as "students" (data/open_lfw/manifest.csv)
  2. Our train split (data/splits/train): UTP students' ID-card photo vs face photo, plus train LFW people.
     These pairs are the closest to real IRC use, so they are repeated (--project-weight) to count more.

Pairs:
  genuine  = two photos of the same person
  impostor = two photos of different people: one random, one "hard" (the most similar other person)

Model: scikit-learn neural network (MLP, 2 hidden layers) on pair features (see src/verifier.py).
Output: models/verifier.joblib. Then run `python -m src.evaluate` to compare it with plain cosine.

Usage: python -m src.train_verifier [--model logreg|mlp] [--max-per-person 6] [--project-weight 1] [--seed 0]
"""
import argparse
import csv
import itertools
import random
import time
from pathlib import Path

import cv2
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.face_model import FaceModel
from src.verifier import Verifier, pair_features

ROOT = Path(__file__).resolve().parents[1]
LFW = ROOT / "data" / "downloads" / "lfw_home" / "lfw_funneled"
LFW_USED = ROOT / "data" / "open_lfw" / "manifest.csv"
TRAIN_SPLIT = ROOT / "data" / "splits" / "train"
CACHE = ROOT / "data" / "lfw_train_embeddings.npz"


def embed_lfw(model, max_per_person):
    """{lfw_name: [embedding, ...]} for LFW people not used as project students. Cached."""
    if CACHE.exists():
        data = np.load(CACHE, allow_pickle=True)
        if int(data["max_per_person"]) == max_per_person:
            return data["people"].item()
    used = {r["lfw_name"] for r in csv.DictReader(open(LFW_USED, encoding="utf-8"))}
    folders = sorted(p for p in LFW.iterdir() if p.is_dir() and p.name not in used and len(list(p.glob("*.jpg"))) >= 2)
    people, t = {}, time.time()
    for i, d in enumerate(folders, 1):
        embs = [model.embed(cv2.imread(str(p))) for p in sorted(d.glob("*.jpg"))[:max_per_person]]
        embs = [e for e in embs if e is not None]
        if len(embs) >= 2:
            people[d.name] = embs
        if i % 200 == 0:
            print(f"  embedded {i}/{len(folders)} LFW people ({time.time() - t:.0f} s)")
    np.savez(CACHE, people=np.array(people, dtype=object), max_per_person=max_per_person)
    return people


def embed_train_split(model):
    people = {}
    for d in sorted(TRAIN_SPLIT.iterdir()):
        embs = [model.embed(cv2.imread(str(p))) for p in sorted(d.glob("*.jpg"), key=lambda p: int(p.stem))]
        embs = [e for e in embs if e is not None]
        if len(embs) >= 2:
            people["train:" + d.name] = embs
    return people


def make_pairs(people, rng, weight=1, max_genuine=10):
    """Return (features, labels). For every genuine pair add one random and one hard impostor."""
    names = list(people)
    means = np.stack([np.mean(people[n], axis=0) for n in names])
    X, y = [], []
    for i, name in enumerate(names):
        embs = people[name]
        genuine = list(itertools.combinations(range(len(embs)), 2))
        rng.shuffle(genuine)
        # hardest other people for this person (highest cosine of the mean faces)
        sims = means @ means[i]
        sims[i] = -2
        hard = [names[j] for j in np.argsort(sims)[-5:]]
        for a, b in genuine[:max_genuine]:
            for _ in range(weight):
                X.append(pair_features(embs[a], embs[b])[0]); y.append(1)
                other = rng.choice(names)
                while other == name:
                    other = rng.choice(names)
                X.append(pair_features(embs[a], rng.choice(people[other]))[0]); y.append(0)
                X.append(pair_features(embs[b], rng.choice(people[rng.choice(hard)]))[0]); y.append(0)
    return np.array(X), np.array(y)


def main(max_per_person, project_weight, seed, kind="logreg"):
    rng = random.Random(seed)
    model = FaceModel()
    t0 = time.time()
    print("Embedding LFW training people (first run takes a few minutes, then cached) ...")
    lfw = embed_lfw(model, max_per_person)
    project = embed_train_split(model)
    print(f"LFW people: {len(lfw)} ({sum(map(len, lfw.values()))} photos) · project train people: {len(project)}")

    # Hold out 10% of people (not pairs) to check the model on unseen faces
    names = list(lfw)
    rng.shuffle(names)
    hold = set(names[: len(names) // 10])
    X_tr, y_tr = make_pairs({n: lfw[n] for n in lfw if n not in hold}, rng)
    X_pr, y_pr = make_pairs(project, rng, weight=project_weight)
    X_tr, y_tr = np.vstack([X_tr, X_pr]), np.concatenate([y_tr, y_pr])
    X_ho, y_ho = make_pairs({n: lfw[n] for n in hold}, rng)
    print(f"Training pairs: {len(y_tr)} ({y_tr.mean():.0%} genuine) · held-out pairs: {len(y_ho)}")

    if kind == "logreg":
        clf = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=2000))
    else:
        clf = make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(128, 32), alpha=1e-3,
                                                            early_stopping=True, max_iter=300, random_state=seed))
    clf.fit(X_tr, y_tr)
    mlp = clf[-1]

    p_ho = clf.predict_proba(X_ho)[:, 1]
    cos_ho = X_ho[:, :128].sum(axis=1)  # a*b summed = cosine similarity (the baseline)
    acc = float(np.mean((p_ho >= 0.5) == y_ho))
    epochs = int(np.max(mlp.n_iter_))
    print(f"\nTrained {kind} in {time.time() - t0:.0f} s, {epochs} iterations")
    print(f"Held-out people  accuracy {acc:.1%} · AUC ours {roc_auc_score(y_ho, p_ho):.4f} "
          f"vs cosine {roc_auc_score(y_ho, cos_ho):.4f}")

    Verifier(clf, {"lfw_people": len(lfw), "project_people": len(project), "pairs": int(len(y_tr)),
                   "model": kind, "project_weight": project_weight, "epochs": epochs,
                   "heldout_accuracy": acc,
                   "loss_curve": [float(v) for v in getattr(mlp, "loss_curve_", [])],
                   "val_curve": [float(v) for v in getattr(mlp, "validation_scores_", None) or []]}).save()
    print("Saved models/verifier.joblib. Next: python -m src.evaluate")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-per-person", type=int, default=6)
    ap.add_argument("--project-weight", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", choices=["mlp", "logreg"], default="logreg")
    a = ap.parse_args()
    main(a.max_per_person, a.project_weight, a.seed, a.model)
