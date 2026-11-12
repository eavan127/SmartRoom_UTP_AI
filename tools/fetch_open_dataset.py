"""Download LFW into the repo and copy N people with 2 photos each into data/open_lfw/.

Output (not committed, see .gitignore):
  data/downloads/lfw_home/...        full LFW download (about 200 MB, can be deleted afterwards)
  data/open_lfw/001/001_1.jpg        person 001, photo 1 (used as the "ID photo")
  data/open_lfw/001/001_2.jpg        person 001, photo 2 (used as the "normal photo")
  ...
  data/open_lfw/001/info.json        fake name, fake student ID, programme (shown by the kiosk on a match)
  data/open_lfw/profiles.csv         all fake profiles in one table
  data/open_lfw/manifest.csv         number -> real LFW name (keep private)

Fake student IDs start with 99 so they can never clash with a real UTP ID (real ones start 2x).

People are chosen at random with a fixed seed, only from LFW people with at least 2 photos.

Usage: python tools/fetch_open_dataset.py [--count 41] [--seed 42]
"""
import argparse
import csv
import json
import random
import shutil
from pathlib import Path

from sklearn.datasets import fetch_lfw_people

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "data" / "downloads"
OUT = ROOT / "data" / "open_lfw"

FIRST_F = ["Aisyah", "Nurul", "Sofea", "Alya", "Hana", "Mei Ling", "Xin Yi", "Jia Hui", "Priya", "Divya",
           "Sarah", "Emily", "Nadia", "Zara", "Chloe"]
FIRST_M = ["Aiman", "Hakim", "Danish", "Irfan", "Haziq", "Wei Jie", "Jun Hao", "Kai Xuan", "Arvin", "Kavin",
           "Daniel", "Ryan", "Adam", "Ethan", "Iman"]
# People (for the default seed 42) whose photos look female, checked by eye so the fake name fits the face.
# If you change --seed or --count, check the photos again and update this set.
FEMALE = {1, 3, 8, 13, 17, 18, 22, 28, 31, 40, 41}
BASE = 41
LAST = ["Rahman", "Ismail", "Hassan", "Yusof", "Aziz", "Tan", "Lim", "Wong", "Lee", "Ng",
        "Kumar", "Raj", "Pillai", "Nair", "Ahmad", "Chong", "Teo", "Sim", "Musa", "Osman"]
PROGRAMMES = ["Computer Science", "Information Technology", "Chemical Engineering", "Petroleum Engineering",
              "Mechanical Engineering", "Electrical and Electronic Engineering", "Civil Engineering", "Geoscience"]


def fake_profiles(count, rng):
    """Unique fake names and student IDs (99xxxxxx, never a real UTP ID)."""
    # Shuffle the whole pool so person N keeps the same name whatever --count is
    pools = {True: rng.sample([f"{f} {l}" for f in FIRST_F for l in LAST], len(FIRST_F) * len(LAST)),
             False: rng.sample([f"{f} {l}" for f in FIRST_M for l in LAST], len(FIRST_M) * len(LAST))}
    return [{"name": pools[i in FEMALE].pop(), "student_id": f"99{i:06d}", "programme": rng.choice(PROGRAMMES)}
            for i in range(1, count + 1)]


def main(count, seed):
    # Downloads the whole LFW archive once; later runs reuse it
    fetch_lfw_people(data_home=str(DOWNLOADS), min_faces_per_person=2, download_if_missing=True)
    lfw = DOWNLOADS / "lfw_home" / "lfw_funneled"

    people = sorted(p for p in lfw.iterdir() if p.is_dir() and len(list(p.glob("*.jpg"))) >= 2)
    # The first 41 are fixed; extra people are drawn from the rest, so 001-041 never change
    rng = random.Random(seed)
    chosen = rng.sample(people, BASE)
    chosen = chosen[:count] + rng.sample([p for p in people if p not in chosen], max(0, count - BASE))

    profiles = fake_profiles(count, random.Random(seed + 1))

    shutil.rmtree(OUT, ignore_errors=True)
    rows, table = [], []
    for i, person in enumerate(chosen, start=1):
        num = f"{i:03d}"
        folder = OUT / num
        folder.mkdir(parents=True)
        photos = sorted(person.glob("*.jpg"))[:2]
        for j, src in enumerate(photos, start=1):
            shutil.copy(src, folder / f"{num}_{j}.jpg")
        info = {"number": num, **profiles[i - 1], "source": "LFW (public)"}
        (folder / "info.json").write_text(json.dumps(info, indent=2))
        table.append(info)
        rows.append({"number": num, "lfw_name": person.name,
                     "photo_1": photos[0].name, "photo_2": photos[1].name})

    with open(OUT / "manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["number", "lfw_name", "photo_1", "photo_2"])
        w.writeheader()
        w.writerows(rows)
    with open(OUT / "profiles.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["number", "name", "student_id", "programme", "source"])
        w.writeheader()
        w.writerows(table)
    print(f"Copied {count} of {len(people)} LFW people (seed {seed}) into {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=44, help="people to add, e.g. 100 minus usable UTP students")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    main(a.count, a.seed)
