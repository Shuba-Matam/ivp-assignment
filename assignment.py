"""Image and Video Processing assignment: ten reproducible OpenCV experiments.

Author: Shuba Bhuvi Matam (RA2311031010068)

Run ``python assignment.py`` (or ``--all``) to generate every result.  Paths are
resolved relative to this file so the program also works when launched from a
Windows shortcut or a different working directory.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import mimetypes
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterable

import cv2
import imageio_ffmpeg
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs"
OUTPUTS = ROOT / "outputs"
DEMO_IMAGE = INPUTS / "demo_image.png"
DEMO_VIDEO = INPUTS / "demo_video.avi"
REAL_VIDEO = INPUTS / "real_clip.mp4"
METRICS_FILE = OUTPUTS / "metrics.json"
RNG_SEED = 2311031010068 % (2**32)
FPS = 24.0
FRAME_SIZE = (480, 320)  # width, height
FRAME_COUNT = 96


def rel(path: Path) -> str:
    """Return a stable repository-relative path for JSON and console output."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def reset_dir(path: Path) -> Path:
    output_root = OUTPUTS.resolve()
    requested = path.absolute()
    resolved = requested.resolve()
    if output_root != ROOT.resolve() / "outputs" or output_root not in resolved.parents or resolved == output_root:
        raise ValueError(f"Refusing to reset a directory outside outputs: {path}")
    current = OUTPUTS
    for part in requested.relative_to(ROOT.absolute()).parts[1:]:
        current = current / part
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            raise RuntimeError(f"Refusing to follow an output link: {current}")
    if requested.exists():
        shutil.rmtree(requested)
    return ensure_dir(requested)


def json_number(value: float) -> float | None:
    return None if not math.isfinite(value) else round(float(value), 6)


def mse_psnr(reference: np.ndarray, test: np.ndarray) -> tuple[float, float]:
    """Calculate MSE and PSNR after signed-safe floating-point conversion."""
    if reference.shape != test.shape:
        raise ValueError(f"Image shapes differ: {reference.shape} and {test.shape}")
    error = reference.astype(np.float64) - test.astype(np.float64)
    mse = float(np.mean(error * error))
    psnr = math.inf if mse == 0 else 10.0 * math.log10((255.0**2) / mse)
    return mse, psnr


def file_size(path: Path) -> int:
    return path.stat().st_size


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_image(path: Path, image: np.ndarray, params: list[int] | None = None) -> None:
    ensure_dir(path.parent)
    if not cv2.imwrite(str(path), image, params or []):
        raise RuntimeError(f"OpenCV could not write {path}")


def read_image(path: Path, flags: int = cv2.IMREAD_COLOR) -> np.ndarray:
    image = cv2.imread(str(path), flags)
    if image is None:
        raise FileNotFoundError(f"Could not decode image: {path}")
    return image


def video_info(path: Path) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise FileNotFoundError(f"Could not open video: {path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frames = int(round(capture.get(cv2.CAP_PROP_FRAME_COUNT)))
    width = int(round(capture.get(cv2.CAP_PROP_FRAME_WIDTH)))
    height = int(round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    capture.release()
    return {
        "path": rel(path),
        "size_bytes": file_size(path),
        "sha256": sha256_file(path),
        "codec_container_note": path.suffix.lower().lstrip("."),
        "frame_count": frames,
        "fps": round(fps, 6),
        "width": width,
        "height": height,
        "duration_seconds": round(frames / fps, 6) if fps else None,
    }


def open_writer(
    path: Path, fps: float, size: tuple[int, int], codec: str = "FFV1"
) -> cv2.VideoWriter:
    ensure_dir(path.parent)
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*codec), fps, size, True
    )
    if not writer.isOpened():
        raise RuntimeError(
            f"Could not create {path} with codec {codec}. Check the OpenCV video codecs."
        )
    return writer


def iter_video(path: Path) -> Iterable[tuple[int, np.ndarray]]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise FileNotFoundError(f"Could not open video: {path}")
    index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            yield index, frame
            index += 1
    finally:
        capture.release()


def frame_at(path: Path, index: int) -> np.ndarray:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise FileNotFoundError(f"Could not open video: {path}")
    capture.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, frame = capture.read()
    capture.release()
    if not ok:
        raise IndexError(f"Could not read frame {index} from {path}")
    return frame


def center_crop(image: np.ndarray, width: int, height: int) -> np.ndarray:
    image_height, image_width = image.shape[:2]
    width, height = min(width, image_width), min(height, image_height)
    x = (image_width - width) // 2
    y = (image_height - height) // 2
    return image[y : y + height, x : x + width].copy()


