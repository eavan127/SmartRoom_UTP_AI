"""Pair the collected Google Forms uploads by filename and arrange them like open_lfw/.

Input (as downloaded, unsorted):
  data/collected_utp/front/<name>.<jpg|jpeg|png|HEIC|docx>     face photo
  data/collected_utp/student id/<name>.<jpg|jpeg|png|pdf>       student ID card

Files whose names are similar belong to the same person (Forms adds " - <respondent>").
Output:
  data/utp/001/001_1.jpg    student ID card, only if a face is detected on it (enrolment photo)
  data/utp/001/001_2.jpg    face photo (and 001_3.jpg ... if someone uploaded more than one)
  data/utp/001/info.json    name (from the filename), source, which photos exist
  data/utp/pairs.csv        number -> original filenames (private) and match score
Respondents with no face photo are skipped and listed at the end.

Usage: python tools/organize_collected.py
"""
import csv
import difflib
import io
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

import cv2
import fitz  # PyMuPDF, for PDF ID cards
import numpy as np
import pillow_heif
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.face_model import FaceModel  # noqa: E402

SRC = ROOT / "data" / "collected_utp"
OUT = ROOT / "data" / "utp"
NOISE = re.compile(r"front face|matric card|student ?id|photo|_", re.I)
MIN_SCORE = 0.6

pillow_heif.register_heif_opener()


def key(path):
    """Comparable name: the respondent part after ' - ', lower case, letters only."""
    stem = path.stem
    parts = [p for p in stem.split(" - ") if p.strip()]
    name = parts[-1] if len(parts) > 1 else stem
    name = NOISE.sub(" ", name)
    return "".join(ch for ch in name.lower() if ch.isalpha())


def display_name(path):
    stem = path.stem.split(" - ")[-1]
    return " ".join(NOISE.sub(" ", stem).split()).title()


def similarity(a, b):
    if not a or not b:
        return 0.0
    if a in b or b in a:  # "dania" vs "qaseehdaniaaisyah" stays low unless lengths are close
        return max(difflib.SequenceMatcher(None, a, b).ratio(), min(len(a), len(b)) / max(len(a), len(b)))
    return difflib.SequenceMatcher(None, a, b).ratio()


def load_image(path):
    """Return a BGR image from jpg/png/HEIC, the first PDF page, or the largest image in a .docx."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        page = fitz.open(path)[0]
        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
    elif ext == ".docx":
        with zipfile.ZipFile(path) as z:
            media = [n for n in z.namelist() if n.startswith("word/media/")]
            if not media:
                return None
            img = Image.open(io.BytesIO(z.read(max(media, key=lambda n: z.getinfo(n).file_size))))
    else:
        img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # phone photos are stored sideways with a rotation tag
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)


def pair(fronts, ids):
    """Greedy best-score matching of ID cards to face photos (each ID used once)."""
    scores = sorted(((similarity(key(f), key(i)), f, i) for f in fronts for i in ids), key=lambda t: -t[0])
    match, used = {}, set()
    for s, f, i in scores:
        if s >= MIN_SCORE and f not in match and i not in used:
            match[f] = (i, s)
            used.add(i)
    return match, [i for i in ids if i not in used]


def main():
    fronts = sorted(p for p in (SRC / "front").iterdir() if p.is_file())
    ids = sorted(p for p in (SRC / "student id").iterdir() if p.is_file())

    # Someone may upload two face photos: group fronts with identical keys first
    people = {}
    for f in fronts:
        people.setdefault(key(f), []).append(f)
    match, unmatched_ids = pair([fs[0] for fs in people.values()], ids)

    model = FaceModel()
    shutil.rmtree(OUT, ignore_errors=True)
    rows, problems = [], []
    n = 0
    for k, fs in sorted(people.items(), key=lambda kv: kv[1][0].name.lower()):
        faces = []
        for f in fs:
            img = load_image(f)
            if img is None or model.detect(img) is None:
                problems.append(f"no face found in face photo: {f.name}")
                continue
            faces.append(img)
        if not faces:
            continue
        id_file, score = match.get(fs[0], (None, 0.0))
        id_img = load_image(id_file) if id_file else None
        id_has_face = id_img is not None and model.detect(id_img) is not None

        n += 1
        num = f"{n:03d}"
        folder = OUT / num
        folder.mkdir(parents=True)
        photos = ([id_img] if id_has_face else []) + faces
        start = 1 if id_has_face else 2  # _1 is always the ID card, _2+ are face photos
        for j, img in enumerate(photos, start=start):
            cv2.imwrite(str(folder / f"{num}_{j}.jpg"), img)
        info = {"number": num, "name": display_name(fs[0]), "student_id": "", "source": "UTP survey",
                "id_card": "used" if id_has_face else ("no face detected" if id_file else "not uploaded"),
                "face_photos": len(faces)}
        (folder / "info.json").write_text(json.dumps(info, indent=2))
        rows.append({"number": num, "face_files": "; ".join(f.name for f in fs),
                     "id_file": id_file.name if id_file else "", "match_score": round(score, 2),
                     "id_card": info["id_card"]})

    with open(OUT / "pairs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["number", "face_files", "id_file", "match_score", "id_card"])
        w.writeheader()
        w.writerows(rows)

    print(f"{n} people arranged in {OUT.relative_to(ROOT)}")
    print(f"  ID card used: {sum(r['id_card'] == 'used' for r in rows)}, "
          f"no face on card: {sum(r['id_card'] == 'no face detected' for r in rows)}, "
          f"no card: {sum(r['id_card'] == 'not uploaded' for r in rows)}")
    print("\nCheck these pairs (lowest scores):")
    for r in sorted(rows, key=lambda r: r["match_score"])[:8]:
        print(f"  {r['number']}  {r['match_score']:.2f}  {r['face_files']}  <->  {r['id_file'] or '-'}")
    if unmatched_ids:
        print("\nID cards with no face photo (skipped):")
        for i in unmatched_ids:
            print("  ", i.name)
    for p in problems:
        print("  ", p)


if __name__ == "__main__":
    main()
