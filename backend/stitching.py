"""
Lightweight panorama generation.

Uses OpenCV's built-in cv2.Stitcher (a classical feature-matching / homography
pipeline, not an AI model, not GPU-dependent) to combine overlapping photos
into a single panoramic image, then remaps it to an equirectangular 2:1
canvas so it can be viewed with a standard 360 sphere/panorama viewer.

Design goals per spec:
- No custom advanced CV algorithms - rely entirely on OpenCV's Stitcher.
- No AI models, no GPU requirement.
- Resize large images before processing to control memory usage.
- Never leak raw stack traces to the caller - raise StitchError with a
  friendly message instead.
"""
from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from . import config

logger = logging.getLogger("panorama.stitching")


class StitchError(Exception):
    """User-friendly stitching failure."""


def _load_and_resize(path: Path) -> np.ndarray:
    img = cv2.imread(str(path))
    if img is None:
        raise StitchError(f"Could not read image: {path.name}")

    h, w = img.shape[:2]
    max_dim = max(h, w)
    if max_dim > config.MAX_SOURCE_DIMENSION:
        scale = config.MAX_SOURCE_DIMENSION / max_dim
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img


def _to_equirectangular(panorama: np.ndarray) -> np.ndarray:
    """Fit the stitched panorama onto a 2:1 equirectangular canvas.

    This is a simple resize/letterbox step (not a true spherical projection,
    which would require calibrated camera intrinsics per spec's "keep it
    lightweight" constraint). The stitched panorama already spans the
    photographed field of view horizontally; we pad vertically to reach a
    2:1 aspect ratio so it is compatible with standard 360 sphere viewers.
    """
    h, w = panorama.shape[:2]
    target_h = w // 2

    canvas = np.zeros((target_h, w, 3), dtype=np.uint8)

    if h >= target_h:
        # Crop from the vertical center
        top = (h - target_h) // 2
        canvas = panorama[top:top + target_h, :, :]
    else:
        # Letterbox (center) the panorama vertically
        top = (target_h - h) // 2
        canvas[top:top + h, :, :] = panorama

    return canvas


def generate_panorama(image_paths: list[Path], output_path: Path, thumbnail_path: Path) -> None:
    """Stitch images and write the equirectangular panorama + thumbnail.

    Raises StitchError with a friendly message on failure.
    """
    if len(image_paths) < 2:
        raise StitchError("At least two photos are required to generate a panorama.")

    images = []
    for p in image_paths:
        try:
            images.append(_load_and_resize(p))
        except StitchError:
            raise
        except Exception:
            logger.exception("Failed loading image %s", p)
            raise StitchError(f"Could not read image: {p.name}")

    try:
        stitcher = cv2.Stitcher_create(cv2.Stitcher_PANORAMA)
    except AttributeError:
        stitcher = cv2.createStitcher(cv2.Stitcher_PANORAMA)  # older OpenCV API

    try:
        status, stitched = stitcher.stitch(images)
    except Exception:
        logger.exception("Stitcher raised an exception")
        raise StitchError(
            "Unable to create the 360 view. Please upload photos with more "
            "overlap and similar lighting, then try again."
        )

    if status != cv2.Stitcher_OK or stitched is None:
        logger.warning("Stitching failed with status code %s", status)
        raise StitchError(
            "Unable to create the 360 view. Please make sure neighboring "
            "photos overlap by 30-50% and try again."
        )

    equirect = _to_equirectangular(stitched)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)

    if not cv2.imwrite(str(output_path), equirect, [cv2.IMWRITE_JPEG_QUALITY, 90]):
        raise StitchError("Failed to save the generated panorama.")

    th, tw = equirect.shape[:2]
    thumb_w = 480
    thumb_h = int(th * (thumb_w / tw))
    thumbnail = cv2.resize(equirect, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(thumbnail_path), thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 85])
