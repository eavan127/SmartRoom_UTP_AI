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
| d | `python -m src.train_verifier` | Trains **our own verification model** (see below) and saves it to `models/verifier.joblib`. About 3 minutes the first time (embeds the LFW photos once, then cached). |
| e | `python -m src.evaluate` | Builds 200 mock bookings of 4 and compares both scorers on the same bookings: picks the cosine threshold on the validation set (at most 1% strangers let in), reports accuracy, FAR and FRR on the test set, and saves the better scorer (`matcher`) and its threshold to `mock/config.json` for the kiosk. |

`--count` in step b sets how many public people to add: use 100 minus the number of UTP people step a reports.

## What is pretrained and what we trained

| Step | Model | Who trained it |
|---|---|---|
| Find the face | YuNet (OpenCV Zoo) | Pretrained, not changed |
| Face to 128 numbers | SFace (OpenCV Zoo) | Pretrained on millions of faces, not changed |
| Same person or not? | **Our verification model** (`src/train_verifier.py`) | **Trained by us** |

Our verification model is a logistic regression on pair features of two embeddings (element-wise product and
absolute difference, 256 inputs). It is trained on **19,000+ face pairs**: 1,636 LFW people who are *not* among our
44 "student" LFW people, plus the train split (UTP ID photo vs face photo). Pairs are 1/3 genuine, 2/3 impostor
(one random, one "hard": the most similar other person). 10% of LFW people are held out to check it.
A 2-layer neural network (MLP) and heavier weighting of the UTP pairs were also tried; they did not do better on held-out people.

The baseline is the plain cosine similarity of the two embeddings (no training, only a threshold).

## Result (22 Nov 2026)

Dataset: 56 UTP students (46 with a usable ID card photo) + 44 LFW people = 100. Split 70 / 15 / 15.
Same 1,600 test trials for both scorers.

| Scorer | Threshold | Accuracy | FAR (stranger let in) | FRR (booked student rejected) | UTP accuracy | UTP FAR | UTP FRR |
|---|---|---|---|---|---|---|---|
| Cosine (pretrained only) | 0.41 (validation) | **96.2%** | **1.6%** | 6.0% | **93.6%** | **2.7%** | 9.9% |
| Our trained model | 0.5 (its own boundary) | 95.4% | 3.2% | 6.0% | 92.3% | 5.5% | 9.9% |

LFW people: 100% for both. Seconds per verification: about 0.013 (laptop CPU).
Held-out LFW people (2,274 pairs): our model 99.1% accuracy, AUC 0.994 vs cosine 0.993.

**The kiosk uses cosine**, because it was at least as good on validation and better on test.
Our model is slightly better on held-out LFW people but slightly worse on UTP students: it learned mostly from LFW
news photos, while UTP enrolment uses small printed ID photos, and only ~40 UTP people were available to train on.
More UTP training pairs (the planned pilot) are the way to make it beat the baseline.

Notes for the report:
- UTP students are harder than LFW because the enrolment photo is a small, printed ID card photo, while LFW pairs are two similar news photos. The UTP figure is the one that matters for IRC.
- The test set has only 15 people (9 UTP), so these percentages can move by several points with a different split.
- 59 face-photo files came from 58 respondents (one uploaded twice). 56 were kept; 2 were left out because no face was detected in their face photo. See `data/utp/pairs.csv`.
- For 9 UTP students no face was detected on the ID card, so only their face photo is used; they are enrolled but cannot be tested as "genuine".
