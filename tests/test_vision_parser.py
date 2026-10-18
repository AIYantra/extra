"""
Project Extra — Edge Vision Parser Test Suite
Validates the on-device computer vision engine for opaque canvas applications (Canva, Figma, Blender, WebGL):
1. Visual UI region detection (buttons, inputs, icons) from raw pixels.
2. Aspect ratio classification and boundary deduplication.
3. Semantic visual grounding on synthetic opaque canvas buffers.
4. SoulEyes integration (Tier 1 Edge Vision fallback before heuristics).
5. UIDistiller integration with force_vision=True (source='vision_tier1').
6. Sub-35ms latency benchmarks on pure NumPy + PIL.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extra.core.distiller import distill_screen
from extra.core.soul.eyes import SoulEyes, get_soul_eyes
from extra.core.soul.vision_parser import (
    EdgeVisionParser,
    VisualRegion,
    parse_opaque_canvas,
)


def create_synthetic_canvas_image(width: int = 1200, height: int = 800) -> Image.Image:
    """
    Renders an opaque UI resembling an Electron canvas app (e.g. Canva / Figma / WebGL):
    - Dark gray background (30, 30, 35)
    - Top header bar with buttons ('Export', 'Share', 'Settings')
    - Search input box
    - Left tool rail with square icon buttons
    - Center drawing workspace
    """
    img = Image.new("RGB", (width, height), (32, 34, 38))
    draw = ImageDraw.Draw(img)

    # 1. Header bar
    draw.rectangle([0, 0, width, 55], fill=(24, 25, 28))

    # Top Search input box (wide, outlined)
    draw.rectangle([100, 10, 400, 45], fill=(42, 45, 52), outline=(70, 75, 85), width=2)

    # Top 'Share' button (compact rectangle)
    draw.rectangle([950, 10, 1050, 45], fill=(60, 64, 72), outline=(90, 95, 105), width=2)

    # Top 'Export' accent button (purple/blue pill)
    draw.rectangle([1070, 10, 1180, 45], fill=(100, 50, 220), outline=(130, 80, 250), width=2)

    # 2. Left Tool Rail
    draw.rectangle([0, 55, 65, height], fill=(24, 25, 28))

    # Square Tool Icons
    draw.rectangle([12, 75, 52, 115], fill=(45, 48, 55), outline=(75, 80, 90), width=1)
    draw.rectangle([12, 135, 52, 175], fill=(45, 48, 55), outline=(75, 80, 90), width=1)
    draw.rectangle([12, 195, 52, 235], fill=(45, 48, 55), outline=(75, 80, 90), width=1)

    # 3. Center Canvas Card
    draw.rectangle([200, 120, 1000, 720], fill=(245, 245, 245), outline=(200, 200, 200), width=2)

    return img


def test_edge_region_detection() -> None:
    print("[Test 1] Detecting visual regions on opaque synthetic canvas...", end=" ")
    img = create_synthetic_canvas_image()
    parser = EdgeVisionParser()

    t0 = time.perf_counter()
    regions = parser.detect_regions(img)
    dt_ms = (time.perf_counter() - t0) * 1000.0

    assert len(regions) >= 4, f"Expected at least 4 visual regions, detected {len(regions)}"
    categories = [r.category for r in regions]
    assert "button" in categories or "icon" in categories, "Expected buttons or icons to be detected"
    print(f"PASSED ({len(regions)} regions detected in {dt_ms:.2f}ms)")


def test_element_parsing_and_offsets() -> None:
    print("[Test 2] Converting visual regions to UIElements with screen offsets...", end=" ")
    img = create_synthetic_canvas_image()
    offset = (150, 100)
    elements = parse_opaque_canvas(img, offset=offset)

    assert len(elements) >= 4, f"Expected >= 4 elements, got {len(elements)}"
    for el in elements:
        assert el.bounding_box[0] >= offset[0], "Bounding box left should include offset"
        assert el.bounding_box[1] >= offset[1], "Bounding box top should include offset"
        assert el.center[0] >= offset[0], "Center X should include offset"
        assert el.center[1] >= offset[1], "Center Y should include offset"
        assert el.control_type in ("Button", "Edit", "Text"), f"Unexpected control type: {el.control_type}"
    print(f"PASSED ({len(elements)} UIElements generated with valid physical offsets)")


def test_semantic_visual_grounding() -> None:
    print("[Test 3] Edge vision visual grounding queries...", end=" ")
    img = create_synthetic_canvas_image()
    parser = EdgeVisionParser()

    # Query for general button
    match_btn = parser.ground_query(img, "button")
    assert match_btn is not None, "Expected match for 'button'"
    cx, cy, sbox = match_btn
    assert 0 <= cx <= 1200 and 0 <= cy <= 800
    assert sbox.ymin >= 0.0 and sbox.ymax <= 1000.0

    # Query for input field
    match_input = parser.ground_query(img, "input")
    assert match_input is not None, "Expected match for 'input'"
    icx, icy, isbox = match_input
    assert 100 <= icx <= 400, f"Expected input center X near search box (100-400), got {icx}"
    print("PASSED")


def test_souleyes_integration() -> None:
    print("[Test 4] SoulEyes visual_ground integration with Edge Vision...", end=" ")
    img = create_synthetic_canvas_image()
    eyes = SoulEyes()

    # Clear cache for fresh evaluation
    eyes._id_cache.clear()
    eyes._cache.clear()

    res = eyes.visual_ground(image=img, query="input")
    assert res.matched is True, "SoulEyes should match 'input' via Edge Vision Parser"
    assert res.screen_point is not None
    assert res.metadata.get("model") == "soul_edge_vision_parser", f"Expected model 'soul_edge_vision_parser', got {res.metadata.get('model')}"
    print(f"PASSED (Grounded at {res.screen_point} in {res.latency_ms:.2f}ms)")


def test_distiller_force_vision_tier1() -> None:
    print("[Test 5] UIDistiller live distillation with force_vision=True...", end=" ")
    res = distill_screen(format="markdown", max_elements=25, force_vision=True)

    assert res.source == "vision_tier1", f"Expected source 'vision_tier1', got '{res.source}'"
    assert res.element_count > 0, "Expected at least 1 visual element to be detected"
    assert res.approx_tokens < 500
    assert res.token_savings_pct >= 65.0
    print(f"PASSED (Source: {res.source}, Elements: {res.element_count}, Tokens: ~{res.approx_tokens})")


def test_detect_work_surface_viewport() -> None:
    print("[Test 6] Universal Work Surface Viewport Detection...", end=" ")
    img = create_synthetic_canvas_image(1200, 800)
    parser = EdgeVisionParser()

    t0 = time.perf_counter()
    ws = parser.detect_work_surface(img)
    dt_ms = (time.perf_counter() - t0) * 1000.0

    assert ws is not None, "Expected WorkSurfaceViewport to be detected"
    assert ws.width >= 750, f"Expected width >= 750, got {ws.width}"
    assert ws.height >= 550, f"Expected height >= 550, got {ws.height}"
    assert dt_ms < 25.0, f"Expected latency < 25ms, got {dt_ms:.2f}ms"
    print(f"PASSED (Bounds: {ws.bounding_box}, Size: {ws.width}x{ws.height}, Latency: {dt_ms:.2f}ms)")


def run_all() -> None:
    print("=" * 65)
    print("  EXTRA PHASE 2: EDGE VISION PARSER VALIDATION SUITE")
    print("=" * 65)
    t0 = time.perf_counter()

    test_edge_region_detection()
    test_element_parsing_and_offsets()
    test_semantic_visual_grounding()
    test_souleyes_integration()
    test_distiller_force_vision_tier1()
    test_detect_work_surface_viewport()

    elapsed = (time.perf_counter() - t0) * 1000.0
    print("=" * 65)
    print(f"  ALL 6 PHASE 2 TESTS PASSED in {elapsed:.2f}ms")
    print("=" * 65)


if __name__ == "__main__":
    run_all()

