"""
Project Extra — High-Speed Raster-to-Spline Vectorizer & Stroke Synthesizer
Converts reference bitmap drawings into fluid Catmull-Rom vector brush strokes
ready for sub-millisecond execution via extra_batch_actions or extra_stroke.

Follows the Universal Engine Invariant: Zero application-specific hardcoding.
Pure NumPy and Pillow — Zero heavy native dependencies.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageFilter

logger = logging.getLogger("extra.fastpath.vectorizer")

# Standard 20-Color Palette Matrix (RGB)
STANDARD_PALETTE: Dict[str, Tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "dark_gray": (127, 127, 127),
    "maroon": (136, 0, 21),
    "red": (237, 28, 36),
    "orange": (255, 127, 39),
    "yellow": (255, 201, 14),
    "lime": (181, 230, 29),
    "turquoise": (153, 217, 234),
    "slate": (112, 146, 190),
    "purple": (200, 191, 231),
    "white": (255, 255, 255),
    "light_gray": (195, 195, 195),
    "brown": (185, 122, 87),
    "pink": (255, 174, 201),
    "light_orange": (255, 201, 14),
    "light_yellow": (239, 228, 176),
    "green": (34, 177, 76),
    "aqua": (0, 162, 232),
    "blue": (63, 72, 204),
    "lavender": (163, 73, 164),
}

# Standard Windows 11 MS Paint Palette Coordinates (Calibrated for 1366x768 & 1920x1080)
DEFAULT_PAINT_SWATCHES: Dict[str, Tuple[int, int]] = {
    # Row 1 (y = 83)
    "black": (791, 83),
    "dark_gray": (815, 83),
    "maroon": (839, 83),
    "red": (863, 83),
    "orange": (887, 83),
    "yellow": (911, 83),
    "lime": (935, 83),
    "turquoise": (959, 83),
    "slate": (983, 83),
    "purple": (1007, 83),
    # Row 2 (y = 107)
    "white": (791, 107),
    "light_gray": (815, 107),
    "brown": (839, 107),
    "pink": (863, 107),
    "light_orange": (887, 107),
    "light_yellow": (911, 107),
    "green": (935, 107),
    "aqua": (959, 107),
    "blue": (983, 107),
    "lavender": (1007, 107),
}


def douglas_peucker(points: List[Tuple[float, float]], epsilon: float = 3.0) -> List[Tuple[float, float]]:
    """
    Ramer-Douglas-Peucker algorithm for polyline simplification.
    Reduces dense pixel contours into minimal coarse anchor points for Catmull-Rom splines.
    """
    if len(points) <= 2:
        return points

    p1 = points[0]
    p2 = points[-1]
    dx = float(p2[0] - p1[0])
    dy = float(p2[1] - p1[1])
    line_len = (dx * dx + dy * dy) ** 0.5

    dmax = 0.0
    index = 0
    for i in range(1, len(points) - 1):
        p = points[i]
        if line_len == 0.0:
            d = ((p[0] - p1[0]) ** 2 + (p[1] - p1[1]) ** 2) ** 0.5
        else:
            # Perpendicular distance in 2D: |dx * (y1 - y0) - dy * (x1 - x0)| / line_len
            d = abs(dx * (p1[1] - p[1]) - dy * (p1[0] - p[0])) / line_len

        if d > dmax:
            index = i
            dmax = d

    if dmax > epsilon:
        res1 = douglas_peucker(points[:index + 1], epsilon)
        res2 = douglas_peucker(points[index:], epsilon)
        return res1[:-1] + res2
    else:
        return [points[0], points[-1]]


def match_nearest_color(
    rgb: Tuple[int, int, int],
    palette: Dict[str, Tuple[int, int, int]] = STANDARD_PALETTE,
) -> str:
    """Finds the closest named palette color using Euclidean RGB distance."""
    r0, g0, b0 = rgb
    best_name = "black"
    best_dist = float("inf")

    for name, (pr, pg, pb) in palette.items():
        # Weighted RGB distance matching human visual perception (rec. 601)
        dist = 0.3 * (r0 - pr) ** 2 + 0.59 * (g0 - pg) ** 2 + 0.11 * (b0 - pb) ** 2
        if dist < best_dist:
            best_dist = dist
            best_name = name

    return best_name


def _trace_chains(edge_mask: np.ndarray, min_chain_len: int = 8) -> List[List[Tuple[int, int]]]:
    """
    Extracts continuous directional stroke chains from an edge pixel mask.
    Fast, pure NumPy/Python graph walk without requiring OpenCV.
    """
    h, w = edge_mask.shape
    visited = np.zeros((h, w), dtype=bool)
    chains: List[List[Tuple[int, int]]] = []

    # Get edge pixel coordinates
    ys, xs = np.nonzero(edge_mask)
    if len(ys) == 0:
        return []

    # 8-connectivity neighbor offsets
    neighbors = [
        (-1, 0), (1, 0), (0, -1), (0, 1),
        (-1, -1), (-1, 1), (1, -1), (1, 1)
    ]

    for start_y, start_x in zip(ys, xs):
        if visited[start_y, start_x]:
            continue

        chain = [(int(start_x), int(start_y))]
        visited[start_y, start_x] = True
        curr_y, curr_x = start_y, start_x

        # Walk connected path
        while True:
            next_pt = None
            for dy, dx in neighbors:
                ny, nx = curr_y + dy, curr_x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    if edge_mask[ny, nx] and not visited[ny, nx]:
                        next_pt = (ny, nx)
                        break

            if next_pt is not None:
                curr_y, curr_x = next_pt
                visited[curr_y, curr_x] = True
                chain.append((int(curr_x), int(curr_y)))
            else:
                break

        if len(chain) >= min_chain_len:
            chains.append(chain)

    return chains


def extract_vector_strokes(
    image_path: Union[str, Path],
    canvas_bounds: Tuple[int, int, int, int] = (100, 180, 1250, 670),
    max_strokes: int = 60,
    min_stroke_len: int = 10,
    swatch_map: Optional[Dict[str, Tuple[int, int]]] = None,
    simplify_epsilon: float = 4.0,
    stage_sorting: bool = True,
) -> List[Dict[str, Any]]:
    """
    Synthesizes smooth, multi-colored Catmull-Rom vector brush strokes from a raster image.
    Designed to run in ONE turn via extra_execute_bridge or fast-path.

    Args:
        image_path: Path to the reference bitmap image.
        canvas_bounds: Target bounding box (min_x, min_y, max_x, max_y) on desktop display.
        max_strokes: Maximum total brush strokes to generate.
        min_stroke_len: Minimum pixels for a feature to be considered a stroke.
        swatch_map: Dictionary of color name -> (click_x, click_y). Defaults to Windows Paint.
        simplify_epsilon: Douglas-Peucker tolerance. Higher values produce smoother, coarser curves.
        stage_sorting: If True, orders strokes: broad washes first, linework/anatomy second.

    Returns:
        List of batch actions ready for extra_batch_actions dispatch.
    """
    p = Path(image_path)
    if not p.is_file():
        raise FileNotFoundError(f"Reference image not found: {image_path}")

    if swatch_map is None:
        swatch_map = DEFAULT_PAINT_SWATCHES

    img = Image.open(p).convert("RGB")
    src_w, src_h = img.size
    arr = np.array(img)

    # 1. White/near-white background isolation
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    diff = np.maximum(np.maximum(np.abs(r - g), np.abs(r - b)), np.abs(g - b))
    is_bg = (r > 220) & (g > 220) & (b > 220) & (diff < 30)
    foreground_mask = ~is_bg
    if np.sum(foreground_mask) < (src_w * src_h * 0.05):
        foreground_mask = np.ones((src_h, src_w), dtype=bool)

    # 2. Extract edge contours via spatial gradients
    gray = np.mean(arr[:, :, :3], axis=2).astype(float)
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[:, 1:-1] = (gray[:, 2:] - gray[:, :-2]) / 2.0
    gy[1:-1, :] = (gray[2:, :] - gray[:-2, :]) / 2.0
    grad = np.hypot(gx, gy)

    edge_arr = (grad > 20) & foreground_mask
    if np.sum(edge_arr) < 20:
        edge_arr = grad > 15

    # 3. Trace vector stroke chains
    raw_chains = _trace_chains(edge_arr, min_chain_len=min_stroke_len)

    # Calculate coordinate scaling preserving aspect ratio
    min_cx, min_cy, max_cx, max_cy = canvas_bounds
    target_w = max_cx - min_cx
    target_h = max_cy - min_cy

    scale = min(target_w / float(src_w), target_h / float(src_h)) * 0.92
    offset_x = min_cx + (target_w - src_w * scale) / 2.0
    offset_y = min_cy + (target_h - src_h * scale) / 2.0

    # 4. Simplify chains and map to dominant colors
    stroke_records: List[Dict[str, Any]] = []

    for chain in raw_chains:
        # Douglas-Peucker polyline simplification into 4-12 coarse anchors
        simplified = douglas_peucker(chain, epsilon=simplify_epsilon)
        if len(simplified) < 2:
            continue

        # Determine dominant color for this stroke
        sample_pts = [chain[len(chain) // 4], chain[len(chain) // 2], chain[3 * len(chain) // 4]]
        sample_colors = [arr[pt[1], pt[0], :3] for pt in sample_pts if 0 <= pt[1] < src_h and 0 <= pt[0] < src_w]
        if sample_colors:
            avg_rgb = tuple(int(np.mean([c[i] for c in sample_colors])) for i in range(3))
        else:
            avg_rgb = (0, 0, 0)

        color_name = match_nearest_color(avg_rgb)

        # Scale points to target canvas coordinates
        scaled_points = []
        for px, py in simplified:
            tx = int(round(offset_x + px * scale))
            ty = int(round(offset_y + py * scale))
            scaled_points.append([tx, ty])

        stroke_records.append({
            "color": color_name,
            "points": scaled_points,
            "length": len(chain),
            "is_dark": color_name in ("black", "dark_gray", "maroon", "slate"),
        })

    # Sort strokes: longer strokes first, color washes before dark linework
    if stage_sorting:
        stroke_records.sort(key=lambda s: (1 if s["is_dark"] else 0, -s["length"]))
    else:
        stroke_records.sort(key=lambda s: -s["length"])

    # Limit to max_strokes to guarantee rapid turn budget compliance
    selected = stroke_records[:max_strokes]

    # 5. Synthesize final batch actions
    actions: List[Dict[str, Any]] = []
    current_color: Optional[str] = None

    for s in selected:
        c_name = s["color"]
        # Click new color swatch if changed
        if c_name != current_color:
            if c_name in swatch_map:
                sx, sy = swatch_map[c_name]
                actions.append({
                    "action": "click",
                    "x": sx,
                    "y": sy,
                    "semantic": f"color_{c_name}",
                })
                current_color = c_name

        # Dispatch smooth Catmull-Rom stroke
        actions.append({
            "action": "stroke",
            "points": s["points"],
            "smooth": True,
            "duration": 0.4,
        })

    logger.info(
        "[Vectorizer] Synthesized %d batch actions from %s (%d strokes)",
        len(actions), p.name, len(selected)
    )
    return actions


def generate_vectorizer_preview(
    actions: List[Dict[str, Any]],
    output_path: Union[str, Path],
    canvas_size: Tuple[int, int] = (1366, 768),
) -> Path:
    """
    Renders an in-memory preview of the synthesized actions for diagnostic verification.
    """
    from PIL import ImageDraw
    from extra.core.motion.curves import generate_catmull_rom_spline

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    im = Image.new("RGB", canvas_size, (255, 255, 255))
    draw = ImageDraw.Draw(im)

    curr_color = (0, 0, 0)
    # Reverse lookup from coordinate to RGB
    coord_to_color: Dict[Tuple[int, int], Tuple[int, int, int]] = {
        pos: STANDARD_PALETTE[name]
        for name, pos in DEFAULT_PAINT_SWATCHES.items()
        if name in STANDARD_PALETTE
    }

    for a in actions:
        act = a.get("action")
        if act == "click":
            pos = (a.get("x", 0), a.get("y", 0))
            if pos in coord_to_color:
                curr_color = coord_to_color[pos]
        elif act == "stroke":
            pts = a.get("points", [])
            if len(pts) >= 2:
                # Use Catmull-Rom spline
                spline_pts = generate_catmull_rom_spline(pts, steps_per_segment=10)
                for i in range(len(spline_pts) - 1):
                    draw.line([spline_pts[i], spline_pts[i + 1]], fill=curr_color, width=3)

    im.save(out_p)
    return out_p
