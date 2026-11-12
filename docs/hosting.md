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

- **Simulation** (default): no camera, results are simulated. Used for the screenshots.
- **Live**: Staff (PIN `1234`) → Settings → tick **Live camera and face model**, or open the page with `?live=1`.
  The first time, the model downloads (about 39 MB) and the browser asks for camera permission.

## Run on your laptop

The camera only works on `https://` or `localhost`, so start a tiny local server from the repo folder:

```bash
python -m http.server 8000
```

Then open <http://localhost:8000/prototype/?live=1>.

## Host online

### Option A: GitHub Pages (automatic, recommended)

The repo already contains `.github/workflows/pages.yml`, which publishes only the `prototype/` folder.

1. Push the workflow and `prototype/` to the `main` branch.
2. On GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Open the **Actions** tab and wait for "Deploy kiosk to GitHub Pages" to turn green (about 1 minute).
4. The site is at **https://eavan127.github.io/SmartRoom_UTP_AI/** (add `?live=1` for the camera).

Every later push that changes `prototype/` redeploys automatically.
GitHub Pages is free for public repos. For a private repo you need GitHub Pro, which is free with the GitHub Student Developer Pack.

### Option B: Netlify Drop (no git, 1 minute)

1. Go to <https://app.netlify.com/drop> and sign in.
2. Drag the `prototype` folder onto the page.
3. Netlify gives you an `https://….netlify.app` link. To update, drag the folder again.

## Demo checklist

1. Open the hosted link with `?live=1` on the laptop that will act as the kiosk.
2. Staff → Enrol faces: enrol each team member 2-3 times as Student A, B, C, D.
3. Exit staff → Collect Room Card → Discussion Room 1 → each member presses **Scan face**.
4. Record the scenarios (all verified, stranger, missing member + staff override, return).

## Privacy

- The hosted site contains no student data: only the two files above.
- Enrolled faces stay in the kiosk browser's local storage. Delete them with **Staff → Enrol faces → Delete all enrolments**, or by clearing the site data.
- The staff PIN is a mock value visible in the page source; do not reuse a real PIN.
