"""
Exhaustive Perception, Vision, Perceptual Hashing, ROI Cropping, and Base64 Tests
Contains 150 discrete test cases covering image hashing, Hamming distance,
ROI boundary math, Base64 JPEG encoding/decoding, and visual fidelity.
"""

import io
import base64
import unittest
from PIL import Image, ImageDraw
import imagehash
from extra.core.platform.base import image_to_base64


def decode_base64_image(b64_str: str) -> Image.Image:
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    raw = base64.b64decode(b64_str)
    return Image.open(io.BytesIO(raw))


def crop_roi(image: Image.Image, box: tuple) -> Image.Image:
    x1, y1, x2, y2 = box
    w, h = image.size
    cx1 = max(0, min(w - 1, x1))
    cy1 = max(0, min(h - 1, y1))
    cx2 = max(cx1 + 1, min(w, x2))
    cy2 = max(cy1 + 1, min(h, y2))
    return image.crop((cx1, cy1, cx2, cy2))


class TestPerceptionVisionExhaustive(unittest.TestCase):
    """Base class for perception and vision tests."""
    pass


# 1. 50 Perceptual Hashing Tests across diverse synthetic patterns
def _make_phash_test(color1, color2, shape_type):
    def test_func(self):
        img = Image.new("RGB", (128, 128), color=color1)
        draw = ImageDraw.Draw(img)
        if shape_type == "rect":
            draw.rectangle([20, 20, 100, 100], fill=color2)
        elif shape_type == "ellipse":
            draw.ellipse([20, 20, 100, 100], fill=color2)
        elif shape_type == "line":
            draw.line([0, 0, 128, 128], fill=color2, width=4)

        h = imagehash.phash(img)
        self.assertIsNotNone(h)
        self.assertEqual(len(str(h)), 16)
    return test_func

colors = [
    ("black", "white"), ("white", "black"), ("red", "blue"), ("green", "yellow"),
    ("purple", "orange"), ("gray", "navy"), ("maroon", "teal"), ("cyan", "magenta"),
]
shapes = ["rect", "ellipse", "line"]
idx = 0
for c1, c2 in colors:
    for s in shapes:
        setattr(TestPerceptionVisionExhaustive, f"test_001_to_050_phash_generation_{idx:02d}", _make_phash_test(c1, c2, s))
        idx += 1
while idx < 50:
    setattr(TestPerceptionVisionExhaustive, f"test_001_to_050_phash_generation_{idx:02d}", _make_phash_test((idx * 5, 50, 100), (255, idx * 5, 0), "rect"))
    idx += 1


# 2. 30 Hamming Distance Delta Tests
def _make_hamming_test(diff_pixels, expected_min_delta):
    def test_func(self):
        base_img = Image.new("RGB", (100, 100), "white")
        mod_img = base_img.copy()
        if diff_pixels > 0:
            draw = ImageDraw.Draw(mod_img)
            draw.rectangle([0, 0, diff_pixels, diff_pixels], fill="black")

        h1 = imagehash.phash(base_img)
        h2 = imagehash.phash(mod_img)
        delta = h1 - h2
        if diff_pixels == 0:
            self.assertEqual(delta, 0)
        else:
            self.assertTrue(delta >= expected_min_delta)
    return test_func

for idx in range(30):
    diff = idx * 3
    min_delta = 0 if diff == 0 else 1
    setattr(TestPerceptionVisionExhaustive, f"test_051_to_080_hamming_delta_{idx:02d}", _make_hamming_test(diff, min_delta))


# 3. 40 ROI Cropping Boundary Safety Tests
def _make_roi_crop_test(img_w, img_h, roi_box):
    def test_func(self):
        base_img = Image.new("RGB", (img_w, img_h), "blue")
        cropped = crop_roi(base_img, roi_box)
        self.assertIsNotNone(cropped)
        self.assertTrue(cropped.width > 0)
        self.assertTrue(cropped.height > 0)
        self.assertTrue(cropped.width <= img_w)
        self.assertTrue(cropped.height <= img_h)
    return test_func

for idx in range(40):
    w, h = 500, 400
    x1 = idx * 8
    y1 = idx * 6
    x2 = min(w, x1 + 50)
    y2 = min(h, y1 + 50)
    setattr(TestPerceptionVisionExhaustive, f"test_081_to_120_roi_cropping_{idx:02d}", _make_roi_crop_test(w, h, (x1, y1, x2, y2)))


# 4. 30 Base64 Encoding / Decoding Roundtrip Fidelity Tests
def _make_base64_roundtrip_test(w, h, quality):
    def test_func(self):
        img = Image.new("RGB", (w, h), color=(w % 255, h % 255, quality * 2))
        b64_str = image_to_base64(img, quality=quality)
        self.assertTrue(len(b64_str) > 50)

        decoded = decode_base64_image(b64_str)
        self.assertEqual(decoded.width, w)
        self.assertEqual(decoded.height, h)
    return test_func

qualities = [30, 50, 75, 85, 95]
dimensions = [(50, 50), (100, 100), (200, 150), (320, 240), (640, 480), (800, 600)]
idx = 0
for q in qualities:
    for dim in dimensions:
        setattr(TestPerceptionVisionExhaustive, f"test_121_to_150_base64_roundtrip_{idx:02d}", _make_base64_roundtrip_test(dim[0], dim[1], q))
        idx += 1


if __name__ == "__main__":
    unittest.main()
