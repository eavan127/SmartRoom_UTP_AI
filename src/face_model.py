"""Pretrained face model: YuNet detector + SFace embedder (OpenCV Zoo).

No training happens here. Models are downloaded once into models/ (ignored by git).
"""
from pathlib import Path
import urllib.request

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models"
ZOO = "https://github.com/opencv/opencv_zoo/raw/main/models"
DETECTOR = ("face_detection_yunet_2023mar.onnx", f"{ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx")
RECOGNIZER = ("face_recognition_sface_2021dec.onnx", f"{ZOO}/face_recognition_sface/face_recognition_sface_2021dec.onnx")


def _ensure(name, url):
    path = MODEL_DIR / name
    if not path.exists():
        MODEL_DIR.mkdir(exist_ok=True)
        print(f"Downloading {name} ...")
        urllib.request.urlretrieve(url, path)
    return str(path)


class FaceModel:
    def __init__(self, score_threshold=0.8):
        self.detector = cv2.FaceDetectorYN.create(_ensure(*DETECTOR), "", (320, 320), score_threshold)
        self.recognizer = cv2.FaceRecognizerSF.create(_ensure(*RECOGNIZER), "")

    def detect(self, img):
        """Return the largest face row [x, y, w, h, landmarks..., score] or None."""
        # Phone photos are large; YuNet misses big faces, so detect on a copy at most 960 px wide
        h, w = img.shape[:2]
        scale = min(1.0, 960 / max(h, w))
        small = cv2.resize(img, (round(w * scale), round(h * scale))) if scale < 1 else img
        self.detector.setInputSize((small.shape[1], small.shape[0]))
        _, faces = self.detector.detect(small)
        if faces is None or len(faces) == 0:
            return None
        face = max(faces, key=lambda f: f[2] * f[3]).copy()
        face[:14] /= scale  # box and 5 landmarks back to full-size coordinates
        return face

    def align(self, img):
        """Return the 112x112 aligned face the recognizer uses, or None if no face is found."""
        face = self.detect(img)
        return None if face is None else self.recognizer.alignCrop(img, face)

    def embed(self, img):
        """Return an L2-normalised 128-d embedding for the largest face, or None.

        A 112x112 image is taken as an already aligned face (saved by prepare_data), so it is
        not detected again; detection often fails on such tight crops.
        """
        if img is None:
            return None
        aligned = img if img.shape[:2] == (112, 112) else self.align(img)
        if aligned is None:
            return None
        feat = self.recognizer.feature(aligned).flatten()
        return feat / np.linalg.norm(feat)

    def crop(self, img, margin=0.25):
        """Crop the largest face with a margin (used by prepare_data for ID photos)."""
        face = self.detect(img)
        if face is None:
            return None
        x, y, w, h = face[:4]
        mx, my = w * margin, h * margin
        x0, y0 = int(max(0, x - mx)), int(max(0, y - my))
        x1, y1 = int(min(img.shape[1], x + w + mx)), int(min(img.shape[0], y + h + my))
        return img[y0:y1, x0:x1]


def cosine(a, b):
    return float(np.dot(a, b))


def decode_image(data: bytes):
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
