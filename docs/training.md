# Building the dataset and evaluating the model

All commands run from the repository folder. Photos stay in `data/` and are never committed.

## 1. Install (once)

```bash
pip install -r requirements.txt
```

The two face models (about 39 MB, OpenCV Zoo) download into `models/` on the first run.

## 2. Put the collected photos in place

Download the Google Forms uploads and keep the two folders as they are:

```
data/collected_utp/front/        face photos (jpg, png, HEIC, or a photo inside .docx)
data/collected_utp/student id/   ID cards (jpg, png or PDF)
```

## 3. Run, in this order

| Step | Command | What it does |
|---|---|---|
| a | `python tools/organize_collected.py` | Pairs face photo and ID card by similar filename, converts PDF/HEIC/Word to JPG, writes `data/utp/001/001_1.jpg` (ID card, only if a face is found on it), `001_2.jpg` (face photo), `info.json`. Skips anyone with no usable face photo. |
| b | `python tools/fetch_open_dataset.py` | Downloads LFW and copies 44 public people into `data/open_lfw/` the same way, with fake names and fake student IDs (`99xxxxxx`). |
| c | `python -m src.prepare_data` | Combines both into 100 people, aligns every face to 112x112, renames them `Student A ...`, splits 70/15/15 by person (each source split separately). Writes `data/splits/`, `data/gallery/` and `data/dataset_manifest.csv`. |
| d | `python -m src.evaluate` | Builds 200 mock bookings of 4, picks the match threshold on the validation set (at most 1% strangers let in), reports accuracy, FAR and FRR on the test set, and saves the threshold to `mock/config.json` for the kiosk. |

`--count` in step b sets how many public people to add: use 100 minus the number of UTP people step a reports.

## What "training" means here

No new network is trained. The pretrained SFace model (trained on millions of faces) turns each face into 128 numbers.
"Training" for this project is:

1. **Enrolment**: store the 128 numbers of each person's ID photo (`1.jpg`).
2. **Threshold**: choose how similar two faces must be to count as the same person, on the validation set.
3. **Evaluation**: measure on the test set people the threshold never saw.

Fine-tuning is only planned if accuracy falls below 90%.

## Result (12 Nov 2026)

Dataset: 56 UTP students (46 with a usable ID card photo) + 44 LFW people = 100. Split 70 / 15 / 15.
Threshold chosen on validation: **0.405**. Test set, 1,600 trials:

| | Accuracy | FAR (stranger let in) | FRR (booked student rejected) |
|---|---|---|---|
| All 100 people | 95.4% | 3.2% | 6.0% |
| UTP students | 92.3% | 5.5% | 9.9% |
| LFW (public) | 100.0% | 0.0% | 0.0% |

Seconds per verification: 0.013 (laptop CPU).

Notes for the report:
- UTP students are harder than LFW because the enrolment photo is a small, printed ID card photo, while LFW pairs are two similar news photos. The UTP figure is the one that matters for IRC.
- The test set has only 15 people (9 UTP), so these percentages can move by several points with a different split.
- 59 face-photo files came from 58 respondents (one uploaded twice). 56 were kept; 2 were left out because no face was detected in their face photo. See `data/utp/pairs.csv`.
- For 9 UTP students no face was detected on the ID card, so only their face photo is used; they are enrolled but cannot be tested as "genuine".
