"""Pre-enrol the kiosk with public LFW people so it can recognise faces with no setup.

Booking members Student A, B, C ... are mapped to LFW people 001, 002, 003 ... (data/open_lfw/).
Only public LFW faces are used, never the UTP students, because the kiosk site is public.

Output:
  prototype/demo_gallery.js            128 numbers per person from photo _1, plus fake name and student ID
  data/demo_test_photos/<booking>/...  photo _2 of each person, to show to the camera (not committed)

Usage: python tools/export_demo_gallery.py
"""
import json
import shutil
import string
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.face_model import FaceModel  # noqa: E402

LFW = ROOT / "data" / "open_lfw"
OUT_JS = ROOT / "prototype" / "demo_gallery.js"
PHOTOS = ROOT / "data" / "demo_test_photos"
# Same mock bookings as prototype/index.html
BOOKINGS = {
    "Discussion Room 1": "ABCD",
    "Discussion Room 3": "EFGH",
    "Discussion Room 5": "BIJK",
    "Meeting Room 2": "LMNO",
}


def main():
    model = FaceModel()
    letters = sorted({c for members in BOOKINGS.values() for c in members})
    gallery = {}
    for i, letter in enumerate(letters, start=1):
        num = f"{i:03d}"
        info = json.loads((LFW / num / "info.json").read_text())
        enrol = model.embed(cv2.imread(str(LFW / num / f"{num}_1.jpg")))
        probe = model.embed(cv2.imread(str(LFW / num / f"{num}_2.jpg")))
        score = float(enrol @ probe)
        gallery[f"Student {letter}"] = {
            "name": info["name"], "student_id": info["student_id"], "programme": info["programme"],
            "faces": [[round(float(v), 5) for v in enrol]],
        }
        print(f"Student {letter} = LFW {num} {info['name']:<20} photo 2 vs photo 1: {score:.2f}")

    OUT_JS.write_text(
        "/* Demo enrolments: public LFW faces (made by tools/export_demo_gallery.py). No UTP student data. */\n"
        f"window.DEMO_GALLERY = {json.dumps(gallery)};\n")

    shutil.rmtree(PHOTOS, ignore_errors=True)
    for room, members in BOOKINGS.items():
        folder = PHOTOS / room
        folder.mkdir(parents=True)
        for letter in members:
            num = f"{letters.index(letter) + 1:03d}"
            name = gallery[f"Student {letter}"]["name"]
            shutil.copy(LFW / num / f"{num}_2.jpg", folder / f"Student {letter} - {name}.jpg")
    print(f"\nWrote {OUT_JS.relative_to(ROOT)} and test photos in {PHOTOS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
