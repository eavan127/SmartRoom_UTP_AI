# Running and hosting the kiosk

The kiosk is two static files: `prototype/index.html` and `prototype/face.js`.
The face model runs **inside the browser** (onnxruntime-web), so no Python server is needed to host it.

## How the face model gets into the page

| Piece | Where it comes from |
|---|---|
| YuNet detector (0.2 MB) and SFace recogniser (39 MB), the same `.onnx` files as `models/` | Downloaded by the browser from the OpenCV mirror on Hugging Face, once, then cached |
| onnxruntime-web 1.20.1 (runs `.onnx` in the browser) | jsDelivr CDN |
| Match threshold 0.41 | Chosen by `python -m src.evaluate`, written into `CFG.threshold` in `index.html` |
| Enrolled faces | Captured on the kiosk under **Staff → Enrol faces**, stored in that browser only (128 numbers per face, no photos) |

The browser pipeline was checked against the Python one: same person 0.71 vs 0.70, different people 0.24 vs 0.22.
If you re-run `evaluate.py` and the threshold changes, update `CFG.threshold` in `index.html`.

## Live mode vs simulation

- **Live** (default): the browser asks for camera permission; the first time, the model downloads (about 39 MB).
- **Simulation**: no camera, results are simulated. Turn it on with Staff (PIN `1234`) → Settings → untick **Live camera and face model**, or open the page with `?sim`. The screenshot script uses this.

## Run on your laptop

The camera only works on `https://` or `localhost`, so start a tiny local server from the repo folder:

```bash
python -m http.server 8000
```

Then open <http://localhost:8000/prototype/>.

## Host online

### Option A: GitHub Pages (automatic, recommended)

The repo already contains `.github/workflows/pages.yml`, which publishes only the `prototype/` folder.

1. Push the workflow and `prototype/` to the `main` branch.
2. On GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Open the **Actions** tab and wait for "Deploy kiosk to GitHub Pages" to turn green (about 1 minute).
4. The site is at **https://eavan127.github.io/SmartRoom_UTP_AI/** (camera is on by default).

Every later push that changes `prototype/` redeploys automatically.
GitHub Pages is free for public repos. For a private repo you need GitHub Pro, which is free with the GitHub Student Developer Pack.

### Option B: Netlify Drop (no git, 1 minute)

1. Go to <https://app.netlify.com/drop> and sign in.
2. Drag the `prototype` folder onto the page.
3. Netlify gives you an `https://….netlify.app` link. To update, drag the folder again.

## Built-in demo people (works with no enrolment)

`prototype/demo_gallery.js` pre-enrols the booking members with public LFW faces (made by `python tools/export_demo_gallery.py`):
Student A-O = LFW people 001-015, with their fake names and student IDs. On a match the kiosk shows e.g.
"✓ Student A: Sarah Rahman (99000001) verified".

To test without your team: open `data/demo_test_photos/<room>/` on your phone (these are each person's *other* photo,
not the one enrolled), choose that room's booking on the kiosk, and hold each photo up to the webcam.
UTP students are never included here, because the site is public.

## Sharing captured faces with teammates

Faces captured with **Capture face** are saved in that browser only. To give a teammate the same enrolments:

1. On your kiosk: Staff → **Enrol faces** → **Export faces**. A file `smartroom-faces-<date>.json` downloads.
2. Send it to the teammate privately (team WhatsApp or the private team Drive). It holds face data (128 numbers per face, no photos), so never post it publicly or commit it (git ignores `smartroom-faces*.json`).
3. On their kiosk (hosted site or localhost): Staff → **Enrol faces** → **Import faces** → choose the file.

Importing adds to what is already there and skips faces it already has, so it is safe to import the same file twice
or to combine files from several teammates. Bookings still reset every time the page opens; faces stay.

## Demo checklist

1. Open the hosted link on the laptop that will act as the kiosk and allow the camera.
2. Staff → Enrol faces: enrol each team member 2-3 times as Student A, B, C, D.
3. Exit staff → Collect Room Card → Discussion Room 1 → each member presses **Scan face**.
4. Record the scenarios (all verified, stranger, missing member + staff override, return).

## Privacy

- The hosted site contains no student data: only the two files above.
- Enrolled faces stay in the kiosk browser's local storage. Delete them with **Staff → Enrol faces → Delete all enrolments**, or by clearing the site data.
- The staff PIN is a mock value visible in the page source; do not reuse a real PIN.
