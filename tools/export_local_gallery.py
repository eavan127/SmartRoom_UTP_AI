"""Enrol the collected UTP students into the kiosk, on THIS laptop only.

Reads data/utp/<NNN>/ (made by tools/organize_collected.py) and writes prototype/local_gallery.js:
  window.LOCAL_GALLERY   "UTP 001" -> name + 128 numbers for every photo of that student (ID card and face photo)
  window.LOCAL_BOOKINGS  test bookings of 4 students, so every student belongs to one booking

prototype/local_gallery.js is in .gitignore: it is derived from real students' faces and must never be
pushed to GitHub or deployed. The kiosk loads it only when the file exists (your laptop), so the hosted
site keeps only the public LFW demo people. Delete the file at the end of the course.

Usage: python tools/export_local_gallery.py
"""
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.face_model import FaceModel  # noqa: E402

UTP = ROOT / "data" / "utp"
OUT_JS = ROOT / "prototype" / "local_gallery.js"
GROUP = 4
# Demo booking Discussion Room 1 (Student A-D) = the project team, replacing the LFW demo faces locally.
# folder in data/utp, or None = no photo collected (enrol with the camera under Staff -> Enrol faces)
TEAM = {
    "Student A": ("013", "Eavan Tan", "24006152"),
    "Student B": ("019", "Nur Alyaa Nabilah", "25014139"),
    "Student C": ("031", "Margareta Vieira", "24007376"),
    "Student D": ("023", "Ivy Rachel Richard", "25014556"),
}


def main():
    model = FaceModel()
    gallery = {}
    for folder in sorted(p for p in UTP.iterdir() if p.is_dir()):
        info = json.loads((folder / "info.json").read_text())
        embs = [model.embed(cv2.imread(str(p))) for p in sorted(folder.glob("*.jpg"))]
        embs = [[round(float(v), 5) for v in e] for e in embs if e is not None]
        if embs:
            gallery[f"UTP {folder.name}"] = {"name": info["name"], "student_id": info.get("student_id", ""),
                                            "faces": embs}

    codes = list(gallery)
    bookings = []
    for g, i in enumerate(range(0, len(codes), GROUP), start=1):
        members = codes[i:i + GROUP]
        start = 9 + (g - 1) % 6 * 2                      # 09:00, 11:00, ... 19:00
        bookings.append({"id": f"UTP-TEST-{g:02d}", "room": f"Test Group {g:02d}", "level": "Level 2",
                         "slot": f"{start:02d}:00 - {start + 2:02d}:00", "by": members[0], "members": members})

    for code, (num, name, sid) in TEAM.items():
        faces = gallery[f"UTP {num}"]["faces"] if num else []
        gallery[code] = {"name": name, "student_id": sid, "faces": faces}
        print(f"{code} = {name} ({sid}): {len(faces) or 'no'} photo(s)" + ("" if num else ", enrol with the camera"))
    print()

    OUT_JS.write_text(
        "/* LOCAL ONLY - real UTP students' face data. Never commit or deploy (see .gitignore). */\n"
        f"window.LOCAL_GALLERY = {json.dumps(gallery)};\n"
        f"window.LOCAL_BOOKINGS = {json.dumps(bookings)};\n", encoding="utf-8")

    print(f"{len(codes)} UTP students enrolled, "
          f"{len(bookings)} test bookings -> {OUT_JS.relative_to(ROOT)}\n")
    for b in bookings:
        print(f"  {b['room']}: " + ", ".join(f"{m} {gallery[m]['name']}" for m in b["members"]))


if __name__ == "__main__":
    main()
