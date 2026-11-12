# Datasets

Photos in this folder are **never committed**. Git tracks only this README and the `.gitkeep`/README files that keep the layout.
All images are deleted at the end of the course.

## Layout

```
data/
├── open_lfw/              41 public people from LFW (made by tools/fetch_open_dataset.py)
│   ├── 001/
│   │   ├── 001_1.jpg      photo 1, used as the "ID photo" (enrolment)
│   │   ├── 001_2.jpg      photo 2, used as the "normal photo" (probe)
│   │   └── info.json      fake name, fake student ID, programme
│   ├── 002/ ...
│   ├── profiles.csv       all fake profiles in one table
│   └── manifest.csv       number -> real LFW name (private, do not share)
├── collected_utp/         drop ALL Google Forms photos here, unsorted (see its README)
└── downloads/             full LFW download cache (about 200 MB, safe to delete)
```

Same rule for every person: one folder, `<number>_1` = ID photo, `<number>_2` = normal photo.

## Rebuild the open dataset

```bash
pip install scikit-learn
python tools/fetch_open_dataset.py
```

- 41 people chosen at random (seed 42) from the 1,680 LFW people with at least 2 photos.
- Fake student IDs start with `99`, so they can never match a real UTP student ID.
- Fake names are matched to how each face looks (female/male name lists). Change `--seed` or `--count` and you must re-check this.

## Sources

- LFW: G. B. Huang, M. Ramesh, T. Berg, E. Learned-Miller, *Labeled Faces in the Wild: A Database for Studying Face Recognition in Unconstrained Environments*, UMass Amherst Technical Report 07-49, 2007. Used for research only.
- UTP students: 59 respondents of the Group 2 survey (29 Oct - 7 Nov 2026) who gave consent.