def bgr_for_plot(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def save_panel(
    path: Path,
    items: list[tuple[str, np.ndarray, str | None]],
    columns: int = 3,
    figsize: tuple[float, float] | None = None,
) -> None:
    rows = math.ceil(len(items) / columns)
    fig, axes = plt.subplots(rows, columns, figsize=figsize or (5.2 * columns, 4.0 * rows))
    axes_array = np.atleast_1d(axes).ravel()
    for axis, (title, image, cmap) in zip(axes_array, items):
        shown = bgr_for_plot(image) if image.ndim == 3 and cmap is None else image
        axis.imshow(shown, cmap=cmap, vmin=0 if cmap == "gray" else None, vmax=255 if cmap == "gray" else None)
        axis.set_title(title, fontsize=12, pad=8)
        axis.axis("off")
    for axis in axes_array[len(items) :]:
        axis.axis("off")
    fig.tight_layout()
    ensure_dir(path.parent)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def make_demo_frame(index: int) -> np.ndarray:
    """Create a textured landscape/road scene with a moving geometric vehicle."""
    width, height = FRAME_SIZE
    y, x = np.mgrid[0:height, 0:width]
    frame = np.zeros((height, width, 3), dtype=np.float32)

    sky = y < 178
    frame[..., 0] = np.where(sky, 205 - y * 0.22, 70)
    frame[..., 1] = np.where(sky, 155 + y * 0.20, 120)
    frame[..., 2] = np.where(sky, 80 + y * 0.28, 72)

    # Deterministic texture makes compression and denoising differences visible.
    texture = 5.0 * np.sin(x / 8.5) + 3.0 * np.cos((x + y) / 13.0)
    frame += texture[..., None]
    frame = np.clip(frame, 0, 255).astype(np.uint8)

    cv2.circle(frame, (392, 58), 27, (35, 205, 245), -1, cv2.LINE_AA)
    cv2.fillPoly(frame, [np.array([(0, 178), (92, 91), (174, 178)], np.int32)], (64, 102, 55))
    cv2.fillPoly(frame, [np.array([(105, 178), (250, 70), (355, 178)], np.int32)], (82, 126, 70))
    cv2.fillPoly(frame, [np.array([(260, 178), (380, 102), (480, 178)], np.int32)], (55, 98, 70))
    cv2.rectangle(frame, (0, 178), (480, 224), (65, 142, 78), -1)

    road = np.array([(168, 320), (226, 178), (272, 178), (376, 320)], np.int32)
    cv2.fillPoly(frame, [road], (62, 66, 72))
    cv2.polylines(frame, [road], True, (210, 210, 210), 3, cv2.LINE_AA)
    for offset in range(0, 170, 34):
        top_y = 188 + offset
        ratio = (top_y - 178) / 142
        center = int(249 + 19 * ratio)
        half = max(2, int(2 + 7 * ratio))
        cv2.line(frame, (center - half, top_y), (center + half, min(319, top_y + 17)), (225, 215, 90), 3)

    # A coordinate grid supports visible translation/rotation/scaling analysis.
    for gx in range(40, width, 80):
        cv2.line(frame, (gx, 0), (gx, height - 1), (120, 145, 145), 1, cv2.LINE_AA)
        cv2.putText(frame, f"x={gx}", (gx + 3, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (30, 40, 40), 1, cv2.LINE_AA)
    for gy in range(40, height, 80):
        cv2.line(frame, (0, gy), (width - 1, gy), (120, 145, 145), 1, cv2.LINE_AA)
        cv2.putText(frame, f"y={gy}", (3, gy - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (30, 40, 40), 1, cv2.LINE_AA)

    # Trees and signs provide strong vertical and diagonal edges.
    for tx in (52, 112, 414, 452):
        cv2.rectangle(frame, (tx - 4, 148), (tx + 4, 207), (42, 64, 82), -1)
        cv2.circle(frame, (tx, 139), 18, (42, 102, 45), -1, cv2.LINE_AA)
    cv2.rectangle(frame, (22, 232), (136, 286), (195, 190, 165), -1)
    cv2.rectangle(frame, (34, 245), (65, 274), (170, 105, 65), -1)
    cv2.rectangle(frame, (82, 245), (124, 258), (90, 130, 150), -1)
    cv2.putText(frame, "IVP ROUTE", (33, 228), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (245, 245, 245), 2, cv2.LINE_AA)

    # Move a brightly colored vehicle with a slight vertical oscillation.
    car_x = int(155 + (index / max(1, FRAME_COUNT - 1)) * 250)
    car_y = int(251 + 7 * math.sin(index * 2 * math.pi / 36))
    cv2.rectangle(frame, (car_x - 30, car_y - 16), (car_x + 31, car_y + 15), (35, 65, 220), -1, cv2.LINE_AA)
    cv2.fillPoly(frame, [np.array([(car_x - 17, car_y - 16), (car_x - 7, car_y - 30), (car_x + 16, car_y - 30), (car_x + 25, car_y - 16)], np.int32)], (55, 105, 235))
    cv2.circle(frame, (car_x - 18, car_y + 16), 8, (25, 25, 25), -1, cv2.LINE_AA)
    cv2.circle(frame, (car_x + 20, car_y + 16), 8, (25, 25, 25), -1, cv2.LINE_AA)
    cv2.putText(frame, f"F{index:02d}", (car_x - 19, car_y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    return frame


def generate_inputs(force: bool = False) -> dict[str, Any]:
    ensure_dir(INPUTS)
    if force or not DEMO_IMAGE.exists():
        save_image(DEMO_IMAGE, make_demo_frame(38))
    if force or not DEMO_VIDEO.exists():
        writer = open_writer(DEMO_VIDEO, FPS, FRAME_SIZE)
        try:
            for index in range(FRAME_COUNT):
                writer.write(make_demo_frame(index))
        finally:
            writer.release()
    return {
        "generated_image": {
            "path": rel(DEMO_IMAGE),
            "size_bytes": file_size(DEMO_IMAGE),
            "sha256": sha256_file(DEMO_IMAGE),
            "width": FRAME_SIZE[0],
            "height": FRAME_SIZE[1],
        },
        "generated_video": video_info(DEMO_VIDEO),
        "real_video": video_info(REAL_VIDEO) if REAL_VIDEO.exists() else None,
        "deterministic_rng_seed": RNG_SEED,
    }


def seeded_region_grow(
    image: np.ndarray, seed_xy: tuple[int, int], threshold: float = 27.0
) -> np.ndarray:
    """Grow an 8-connected color region using distance from the seed in Lab space."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
    height, width = lab.shape[:2]
    seed_x, seed_y = seed_xy
    if not (0 <= seed_x < width and 0 <= seed_y < height):
        raise ValueError("Region-growing seed lies outside the image")
    seed_color = lab[seed_y, seed_x]
    distance = np.linalg.norm(lab - seed_color, axis=2)
    allowed = distance <= threshold
    mask = np.zeros((height, width), np.uint8)
    queue: deque[tuple[int, int]] = deque([(seed_x, seed_y)])
    mask[seed_y, seed_x] = 255
    neighbors = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))
    while queue:
        x, y = queue.popleft()
        for dx, dy in neighbors:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and mask[ny, nx] == 0 and allowed[ny, nx]:
                mask[ny, nx] = 255
                queue.append((nx, ny))
    return mask


def question_1() -> tuple[dict[str, Any], str]:
    out = reset_dir(OUTPUTS / "q1")
    image = read_image(DEMO_IMAGE)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 1.1)
    gx = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
    magnitude_float = cv2.magnitude(gx.astype(np.float32), gy.astype(np.float32))
    magnitude = cv2.normalize(magnitude_float, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    canny = cv2.Canny(blurred, 70, 150, L2gradient=True)
    sobel_path, canny_path = out / "sobel_magnitude.png", out / "canny_edges.png"
    panel_path = out / "edge_detection_comparison.png"
    save_image(sobel_path, magnitude)
    save_image(canny_path, canny)
    save_panel(panel_path, [("Original scene", image, None), ("Sobel gradient magnitude", magnitude, "gray"), ("Canny binary edges", canny, "gray")])
    metrics = {
        "title": "Sobel and Canny edge detection",
        "parameters": {"gaussian_kernel": [5, 5], "gaussian_sigma": 1.1, "sobel_kernel": 3, "canny_thresholds": [70, 150], "canny_l2_gradient": True},
        "sobel": {"mean_magnitude": round(float(magnitude_float.mean()), 6), "maximum_magnitude": round(float(magnitude_float.max()), 6), "nonzero_pixels": int(np.count_nonzero(magnitude))},
        "canny": {"edge_pixels": int(np.count_nonzero(canny)), "edge_percentage": round(100.0 * np.count_nonzero(canny) / canny.size, 6)},
        "outputs": {"sobel": rel(sobel_path), "canny": rel(canny_path), "comparison_figure": rel(panel_path)},
    }
    return metrics, f"Sobel and Canny complete; {metrics['canny']['edge_pixels']} Canny edge pixels"


def question_2() -> tuple[dict[str, Any], str]:
    out = reset_dir(OUTPUTS / "q2")
    image = read_image(DEMO_IMAGE)
    png_path, jpg_path = out / "lossless.png", out / "lossy_q35.jpg"
    save_image(png_path, image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    save_image(jpg_path, image, [cv2.IMWRITE_JPEG_QUALITY, 35])
    png_decoded, jpg_decoded = read_image(png_path), read_image(jpg_path)
    png_mse, png_psnr = mse_psnr(image, png_decoded)
    jpg_mse, jpg_psnr = mse_psnr(image, jpg_decoded)
    diff = cv2.absdiff(image, jpg_decoded)
    diff_visible = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
    diff_path, panel_path = out / "jpeg_absolute_difference.png", out / "compression_comparison.png"
    save_image(diff_path, diff_visible)
    save_panel(panel_path, [("Reference PNG input", image, None), ("Lossless PNG reconstruction", png_decoded, None), ("Lossy JPEG reconstruction (Q=35)", jpg_decoded, None), ("JPEG absolute difference (normalized)", diff_visible, None)], columns=2, figsize=(11, 8))
    source_size = file_size(DEMO_IMAGE)
    metrics = {
        "title": "Lossless PNG and lossy JPEG image compression",
        "reference": {"path": rel(DEMO_IMAGE), "size_bytes": source_size},
        "png": {"path": rel(png_path), "size_bytes": file_size(png_path), "mse": json_number(png_mse), "psnr_db": json_number(png_psnr), "exact_reconstruction": bool(np.array_equal(image, png_decoded))},
        "jpeg": {"path": rel(jpg_path), "quality": 35, "size_bytes": file_size(jpg_path), "mse": json_number(jpg_mse), "psnr_db": json_number(jpg_psnr), "size_reduction_vs_png_percent": round(100.0 * (1.0 - file_size(jpg_path) / file_size(png_path)), 6)},
        "outputs": {"difference": rel(diff_path), "comparison_figure": rel(panel_path)},
    }
    return metrics, f"PNG MSE={png_mse:.2f}; JPEG PSNR={jpg_psnr:.2f} dB"


def question_3() -> tuple[dict[str, Any], str]:
    out = reset_dir(OUTPUTS / "q3")
    image = read_image(DEMO_IMAGE)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    otsu_value, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    seed = (30, 30)
    region = seeded_region_grow(image, seed, threshold=27.0)
    overlay = image.copy()
    overlay[region > 0] = (0.45 * overlay[region > 0] + 0.55 * np.array([255, 90, 40])).astype(np.uint8)
    cv2.drawMarker(overlay, seed, (0, 0, 255), cv2.MARKER_CROSS, 18, 2)
    otsu_path, region_path, overlay_path = out / "otsu_mask.png", out / "seeded_region_mask.png", out / "region_overlay.png"
    panel_path = out / "segmentation_comparison.png"
    save_image(otsu_path, otsu)
    save_image(region_path, region)
    save_image(overlay_path, overlay)
    save_panel(panel_path, [("Original scene", image, None), (f"Otsu global threshold = {otsu_value:.0f}", otsu, "gray"), (f"Seeded region growing at {seed}", region, "gray"), ("Connected region overlay", overlay, None)], columns=2, figsize=(11, 8))
    otsu_bool, region_bool = otsu > 0, region > 0
    union = np.logical_or(otsu_bool, region_bool).sum()
    intersection = np.logical_and(otsu_bool, region_bool).sum()
    iou = float(intersection / union) if union else 1.0
    metrics = {
        "title": "Threshold and region-based segmentation",
        "otsu": {"threshold": round(float(otsu_value), 6), "foreground_pixels": int(otsu_bool.sum()), "foreground_percentage": round(100.0 * otsu_bool.mean(), 6)},
        "seeded_region_growing": {"seed_xy": list(seed), "lab_distance_threshold": 27.0, "connectivity": 8, "region_pixels": int(region_bool.sum()), "region_percentage": round(100.0 * region_bool.mean(), 6)},
        "comparison": {"intersection_over_union": round(iou, 6), "interpretation": "Otsu classifies every pixel by one global gray-level threshold; seeded growth returns only the connected color-similar area attached to the seed."},
        "outputs": {"otsu_mask": rel(otsu_path), "region_mask": rel(region_path), "overlay": rel(overlay_path), "comparison_figure": rel(panel_path)},
    }
    return metrics, f"Otsu threshold={otsu_value:.1f}; grown region={region_bool.mean()*100:.1f}%"


def question_4() -> tuple[dict[str, Any], str]:
    out = reset_dir(OUTPUTS / "q4")
    frames_dir = ensure_dir(out / "frames")
    first = middle = last = None
    count = 0
    expected = video_info(DEMO_VIDEO)["frame_count"]
    for index, frame in iter_video(DEMO_VIDEO):
        save_image(frames_dir / f"frame_{index:04d}.png", frame, [cv2.IMWRITE_PNG_COMPRESSION, 6])
        if index == 0:
            first = frame.copy()
        if index == expected // 2:
            middle = frame.copy()
        last = frame.copy()
        count += 1
    if not count or first is None or middle is None or last is None:
        raise RuntimeError("No frames were extracted from the generated video")
    panel_path = out / "extracted_frame_samples.png"
    save_panel(panel_path, [("First extracted frame", first, None), ("Middle extracted frame", middle, None), ("Last extracted frame", last, None)])
    frame_files = sorted(frames_dir.glob("frame_*.png"))
    metrics = {
        "title": "Extract every video frame as an individual PNG",
        "source": video_info(DEMO_VIDEO),
        "extraction": {"format": "PNG", "frame_count": count, "matches_reported_source_count": count == expected, "directory": rel(frames_dir), "first_file": rel(frame_files[0]), "last_file": rel(frame_files[-1]), "total_png_bytes": sum(file_size(path) for path in frame_files)},
        "outputs": {"sample_figure": rel(panel_path)},
    }
    return metrics, f"extracted {count}/{expected} frames as PNG"


def question_5() -> tuple[dict[str, Any], str]:
    out = reset_dir(OUTPUTS / "q5")
    source = video_info(DEMO_VIDEO)
    factor = 4
    sampled_fps = float(source["fps"]) / factor
    sampled_path = out / "sampled_6fps.avi"
    writer = open_writer(sampled_path, sampled_fps, (source["width"], source["height"]))
    sampled_frames: list[np.ndarray] = []
    original_frames: list[np.ndarray] = []
    try:
        for index, frame in iter_video(DEMO_VIDEO):
            original_frames.append(frame)
            if index % factor == 0:
                sampled_frames.append(frame.copy())
                writer.write(frame)
    finally:
        writer.release()
    per_frame_psnr: list[float] = []
    total_squared_error = 0.0
    total_values = 0
    for index, original in enumerate(original_frames):
        held = sampled_frames[index // factor]
        error = original.astype(np.float64) - held.astype(np.float64)
        squared = float(np.sum(error * error))
        mse = squared / error.size
        per_frame_psnr.append(math.inf if mse == 0 else 10.0 * math.log10((255.0**2) / mse))
        total_squared_error += squared
        total_values += error.size
    hold_mse = total_squared_error / total_values
    hold_psnr = math.inf if hold_mse == 0 else 10.0 * math.log10((255.0**2) / hold_mse)
    finite_plot = np.array([np.nan if not math.isfinite(value) else value for value in per_frame_psnr])
    plot_path = out / "time_aligned_hold_quality.png"
    fig, axis = plt.subplots(figsize=(10, 4.7))
    times = np.arange(len(per_frame_psnr)) / float(source["fps"])
    axis.plot(times, finite_plot, color="#2455a4", linewidth=1.7, label="non-identical held frames")
    exact_times = times[np.array([not math.isfinite(value) for value in per_frame_psnr])]
    marker_y = float(np.nanmax(finite_plot)) + 2.0
    axis.scatter(exact_times, np.full(exact_times.shape, marker_y), marker="v", s=28, color="#2f8f4e", label="exact retained sample (infinite PSNR)")
    axis.axhline(hold_psnr, color="#d4522a", linestyle="--", label=f"overall {hold_psnr:.2f} dB")
    axis.set(title="Frame-rate reduction: time-aligned sample-and-hold quality", xlabel="Original timeline (seconds)", ylabel="PSNR versus held sampled frame (dB)")
    axis.grid(alpha=0.3)
    axis.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)
    original_sample = original_frames[43]
    held_sample = sampled_frames[43 // factor]
    panel_path = out / "sampling_visual_comparison.png"
    save_panel(panel_path, [("Original frame 43 at 24 fps", original_sample, None), ("Held frame 40 from 6 fps sample", held_sample, None), ("Absolute temporal difference", cv2.absdiff(original_sample, held_sample), None)])
    sampled_info = video_info(sampled_path)
    metrics = {
        "title": "Video sampling by frame-rate reduction",
        "method": "Keep every fourth frame, write at one-quarter frame rate, and hold each retained sample for four original time instants during quality comparison.",
        "original": source,
        "sampled": sampled_info,
        "sampling_factor": factor,
        "duration_difference_seconds": round(abs(float(source["duration_seconds"]) - float(sampled_info["duration_seconds"])), 6),
        "time_aligned_sample_and_hold": {"mse": round(hold_mse, 6), "psnr_db": json_number(hold_psnr), "finite_psnr_mean_db": round(float(np.mean([v for v in per_frame_psnr if math.isfinite(v)])), 6), "comparison_frame_count": len(per_frame_psnr)},
        "outputs": {"sampled_video": rel(sampled_path), "quality_plot": rel(plot_path), "comparison_figure": rel(panel_path)},
    }
    return metrics, f"24 fps -> {sampled_fps:g} fps with duration {sampled_info['duration_seconds']:.2f}s; hold PSNR={hold_psnr:.2f} dB"


def question_6() -> tuple[dict[str, Any], str]:
    out = reset_dir(OUTPUTS / "q6")
    info = video_info(DEMO_VIDEO)
    size = (info["width"], info["height"])
    paths = {
        "translation": out / "translated.avi",
        "rotation": out / "rotated.avi",
        "scaling": out / "scaled_fixed_canvas.avi",
    }
    writers = {name: open_writer(path, info["fps"], size) for name, path in paths.items()}
    samples: dict[str, np.ndarray] = {}
    try:
        for index, frame in iter_video(DEMO_VIDEO):
            tx = int(round(55 * math.sin(2 * math.pi * index / info["frame_count"])))
            ty = int(round(25 * math.cos(2 * math.pi * index / info["frame_count"])))
            translated = cv2.warpAffine(frame, np.float32([[1, 0, tx], [0, 1, ty]]), size, borderMode=cv2.BORDER_CONSTANT, borderValue=(18, 18, 18))
            angle = 18 * math.sin(2 * math.pi * index / info["frame_count"])
            rotation_matrix = cv2.getRotationMatrix2D((size[0] / 2, size[1] / 2), angle, 1.0)
            rotated = cv2.warpAffine(frame, rotation_matrix, size, borderMode=cv2.BORDER_CONSTANT, borderValue=(18, 18, 18))
            scale = 0.70 + 0.45 * (0.5 + 0.5 * math.sin(2 * math.pi * index / info["frame_count"]))
            scale_matrix = cv2.getRotationMatrix2D((size[0] / 2, size[1] / 2), 0, scale)
            scaled = cv2.warpAffine(frame, scale_matrix, size, borderMode=cv2.BORDER_CONSTANT, borderValue=(18, 18, 18))
            for name, transformed in (("translation", translated), ("rotation", rotated), ("scaling", scaled)):
                writers[name].write(transformed)
                if index == 30:
                    samples[name] = transformed.copy()
    finally:
        for writer in writers.values():
            writer.release()
    original = frame_at(DEMO_VIDEO, 30)
    panel_path = out / "geometric_transformations.png"
    save_panel(panel_path, [("Original fixed canvas", original, None), ("Translation: content may leave canvas", samples["translation"], None), ("Rotation: corner pixels require fill", samples["rotation"], None), ("Scaling: resampling changes detail", samples["scaling"], None)], columns=2, figsize=(11, 8))
    metrics = {
        "title": "Per-frame geometric transformations on a fixed canvas",
        "source": info,
        "translation": {"x_range_pixels": [-55, 55], "y_range_pixels": [-25, 25], "effect": "Shifts every coordinate; uncovered pixels are filled and some content can be clipped.", "video": rel(paths["translation"])},
        "rotation": {"angle_range_degrees": [-18, 18], "center": [size[0] / 2, size[1] / 2], "effect": "Rotates around the frame center; interpolation resamples pixels and fixed-canvas corners are filled.", "video": rel(paths["rotation"])},
        "scaling": {"scale_range": [0.70, 1.15], "effect": "Changes apparent object size; downscaling removes detail and scaling above one clips edges on the fixed canvas.", "video": rel(paths["scaling"])},
        "outputs": {"comparison_figure": rel(panel_path), **{name + "_video": rel(path) for name, path in paths.items()}},
    }
    return metrics, "translation, rotation, and scaling videos written on a 480x320 canvas"


def question_7() -> tuple[dict[str, Any], str]:
    out = reset_dir(OUTPUTS / "q7")
    first_index, second_index = 20, 68
    first, second = frame_at(DEMO_VIDEO, first_index), frame_at(DEMO_VIDEO, second_index)
    signed = second.astype(np.int16) - first.astype(np.int16)
    absolute = np.abs(signed).astype(np.uint8)
    gray_abs = cv2.cvtColor(absolute, cv2.COLOR_BGR2GRAY)
    threshold = 28
    _, changed = cv2.threshold(gray_abs, threshold, 255, cv2.THRESH_BINARY)
    signed_visual = np.clip(signed + 128, 0, 255).astype(np.uint8)
    abs_path, mask_path, signed_path = out / "absolute_difference.png", out / "changed_pixels_mask.png", out / "signed_difference_offset128.png"
    panel_path = out / "frame_difference_comparison.png"
    save_image(abs_path, absolute)
    save_image(mask_path, changed)
    save_image(signed_path, signed_visual)
    save_panel(panel_path, [(f"Frame {first_index}", first, None), (f"Frame {second_index}", second, None), ("Absolute difference", absolute, None), (f"Changed pixels > {threshold}", changed, "gray")], columns=2, figsize=(11, 8))
    metrics = {
        "title": "Signed-safe difference between two video frames",
        "frames": [first_index, second_index],
        "calculation": "Convert uint8 to int16 before subtraction, then take absolute value to avoid unsigned wrap-around.",
        "difference": {"mean_absolute_difference": round(float(absolute.mean()), 6), "maximum_absolute_difference": int(absolute.max()), "changed_pixel_threshold": threshold, "changed_pixels": int(np.count_nonzero(changed)), "changed_percentage": round(100.0 * np.count_nonzero(changed) / changed.size, 6)},
        "outputs": {"absolute_difference": rel(abs_path), "changed_mask": rel(mask_path), "signed_visualization": rel(signed_path), "comparison_figure": rel(panel_path)},
    }
    return metrics, f"frames {first_index} and {second_index}: {metrics['difference']['changed_percentage']:.1f}% changed pixels"


def add_salt_pepper(frame: np.ndarray, rng: np.random.Generator, amount: float) -> np.ndarray:
    noisy = frame.copy()
    selector = rng.random(frame.shape[:2])
    noisy[selector < amount / 2] = 0
    noisy[(selector >= amount / 2) & (selector < amount)] = 255
    return noisy


def question_8() -> tuple[dict[str, Any], str]:
    out = reset_dir(OUTPUTS / "q8")
    info = video_info(DEMO_VIDEO)
    noisy_path, filtered_path = out / "salt_pepper_noisy.avi", out / "median_filtered.avi"
    noisy_writer = open_writer(noisy_path, info["fps"], (info["width"], info["height"]))
    filtered_writer = open_writer(filtered_path, info["fps"], (info["width"], info["height"]))
    rng = np.random.default_rng(RNG_SEED)
    amount = 0.035
    noisy_sse = filtered_sse = 0.0
    value_count = 0
    sample: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
    try:
        for index, original in iter_video(DEMO_VIDEO):
            noisy = add_salt_pepper(original, rng, amount)
            filtered = cv2.medianBlur(noisy, 3)
            noisy_error = original.astype(np.float64) - noisy.astype(np.float64)
            filtered_error = original.astype(np.float64) - filtered.astype(np.float64)
            noisy_sse += float(np.sum(noisy_error * noisy_error))
            filtered_sse += float(np.sum(filtered_error * filtered_error))
            value_count += original.size
            noisy_writer.write(noisy)
            filtered_writer.write(filtered)
            if index == 40:
                sample = (original.copy(), noisy.copy(), filtered.copy())
    finally:
        noisy_writer.release()
        filtered_writer.release()
    if sample is None:
        raise RuntimeError("Could not collect the filtering sample frame")
    noisy_mse, filtered_mse = noisy_sse / value_count, filtered_sse / value_count
    noisy_psnr = 10 * math.log10(255**2 / noisy_mse)
    filtered_psnr = 10 * math.log10(255**2 / filtered_mse)
    panel_path = out / "spatial_filtering_comparison.png"
    save_panel(panel_path, [("Original frame", sample[0], None), ("Deterministic salt-and-pepper noise", sample[1], None), ("3x3 median-filtered frame", sample[2], None)])
    metrics = {
        "title": "Spatial filtering of all video frames",
        "noise": {"type": "salt and pepper", "amount": amount, "rng_seed": RNG_SEED},
        "filter": {"type": "median", "kernel_size": 3, "all_frames_processed": info["frame_count"]},
        "before_filtering": {"mse_vs_original": round(noisy_mse, 6), "psnr_db_vs_original": round(noisy_psnr, 6)},
        "after_filtering": {"mse_vs_original": round(filtered_mse, 6), "psnr_db_vs_original": round(filtered_psnr, 6), "psnr_improvement_db": round(filtered_psnr - noisy_psnr, 6), "mse_reduction_percent": round(100 * (1 - filtered_mse / noisy_mse), 6)},
        "outputs": {"noisy_video": rel(noisy_path), "filtered_video": rel(filtered_path), "comparison_figure": rel(panel_path)},
    }
    return metrics, f"median filter improved PSNR by {filtered_psnr - noisy_psnr:.2f} dB over {info['frame_count']} frames"


def ffmpeg_exe() -> Path:
    path = Path(imageio_ffmpeg.get_ffmpeg_exe())
    if not path.exists():
        raise FileNotFoundError("FFmpeg was not found. Install imageio-ffmpeg in the selected Python environment.")
    return path


def run_ffmpeg(arguments: list[str], timeout: int = 180, text_output: bool = True) -> subprocess.CompletedProcess[Any]:
    command = [str(ffmpeg_exe()), "-hide_banner", "-loglevel", "error", "-nostdin", *arguments]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=text_output, timeout=timeout)
    if result.returncode != 0:
        error = result.stderr.strip() if text_output else result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"FFmpeg failed ({result.returncode}): {error}")
    return result


def encode_h264(source: Path, destination: Path, crf: int) -> None:
    ensure_dir(destination.parent)
    run_ffmpeg(["-y", "-i", str(source), "-an", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(destination)])


def compare_decoded_videos(reference: Path, test: Path) -> dict[str, Any]:
    reference_info, test_info = video_info(reference), video_info(test)
    if (reference_info["width"], reference_info["height"]) != (test_info["width"], test_info["height"]):
        raise ValueError(f"Video dimensions differ: {reference_info['width']}x{reference_info['height']} versus {test_info['width']}x{test_info['height']}")
    if reference_info["frame_count"] != test_info["frame_count"]:
        raise ValueError(f"Video frame counts differ: {reference_info['frame_count']} versus {test_info['frame_count']}")
    if abs(float(reference_info["fps"]) - float(test_info["fps"])) > 0.01:
        raise ValueError(f"Video frame rates differ: {reference_info['fps']} versus {test_info['fps']}")
    ref_capture, test_capture = cv2.VideoCapture(str(reference)), cv2.VideoCapture(str(test))
    if not ref_capture.isOpened() or not test_capture.isOpened():
        ref_capture.release()
        test_capture.release()
        raise FileNotFoundError(f"Could not decode comparison videos: {reference}, {test}")
    sse = 0.0
    count = values = 0
    frame_psnr: list[float] = []
    try:
        while True:
            ref_ok, ref_frame = ref_capture.read()
            test_ok, test_frame = test_capture.read()
            if ref_ok != test_ok:
                raise ValueError("One decoder ended before the other")
            if not ref_ok:
                break
            if ref_frame.shape != test_frame.shape:
                raise ValueError(f"Decoded frame shapes differ: {ref_frame.shape} versus {test_frame.shape}")
            error = ref_frame.astype(np.float64) - test_frame.astype(np.float64)
            frame_mse = float(np.mean(error * error))
            sse += float(np.sum(error * error))
            values += error.size
            count += 1
            frame_psnr.append(math.inf if frame_mse == 0 else 10 * math.log10(255**2 / frame_mse))
    finally:
        ref_capture.release()
        test_capture.release()
    if count != reference_info["frame_count"]:
        raise ValueError(f"Decoded {count} paired frames, expected {reference_info['frame_count']}")
    if count == 0:
        raise RuntimeError("No paired frames were available for quality comparison")
    mse = sse / values
    finite = [v for v in frame_psnr if math.isfinite(v)]
    return {"paired_frame_count": count, "fps_match": True, "dimensions_match": True, "mse": round(mse, 6), "psnr_db": json_number(math.inf if mse == 0 else 10 * math.log10(255**2 / mse)), "finite_frame_psnr_mean_db": round(float(np.mean(finite)), 6) if finite else None}


def available_sources() -> list[tuple[str, Path]]:
    sources = [("generated", DEMO_VIDEO)]
    if REAL_VIDEO.exists():
        sources.append(("real", REAL_VIDEO))
    return sources


def question_9() -> tuple[dict[str, Any], str]:
    out = reset_dir(OUTPUTS / "q9")
    results: dict[str, Any] = {}
    plot_names, plot_sizes, plot_psnr = [], [], []
    evidence_items: list[tuple[str, np.ndarray, str | None]] = []
    for name, source in available_sources():
        crf = 29 if name == "generated" else 30
        encoded = out / f"{name}_h264_crf{crf}.mp4"
        encode_h264(source, encoded, crf)
        source_info, encoded_info = video_info(source), video_info(encoded)
        quality = compare_decoded_videos(source, encoded)
        results[name] = {
            "reference": source_info,
            "compressed": encoded_info,
            "encoder": {"codec": "H.264/libx264", "crf": crf, "preset": "medium", "pixel_format": "yuv420p"},
            "quality": quality,
            "compression_ratio_reference_to_compressed": round(source_info["size_bytes"] / encoded_info["size_bytes"], 6),
            "size_reduction_percent": round(100 * (1 - encoded_info["size_bytes"] / source_info["size_bytes"]), 6),
        }
        sample_index = min(60, source_info["frame_count"] - 1)
        reference_frame, compressed_frame = frame_at(source, sample_index), frame_at(encoded, sample_index)
        label = "Generated" if name == "generated" else "Real Sintel"
        evidence_items.extend([
            (f"{label} decoded reference, frame {sample_index}", reference_frame, None),
            (f"{label} H.264 reconstruction, frame {sample_index}", compressed_frame, None),
            (f"{label} reference center detail", center_crop(reference_frame, source_info["width"] // 3, source_info["height"] // 3), None),
            (f"{label} compressed center detail", center_crop(compressed_frame, source_info["width"] // 3, source_info["height"] // 3), None),
        ])
        plot_names.append(name.capitalize())
        plot_sizes.append(results[name]["size_reduction_percent"])
        plot_psnr.append(quality["psnr_db"] or 100)
    plot_path = out / "h264_size_quality_comparison.png"
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
    axes[0].bar(plot_names, plot_sizes, color=["#3976af", "#d66a3a"][: len(plot_names)])
    axes[0].set(title="H.264 size reduction", ylabel="Reduction versus reference file (%)")
    axes[0].grid(axis="y", alpha=0.3)
    axes[1].bar(plot_names, plot_psnr, color=["#3976af", "#d66a3a"][: len(plot_names)])
    axes[1].set(title="Decoded quality", ylabel="PSNR versus decoded reference (dB)")
    axes[1].grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)
    evidence_path = out / "h264_reconstructed_frame_evidence.png"
    save_panel(evidence_path, evidence_items, columns=4, figsize=(17, 4.2 * len(results)))
    source_note = None
    source_metadata = INPUTS / "real_clip_source.json"
    if source_metadata.exists():
        metadata = json.loads(source_metadata.read_text(encoding="utf-8"))
        source_note = metadata.get("reference_note")
    metrics = {
        "title": "H.264 compression before streaming",
        "reference_nuance": source_note or "The real clip is treated as a decoded reference; its acquisition history must be considered when interpreting quality.",
        "sources": results,
        "outputs": {"comparison_figure": rel(plot_path), "reconstructed_frame_evidence": rel(evidence_path)},
    }
    return metrics, "; ".join(f"{name} {data['size_reduction_percent']:.1f}% smaller, {data['quality']['psnr_db']:.2f} dB" for name, data in results.items())


HLS_LEVELS = [
    {"name": "low", "bitrate": "180k", "maxrate": "210k", "bufsize": "360k"},
    {"name": "medium", "bitrate": "420k", "maxrate": "480k", "bufsize": "840k"},
    {"name": "high", "bitrate": "850k", "maxrate": "950k", "bufsize": "1700k"},
]


def create_hls_ladder(source: Path, destination: Path) -> dict[str, Path]:
    reset_dir(destination)
    source_info = video_info(source)
    playlists: dict[str, Path] = {}
    for level in HLS_LEVELS:
        level_dir = ensure_dir(destination / level["name"])
        playlist = level_dir / "index.m3u8"
        segment_pattern = level_dir / "segment_%03d.ts"
        run_ffmpeg([
            "-y", "-i", str(source), "-an", "-c:v", "libx264", "-preset", "medium",
            "-b:v", level["bitrate"], "-maxrate", level["maxrate"], "-bufsize", level["bufsize"],
            "-pix_fmt", "yuv420p", "-flags", "+cgop", "-g", "48", "-keyint_min", "48", "-sc_threshold", "0",
            "-force_key_frames", "expr:gte(t,n_forced*2)", "-f", "hls", "-hls_time", "2", "-hls_playlist_type", "vod",
            "-hls_flags", "independent_segments", "-hls_segment_filename", str(segment_pattern), str(playlist),
        ])
        playlists[level["name"]] = playlist
    master = destination / "master.m3u8"
    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    bandwidths = {"low": 240000, "medium": 540000, "high": 1050000}
    for level in HLS_LEVELS:
        name = level["name"]
        lines.extend([
            f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidths[name]},RESOLUTION={source_info['width']}x{source_info['height']},NAME=\"{name}\"",
            f"{name}/index.m3u8",
        ])
    master.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"master": master, **playlists}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


@contextmanager
def local_http_server(port: int = 0):
    handler = partial(QuietHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def decode_to_raw_rgb(input_value: str) -> bytes:
    result = run_ffmpeg(["-i", input_value, "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], timeout=180, text_output=False)
    return result.stdout


def verify_hls_local_http(playlist: Path, port: int, width: int, height: int) -> dict[str, Any]:
    local_bytes = decode_to_raw_rgb(str(playlist))
    http_url = f"http://127.0.0.1:{port}/{rel(playlist)}"
    http_bytes = decode_to_raw_rgb(http_url)
    frame_bytes = width * height * 3
    if len(local_bytes) % frame_bytes or len(http_bytes) % frame_bytes:
        raise ValueError("Decoded HLS byte stream does not contain complete RGB frames")
    local_frames, http_frames = len(local_bytes) // frame_bytes, len(http_bytes) // frame_bytes
    local_hash, http_hash = hashlib.sha256(local_bytes).hexdigest(), hashlib.sha256(http_bytes).hexdigest()
    if local_frames != http_frames or local_hash != http_hash:
        raise ValueError("Local-file and localhost HTTP HLS decodes differ")
    return {
        "local_frame_count": local_frames,
        "http_frame_count": http_frames,
        "frame_counts_match": True,
        "decoded_rgb_sha256_local": local_hash,
        "decoded_rgb_sha256_http": http_hash,
        "decoded_content_matches": True,
        "validation_url": http_url,
    }


def create_mp4_preview(source: Path, destination: Path) -> None:
    encode_h264(source, destination, 24)


def write_demo_html(source_names: list[str]) -> Path:
    demo_path = OUTPUTS / "index.html"
    hls_script = ROOT / "assets" / "vendor" / "hls.min.js"
    cards = []
    for name in source_names:
        label = "Generated road scene" if name == "generated" else "Real Sintel excerpt"
        preview = f"q10/{name}_preview.mp4"
        master = f"q10/{name}_hls/master.m3u8"
        cards.append(f"""
        <section class="card">
          <h2>{html.escape(label)}</h2>
          <div class="grid">
            <div><h3>MP4 preview</h3><p>A conventional MP4 file for direct browser playback.</p><video controls preload="metadata" src="{preview}"></video></div>
            <div><h3>HLS adaptive stream</h3><p>A master playlist with 180, 420, and 850 kbit/s variants.</p><label for="level-{name}">Quality level:</label> <select id="level-{name}" disabled><option value="-1">Auto</option></select><video id="hls-{name}" controls preload="metadata"></video><p id="status-{name}" class="status"></p></div>
          </div>
        </section>""")
    vendor_tag = '<script src="/assets/vendor/hls.min.js"></script>' if hls_script.exists() else ""
    setups = []
    for name in source_names:
        setups.append(f"setupHls('hls-{name}', 'status-{name}', 'level-{name}', '/{rel(OUTPUTS / 'q10' / (name + '_hls') / 'master.m3u8')}');")
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>IVP Assignment Results</title>
<style>
:root{{--ink:#182232;--muted:#536174;--card:#fff;--accent:#2455a4;--bg:#eef2f6}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Segoe UI,Arial,sans-serif;line-height:1.5}}main{{max-width:1120px;margin:auto;padding:28px}}h1{{font-size:clamp(1.7rem,4vw,2.6rem);margin-bottom:.2rem}}h2{{color:var(--accent)}}.lead{{color:var(--muted);max-width:78ch}}.card{{background:var(--card);padding:20px;margin:20px 0;border-radius:14px;box-shadow:0 4px 20px #24364d16}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:22px}}video{{display:block;width:100%;margin-top:8px;background:#111;border-radius:8px;aspect-ratio:3/2}}select{{font:inherit;padding:.35rem .55rem;border:1px solid #aeb9c7;border-radius:6px;background:white}}.status{{color:var(--muted);font-size:.92rem}}code{{background:#e8edf4;padding:.1rem .35rem;border-radius:4px}}a{{color:var(--accent)}}
</style>{vendor_tag}</head><body><main>
<h1>Image and Video Processing Assignment</h1><p class="lead">Shuba Bhuvi Matam &middot; RA2311031010068. This page clearly separates ordinary MP4 previews from packaged HLS playback. Run <code>python assignment.py --serve</code> and open the printed localhost address.</p>
{''.join(cards)}
<section class="card"><h2>Real-clip attribution</h2><p><em>Sintel</em> trailer excerpt, &copy; Blender Foundation, licensed under <a href="https://creativecommons.org/licenses/by/3.0/">CC BY 3.0</a>. The 33&ndash;39 second excerpt was resized to 640&times;360, sampled at 24 fps, and stored losslessly from the decoded trailer without audio. The downloaded trailer was already compressed, so this reference does not recover the production master.</p></section>
<section class="card"><h2>Measured results</h2><p>All experiment values come from <a href="/outputs/metrics.json">outputs/metrics.json</a>. Comparison figures are available in each <code>outputs/qN</code> directory.</p></section>
<script>
function setupHls(videoId,statusId,selectId,url){{const video=document.getElementById(videoId),status=document.getElementById(statusId),select=document.getElementById(selectId),targetLabels=['Low - 180 kbit/s target','Medium - 420 kbit/s target','High - 850 kbit/s target'];if(video.canPlayType('application/vnd.apple.mpegurl')){{video.src=url;status.textContent='Native browser HLS playback. Manual level forcing is available in hls.js browsers.';}}else if(window.Hls&&Hls.isSupported()){{const hls=new Hls();hls.loadSource(url);hls.attachMedia(video);hls.on(Hls.Events.MANIFEST_PARSED,()=>{{hls.levels.forEach((level,index)=>{{const option=document.createElement('option');option.value=index;option.textContent=targetLabels[index]||('Level '+index);select.appendChild(option);}});select.disabled=false;status.textContent='hls.js loaded the three-variant master playlist in Auto mode.';}});select.addEventListener('change',()=>{{hls.currentLevel=Number(select.value);status.textContent=select.value==='-1'?'Auto adaptive level selected.':'Manually forced '+select.options[select.selectedIndex].textContent+'.';}});hls.on(Hls.Events.ERROR,(_,data)=>{{if(data.fatal)status.textContent='HLS playback error: '+data.details;}});}}else{{status.textContent='This browser cannot play HLS. FFmpeg HTTP validation is still recorded in metrics.json.';}}}}
{''.join(setups)}
</script></main></body></html>"""
    demo_path.write_text(document, encoding="utf-8")
    return demo_path


def question_10() -> tuple[dict[str, Any], str]:
    out = reset_dir(OUTPUTS / "q10")
    source_results: dict[str, Any] = {}
    sources = available_sources()
    generated_playlists: dict[str, dict[str, Path]] = {}
    for name, source in sources:
        preview = out / f"{name}_preview.mp4"
        create_mp4_preview(source, preview)
        generated_playlists[name] = create_hls_ladder(source, out / f"{name}_hls")
        source_results[name] = {"reference": video_info(source), "mp4_preview": video_info(preview), "variants": {}}
    with local_http_server(0) as port:
        for name, source in sources:
            source_info = video_info(source)
            for level in HLS_LEVELS:
                playlist = generated_playlists[name][level["name"]]
                segments = sorted(playlist.parent.glob("segment_*.ts"))
                segment_bytes = sum(file_size(path) for path in segments)
                playlist_bytes = file_size(playlist)
                verification = verify_hls_local_http(playlist, port, source_info["width"], source_info["height"])
                if verification["local_frame_count"] != source_info["frame_count"]:
                    raise ValueError(f"HLS variant {name}/{level['name']} decoded {verification['local_frame_count']} frames; expected {source_info['frame_count']}")
                source_results[name]["variants"][level["name"]] = {
                    "target_bitrate": level["bitrate"],
                    "playlist": rel(playlist),
                    "segments": [rel(path) for path in segments],
                    "segment_count": len(segments),
                    "segment_data_size_bytes": segment_bytes,
                    "playlist_size_bytes": playlist_bytes,
                    "package_size_bytes": playlist_bytes + segment_bytes,
                    "actual_segment_data_bitrate_kbps": round(segment_bytes * 8 / float(source_info["duration_seconds"]) / 1000, 6),
                    "package_bitrate_including_playlist_kbps": round((playlist_bytes + segment_bytes) * 8 / float(source_info["duration_seconds"]) / 1000, 6),
                    "quality_vs_reference": compare_decoded_videos(source, playlist),
                    "local_vs_http_verification": verification,
                }
            source_results[name]["master_playlist"] = rel(generated_playlists[name]["master"])
    evidence_name = "real" if "real" in source_results else "generated"
    evidence_source = REAL_VIDEO if evidence_name == "real" else DEMO_VIDEO
    evidence_info = video_info(evidence_source)
    evidence_index = min(72, evidence_info["frame_count"] - 1)
    evidence_frames: dict[str, np.ndarray] = {"reference": frame_at(evidence_source, evidence_index)}
    for level in HLS_LEVELS:
        evidence_frames[level["name"]] = frame_at(generated_playlists[evidence_name][level["name"]], evidence_index)
    evidence_path = out / "hls_bitrate_reconstructed_frame_evidence.png"
    crop_width, crop_height = evidence_info["width"] // 3, evidence_info["height"] // 3
    save_panel(evidence_path, [
        (f"{evidence_name.capitalize()} decoded reference, frame {evidence_index}", evidence_frames["reference"], None),
        ("HLS low: 180 kbit/s", evidence_frames["low"], None),
        ("HLS medium: 420 kbit/s", evidence_frames["medium"], None),
        ("HLS high: 850 kbit/s", evidence_frames["high"], None),
        ("Reference center detail", center_crop(evidence_frames["reference"], crop_width, crop_height), None),
        ("Low-bitrate center detail", center_crop(evidence_frames["low"], crop_width, crop_height), None),
        ("Medium-bitrate center detail", center_crop(evidence_frames["medium"], crop_width, crop_height), None),
        ("High-bitrate center detail", center_crop(evidence_frames["high"], crop_width, crop_height), None),
    ], columns=4, figsize=(17, 8.5))
    plot_path = out / "bitrate_size_quality.png"
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    colors = {"generated": "#3976af", "real": "#d66a3a"}
    numeric_rates = [180, 420, 850]
    for name, data in source_results.items():
        qualities = [data["variants"][level["name"]]["quality_vs_reference"]["psnr_db"] for level in HLS_LEVELS]
        sizes = [data["variants"][level["name"]]["package_size_bytes"] / 1024 for level in HLS_LEVELS]
        axes[0].plot(numeric_rates, qualities, marker="o", linewidth=2, label=name.capitalize(), color=colors[name])
        axes[1].plot(numeric_rates, sizes, marker="o", linewidth=2, label=name.capitalize(), color=colors[name])
    axes[0].set(title="HLS target bitrate versus decoded quality", xlabel="Target video bitrate (kbit/s)", ylabel="PSNR versus decoded reference (dB)")
    axes[1].set(title="HLS target bitrate versus package size", xlabel="Target video bitrate (kbit/s)", ylabel="Playlist + transport-stream segments (KiB)")
    for axis in axes:
        axis.grid(alpha=0.3)
        axis.legend()
    fig.tight_layout()
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)
    demo_path = write_demo_html([name for name, _ in sources])
    metrics = {
        "title": "Video streaming with three meaningful target bitrates",
        "method": "Package independent 2-second HLS transport-stream segments at 180, 420, and 850 kbit/s. During --all, serve the repository on an ephemeral localhost port and require byte-identical RGB decodes through local-file and HTTP playlist access.",
        "http_validation": {"host": "127.0.0.1", "ephemeral_port_used": True, "server_stopped_after_validation": True},
        "sources": source_results,
        "outputs": {"quality_size_plot": rel(plot_path), "reconstructed_frame_evidence": rel(evidence_path), "local_demo": rel(demo_path)},
    }
    verified = sum(len(data["variants"]) for data in source_results.values())
    return metrics, f"packaged and localhost-verified {verified} HLS variants across {len(source_results)} sources"


QUESTIONS = {
    1: question_1,
    2: question_2,
    3: question_3,
    4: question_4,
    5: question_5,
    6: question_6,
    7: question_7,
    8: question_8,
    9: question_9,
    10: question_10,
}


def environment_metrics() -> dict[str, Any]:
    return {
        "author": "Shuba Bhuvi Matam",
        "registration_number": "RA2311031010068",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "opencv": cv2.__version__,
        "matplotlib": matplotlib.__version__,
        "imageio_ffmpeg": imageio_ffmpeg.__version__,
        "ffmpeg_executable": ffmpeg_exe().name,
        "ffmpeg_version": run_ffmpeg(["-version"]).stdout.splitlines()[0],
    }


def load_metrics() -> dict[str, Any]:
    if METRICS_FILE.exists():
        try:
            data = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return {}


def run_questions(question_numbers: list[int]) -> dict[str, Any]:
    ensure_dir(OUTPUTS)
    inputs = generate_inputs(force=False)
    metrics = load_metrics()
    metrics["environment"] = environment_metrics()
    metrics["inputs"] = inputs
    started = time.perf_counter()
    print(f"IVP assignment run: questions {', '.join(map(str, question_numbers))}", flush=True)
    for number in question_numbers:
        question_started = time.perf_counter()
        try:
            result, summary = QUESTIONS[number]()
            result["runtime_seconds"] = round(time.perf_counter() - question_started, 3)
            metrics[f"q{number}"] = result
            METRICS_FILE.write_text(json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            print(f"Q{number:02d} PASS - {summary}", flush=True)
        except Exception as error:
            print(f"Q{number:02d} FAIL - {error}", flush=True)
            raise
    metrics["run_summary"] = {
        "questions_completed": question_numbers,
        "question_count": len(question_numbers),
        "total_runtime_seconds": round(time.perf_counter() - started, 3),
        "metrics_file": rel(METRICS_FILE),
        "html_demo": rel(OUTPUTS / "index.html") if (OUTPUTS / "index.html").exists() else None,
    }
    METRICS_FILE.write_text(json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"SUMMARY PASS - {len(question_numbers)} question(s), metrics: {rel(METRICS_FILE)}", flush=True)
    if (OUTPUTS / "index.html").exists():
        print(f"HTML demo: http://127.0.0.1:8000/outputs/index.html (run with --serve)", flush=True)
    return metrics


def serve(port: int) -> None:
    if not (OUTPUTS / "index.html").exists():
        raise FileNotFoundError("outputs/index.html does not exist. Run --all or --question 10 first.")
    handler = partial(QuietHandler, directory=str(ROOT))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    except OSError as error:
        raise OSError(f"Could not start localhost server on port {port}: {error}") from error
    address = f"http://127.0.0.1:{server.server_address[1]}/outputs/index.html"
    print(f"Serving assignment results at {address}", flush=True)
    print("Press Ctrl+C to stop the localhost-only server.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.", flush=True)
    finally:
        server.server_close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ten Image and Video Processing assignment experiments.")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--all", action="store_true", help="Run all ten experiments (default).")
    selection.add_argument("--question", type=int, choices=range(1, 11), metavar="N", help="Run only question N (1-10).")
    selection.add_argument("--generate-inputs", action="store_true", help="Regenerate the deterministic image and AVI inputs, then exit.")
    selection.add_argument("--serve", action="store_true", help="Serve outputs and vendored assets on localhost only.")
    parser.add_argument("--port", type=int, default=8000, help="Local port for --serve; use 0 for an ephemeral port (default: 8000).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.generate_inputs:
            details = generate_inputs(force=True)
            print(f"Generated {details['generated_image']['path']} and {details['generated_video']['path']}", flush=True)
            return 0
        if args.serve:
            serve(args.port)
            return 0
        run_questions([args.question] if args.question else list(range(1, 11)))
        return 0
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
