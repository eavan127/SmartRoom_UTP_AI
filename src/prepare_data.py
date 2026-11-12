"""Combine UTP and LFW people, crop faces, give codes and split 70/15/15 by person.

Input (made by tools/organize_collected.py and tools/fetch_open_dataset.py):
  data/utp/<NNN>/<NNN>_1.jpg ...      _1 = ID card (if it has a face), _2+ = face photos
  data/open_lfw/<NNN>/<NNN>_1.jpg ...
  each folder has info.json (name, student_id, ...)
Output:
  data/splits/{train,val,test}/<Student X>/<n>.jpg   aligned 112x112 faces, 1.jpg = enrolment photo
  data/splits/{train,val,test}/<Student X>/info.json
  data/gallery/<Student X>/...                       same crops, used by the kiosk
  data/dataset_manifest.csv                          code, source, split, images, name, student_id
Each source is split 70/15/15 on its own, so UTP and LFW people appear in all three sets.

Usage: python -m src.prepare_data [--seed 42]
"""
import argparse
import csv
import json
import random
import shutil
import string
from pathlib import Path

import cv2

from src.face_model import FaceModel

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {"UTP survey": ROOT / "data" / "utp", "LFW (public)": ROOT / "data" / "open_lfw"}
SPLITS = ROOT / "data" / "splits"
GALLERY = ROOT / "data" / "gallery"
MANIFEST = ROOT / "data" / "dataset_manifest.csv"


def code_for(i):
    """0 -> Student A, 25 -> Student Z, 26 -> Student AA ..."""
    letters = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        letters = string.ascii_uppercase[r] + letters
    return f"Student {letters}"


def split_people(folders, rng):
    folders = folders[:]
    rng.shuffle(folders)
    n = len(folders)
    n_train, n_val = round(n * 0.70), round(n * 0.15)
    return {"train": folders[:n_train], "val": folders[n_train:n_train + n_val], "test": folders[n_train + n_val:]}


def main(seed=42):
    rng = random.Random(seed)
    model = FaceModel()
    for d in (SPLITS, GALLERY):
        shutil.rmtree(d, ignore_errors=True)

    plan = []  # (source, split, folder)
    for source, root in SOURCES.items():
        folders = sorted(p for p in root.iterdir() if p.is_dir())
        for split, people in split_people(folders, rng).items():
            plan += [(source, split, f) for f in people]
    rng.shuffle(plan)  # codes do not reveal the source

    rows, skipped = [], 0
    for i, (source, split, folder) in enumerate(plan):
        code = code_for(i)
        info = json.loads((folder / "info.json").read_text())
        n_img = 0
        for img_path in sorted(folder.glob("*.jpg")):  # _1 (ID card) sorts first = enrolment photo
            img = cv2.imread(str(img_path))
            face = model.align(img) if img is not None else None
            if face is None:
                skipped += 1
                continue
            n_img += 1
            for out in (SPLITS / split / code, GALLERY / code):
                out.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(out / f"{n_img}.jpg"), face)
        if n_img == 0:
            continue
        info.update(code=code, split=split)
        (SPLITS / split / code / "info.json").write_text(json.dumps(info, indent=2))
        rows.append({"code": code, "source": source, "split": split, "images": n_img,
                     "folder": f"{folder.parent.name}/{folder.name}",
                     "name": info.get("name", ""), "student_id": info.get("student_id", "")})

    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["code", "source", "split", "images", "folder", "name", "student_id"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (len(r["code"]), r["code"])))

    print(f"{len(rows)} people, {skipped} images without a face skipped\n")
    print(f"{'':14}{'train':>7}{'val':>7}{'test':>7}{'total':>7}")
    for source in list(SOURCES) + ["Total"]:
        sel = [r for r in rows if source in ("Total", r["source"])]
        counts = [sum(r["split"] == s for r in sel) for s in ("train", "val", "test")]
        print(f"{source:14}" + "".join(f"{c:>7}" for c in counts) + f"{len(sel):>7}")
    print(f"\nPeople with 2+ photos (can be tested as genuine): {sum(r['images'] >= 2 for r in rows)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    main(ap.parse_args().seed)
