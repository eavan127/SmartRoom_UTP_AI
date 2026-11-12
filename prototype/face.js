/* SmartRoom UTP - face recognition in the browser.
 *
 * Same models and steps as src/face_model.py, run with onnxruntime-web:
 *   YuNet (face + 5 landmarks) -> align to 112x112 -> SFace (128 numbers) -> cosine similarity.
 * The models are downloaded from the OpenCV Hugging Face mirror; no photo ever leaves this device.
 * Needs: <script src="https://cdn.jsdelivr.net/npm/onnxruntime-web@1.20.1/dist/ort.min.js">
 */
const Face = (() => {
  const ORT_DIR = "https://cdn.jsdelivr.net/npm/onnxruntime-web@1.20.1/dist/";
  const MODELS = {
    det: "https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx",
    rec: "https://huggingface.co/opencv/face_recognition_sface/resolve/main/face_recognition_sface_2021dec.onnx",
  };
  const SIZE = 640;            // YuNet input is fixed at 640x640
  const MIN_SCORE = 0.6;
  // Where the 5 landmarks must land in the 112x112 face (ArcFace template, as in OpenCV alignCrop)
  const TEMPLATE = [[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366], [41.5493, 92.3655], [70.7299, 92.2041]];

  let det = null, rec = null, loading = null;

  async function fetchModel(url, onBytes) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Model download failed (${res.status})`);
    const total = +res.headers.get("content-length") || 0;
    const reader = res.body.getReader();
    const chunks = [];
    let got = 0;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value); got += value.length; onBytes(value.length, total);
    }
    const buf = new Uint8Array(got);
    let o = 0;
    for (const c of chunks) { buf.set(c, o); o += c.length; }
    return buf;
  }

  /* Load both models once. onProgress(0..1) is called while downloading (about 39 MB). */
  function load(onProgress = () => {}) {
    if (loading) return loading;
    ort.env.wasm.wasmPaths = ORT_DIR;
    ort.env.wasm.numThreads = 1;  // works on any static host (no cross-origin isolation needed)
    const expected = 232589 + 38696353;
    let got = 0;
    const tick = n => { got += n; onProgress(Math.min(1, got / expected)); };
    loading = (async () => {
      const [d, r] = await Promise.all([fetchModel(MODELS.det, tick), fetchModel(MODELS.rec, tick)]);
      det = await ort.InferenceSession.create(d);
      rec = await ort.InferenceSession.create(r);
    })();
    loading.catch(() => { loading = null; });
    return loading;
  }

  const ready = () => !!(det && rec);

  /* Copy a video/image/canvas into a canvas at its natural size. */
  function toCanvas(src) {
    const w = src.videoWidth || src.naturalWidth || src.width;
    const h = src.videoHeight || src.naturalHeight || src.height;
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    c.getContext("2d").drawImage(src, 0, 0, w, h);
    return c;
  }

  /* Largest face with score >= MIN_SCORE: {box:[x,y,w,h], kps:[[x,y]x5], score} in source pixels, or null. */
  async function detect(canvas) {
    const s = Math.min(1, SIZE / Math.max(canvas.width, canvas.height));  // shrink big photos, never enlarge
    const pad = document.createElement("canvas");
    pad.width = pad.height = SIZE;
    const ctx = pad.getContext("2d");
    ctx.fillStyle = "#000"; ctx.fillRect(0, 0, SIZE, SIZE);
    ctx.drawImage(canvas, 0, 0, Math.round(canvas.width * s), Math.round(canvas.height * s));
    const px = ctx.getImageData(0, 0, SIZE, SIZE).data;
    const n = SIZE * SIZE, input = new Float32Array(3 * n);
    for (let i = 0; i < n; i++) {           // BGR, 0-255, channels first
      input[i] = px[i * 4 + 2]; input[n + i] = px[i * 4 + 1]; input[2 * n + i] = px[i * 4];
    }
    const out = await det.run({ input: new ort.Tensor("float32", input, [1, 3, SIZE, SIZE]) });
    let best = null;
    for (const st of [8, 16, 32]) {
      const cols = SIZE / st;
      const cls = out[`cls_${st}`].data, obj = out[`obj_${st}`].data;
      const bb = out[`bbox_${st}`].data, kp = out[`kps_${st}`].data;
      for (let i = 0; i < cls.length; i++) {
        const score = Math.sqrt(Math.min(1, Math.max(0, cls[i])) * Math.min(1, Math.max(0, obj[i])));
        if (score < MIN_SCORE) continue;
        const r = Math.floor(i / cols), c = i % cols;
        const w = Math.exp(bb[i * 4 + 2]) * st, h = Math.exp(bb[i * 4 + 3]) * st;
        if (best && w * h <= best.area) continue;
        const cx = (c + bb[i * 4]) * st, cy = (r + bb[i * 4 + 1]) * st;
        const kps = [0, 1, 2, 3, 4].map(k => [(kp[i * 10 + 2 * k] + c) * st / s, (kp[i * 10 + 2 * k + 1] + r) * st / s]);
        best = { area: w * h, score, kps, box: [(cx - w / 2) / s, (cy - h / 2) / s, w / s, h / s] };
      }
    }
    return best;
  }

  /* Least-squares similarity transform (rotation + scale + shift) taking the landmarks to TEMPLATE. */
  function similarity(src) {
    const mean = pts => pts.reduce((a, p) => [a[0] + p[0] / 5, a[1] + p[1] / 5], [0, 0]);
    const ms = mean(src), md = mean(TEMPLATE);
    let num1 = 0, num2 = 0, den = 0;
    for (let i = 0; i < 5; i++) {
      const xs = src[i][0] - ms[0], ys = src[i][1] - ms[1];
      const xd = TEMPLATE[i][0] - md[0], yd = TEMPLATE[i][1] - md[1];
      num1 += xs * xd + ys * yd; num2 += xs * yd - ys * xd; den += xs * xs + ys * ys;
    }
    const a = num1 / den, b = num2 / den;
    return { a, b, tx: md[0] - (a * ms[0] - b * ms[1]), ty: md[1] - (b * ms[0] + a * ms[1]) };
  }

  /* 128 numbers (unit length) for the face, or null if no face is found. */
  async function embed(src) {
    if (!ready()) throw new Error("Face model not loaded");
    const canvas = toCanvas(src);
    const face = await detect(canvas);
    if (!face) return null;
    const { a, b, tx, ty } = similarity(face.kps);
    const al = document.createElement("canvas");
    al.width = al.height = 112;
    const ctx = al.getContext("2d");
    ctx.imageSmoothingQuality = "high";
    ctx.setTransform(a, b, -b, a, tx, ty);
    ctx.drawImage(canvas, 0, 0);
    const px = ctx.getImageData(0, 0, 112, 112).data;
    const n = 112 * 112, input = new Float32Array(3 * n);
    for (let i = 0; i < n; i++) {           // RGB, 0-255, channels first
      input[i] = px[i * 4]; input[n + i] = px[i * 4 + 1]; input[2 * n + i] = px[i * 4 + 2];
    }
    const f = (await rec.run({ data: new ort.Tensor("float32", input, [1, 3, 112, 112]) })).fc1.data;
    const norm = Math.hypot(...f);
    return { emb: Array.from(f, v => v / norm), score: face.score };
  }

  const cosine = (x, y) => x.reduce((s, v, i) => s + v * y[i], 0);

  return { load, ready, embed, cosine, toCanvas };
})();
