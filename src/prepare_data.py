"""Crop faces, rename students to codes and split 70/15/15 by student.

Input  (private):  data/raw/<any student folder>/*.jpg   (ID photo + normal photo)
Output (private):  data/splits/{train,val,test}/<Student X>/*.jpg
                   data/gallery/<Student X>/*.jpg        (all cropped images, used by the kiosk)
                   data/code_map.csv                      (folder -> code; keep offline, delete at course end)

Usage: python -m src.prepare_data [--seed 42]
"""
import argparse
import csv
import random
import shutil
import string
from pathlib import Path

import cv2

from src.face_model import FaceModel

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SPLITS = ROOT / "data" / "splits"
GALLERY = ROOT / "data" / "gallery"
CODE_MAP = ROOT / "data" / "code_map.csv"
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp"}


def code_for(i):
    """0 -> Student A, 25 -> Student Z, 26 -> Student AA ..."""
    letters = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        letters = string.ascii_uppercase[r] + letters
    return f"Student {letters}"


def main(seed=42):
    model = FaceModel()
    folders = sorted(p for p in RAW.iterdir() if p.is_dir())
    random.Random(seed).shuffle(folders)  # codes do not follow name order

    for d in (SPLITS, GALLERY):
        shutil.rmtree(d, ignore_errors=True)

    n = len(folders)
    n_train, n_val = round(n * 0.70), round(n * 0.15)
    split_of = ["train"] * n_train + ["val"] * n_val + ["test"] * (n - n_train - n_val)

    rows, skipped = [], 0
    for i, (folder, split) in enumerate(zip(folders, split_of)):
        code = code_for(i)
        rows.append({"folder": folder.name, "code": code, "split": split})
        images = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMG_EXT)
        for j, img_path in enumerate(images):
            img = cv2.imread(str(img_path))
            face = model.crop(img) if img is not None else None
            if face is None:
                skipped += 1
                continue
            name = f"{j:02d}.jpg"
            for out in (SPLITS / split / code, GALLERY / code):
                out.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(out / name), face)

    with open(CODE_MAP, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["folder", "code", "split"])
        w.writeheader()
        w.writerows(rows)
    print(f"{n} students -> train {n_train}, val {n_val}, test {n - n_train - n_val}; {skipped} images had no face")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    main(ap.parse_args().seed)
