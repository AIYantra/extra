"""
Project Extra — Test Suite for MS Paint Remediation & Vectorizer Subsystem
Validates:
1. Subtask intent compilation for canvas reset / clearing (Pattern 9).
2. High-speed raster-to-spline vectorizer (extract_vector_strokes).
3. Color palette resolution and coordinate mapping.
4. In-memory and diagnostic preview rendering.
"""

from __future__ import annotations

from pathlib import Path
import pytest
from PIL import Image

from extra.core.subtask import SubtaskRunner
from extra.fastpath.vectorizer import (
    DEFAULT_PAINT_SWATCHES,
    STANDARD_PALETTE,
    douglas_peucker,
    extract_vector_strokes,
    generate_vectorizer_preview,
    match_nearest_color,
)


def test_canvas_reset_intent_compilation():
    """Verifies that natural language canvas reset intents compile into atomic focus+clear+brush actions."""
    runner = SubtaskRunner()

    # Intent with specified app
    actions = runner.compile_intent("clear canvas in paint")
    assert len(actions) == 9
    assert actions[0]["action"] == "focus"
    assert actions[0]["window_title"] == "paint"
    assert actions[1]["action"] == "click" and actions[1]["x"] == 500 and actions[1]["y"] == 400
    assert actions[2]["action"] == "hotkey" and actions[2]["keys"] == ["ctrl", "a"]
    assert actions[4]["action"] == "hotkey" and actions[4]["keys"] == ["delete"]
    assert actions[5]["action"] == "hotkey" and actions[5]["keys"] == ["esc"]
    assert actions[6]["action"] == "hotkey" and actions[6]["keys"] == ["b"]
    assert actions[7]["action"] == "click" and actions[7]["x"] == 500 and actions[7]["y"] == 400

    # Alternate phrasing
    reset_actions = runner.compile_intent("reset canvas in mspaint")
    assert len(reset_actions) == 9
    assert reset_actions[0]["window_title"] == "mspaint"

    # Start over with blank canvas (no explicit app)
    blank_actions = runner.compile_intent("start over with a blank canvas")
    assert len(blank_actions) == 8
    assert blank_actions[0]["action"] == "click"
    assert blank_actions[1]["action"] == "hotkey" and blank_actions[1]["keys"] == ["ctrl", "a"]
    assert blank_actions[4]["action"] == "hotkey" and blank_actions[4]["keys"] == ["esc"]
    assert blank_actions[5]["action"] == "hotkey" and blank_actions[5]["keys"] == ["b"]


def test_render_vector_stroke_no_redundant_click(monkeypatch):
    """Verifies that render_vector_stroke starts drawing with mouse_down directly (no double-click glitch)."""
    from unittest.mock import MagicMock
    import extra.core.platform.windows.input_engine as ie

    mock_click = MagicMock()
    mock_move = MagicMock()
    mock_down = MagicMock()
    mock_up = MagicMock()
    mock_send_move = MagicMock()

    monkeypatch.setattr(ie, "mouse_click", mock_click)
    monkeypatch.setattr(ie, "mouse_move", mock_move)
    monkeypatch.setattr(ie, "mouse_down", mock_down)
    monkeypatch.setattr(ie, "mouse_up", mock_up)
    monkeypatch.setattr(ie, "send_mouse_move_event", mock_send_move)
    monkeypatch.setattr(ie, "_notify_indicator", MagicMock())

    test_points = [(100, 100), (150, 150), (200, 200)]
    ie.mouse_stroke(test_points, duration=0.1, smooth=False)

    # STRICT ASSERTION: mouse_click must NEVER be called (prevents WM_LBUTTONDBLCLK)
    assert mock_click.call_count == 0, "mouse_click should not be called to avoid double-click glitch"
    # mouse_move must position cursor to start
    assert mock_move.call_count >= 1
    # mouse_down must initiate contact
    assert mock_down.call_count == 1
    # mouse_up must finalize contact
    assert mock_up.call_count == 1
    # send_mouse_move_event must dispatch stroke intermediate waypoints
    assert mock_send_move.call_count > 0



def test_douglas_peucker_simplification():
    """Verifies polyline simplification on synthetic curves."""
    straight_line = [(float(i), float(i)) for i in range(50)]
    simplified = douglas_peucker(straight_line, epsilon=1.0)
    assert len(simplified) == 2
    assert simplified[0] == (0.0, 0.0)
    assert simplified[-1] == (49.0, 49.0)


def test_color_palette_matching():
    """Verifies RGB Euclidean mapping to standard named palette swatches."""
    assert match_nearest_color((0, 0, 0)) == "black"
    assert match_nearest_color((255, 255, 255)) == "white"
    assert match_nearest_color((250, 20, 25)) == "red"
    assert match_nearest_color((250, 195, 10)) == "yellow"
    assert match_nearest_color((50, 70, 210)) == "blue"
    assert match_nearest_color((180, 120, 80)) == "brown"


def test_extract_vector_strokes_synthetic(tmp_path: Path):
    """Verifies extracting vector strokes from a synthetic test bitmap."""
    # Create simple 100x100 test image with a black circle on white background
    test_img = Image.new("RGB", (100, 100), (255, 255, 255))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(test_img)
    draw.ellipse([20, 20, 80, 80], outline=(0, 0, 0), width=3)
    img_file = tmp_path / "test_circle.png"
    test_img.save(img_file)

    actions = extract_vector_strokes(
        image_path=img_file,
        canvas_bounds=(200, 200, 800, 600),
        max_strokes=10,
        min_stroke_len=5,
    )

    assert len(actions) > 0, "Expected at least one synthesized stroke action"
    # Verify action types
    assert any(a["action"] == "click" for a in actions), "Expected color swatch click action"
    assert any(a["action"] == "stroke" for a in actions), "Expected stroke action"

    # Verify coordinate bounds
    for a in actions:
        if a["action"] == "stroke":
            for x, y in a["points"]:
                assert 200 <= x <= 800, f"X coordinate {x} out of canvas bounds"
                assert 200 <= y <= 600, f"Y coordinate {y} out of canvas bounds"

    # Verify preview generation
    preview_path = tmp_path / "preview.png"
    out_p = generate_vectorizer_preview(actions, preview_path, canvas_size=(1000, 800))
    assert out_p.exists() and out_p.stat().st_size > 0


def test_extract_vector_strokes_reference_image(tmp_path: Path):
    """Verifies vectorizer execution on the actual paintthis.jpg reference if present."""
    ref_path = Path(r"C:\Users\AdLoa\Downloads\paintthis.jpg")
    if not ref_path.exists():
        pytest.skip("paintthis.jpg reference not found in Downloads")

    actions = extract_vector_strokes(
        image_path=ref_path,
        canvas_bounds=(100, 180, 1250, 670),
        max_strokes=40,
        min_stroke_len=10,
    )

    assert len(actions) > 0
    stroke_actions = [a for a in actions if a["action"] == "stroke"]
    click_actions = [a for a in actions if a["action"] == "click"]

    assert len(stroke_actions) > 5, "Expected multiple anatomical strokes"
    assert len(click_actions) >= 2, "Expected multiple color palette selections"

    # Preview render
    preview_file = tmp_path / "reference_preview.png"
    rendered = generate_vectorizer_preview(actions, preview_file, canvas_size=(1366, 768))
    assert rendered.exists()


def test_batch_duration_estimation_and_scaling():
    """Verifies that oversized action batches are automatically scaled to prevent MCP client timeouts."""
    from extra.mcp.server import estimate_and_optimize_batch_duration

    # Create 150 strokes with 0.8s duration each (120s+ total)
    oversized = [
        {"action": "stroke", "points": [[100, 100], [200, 200], [300, 300]], "duration": 0.8}
        for _ in range(150)
    ]

    optimized, est_sec, scaled = estimate_and_optimize_batch_duration(oversized, max_budget_sec=45.0)

    assert scaled is True, "Expected batch to be flagged as scaled"
    assert est_sec <= 45.0, f"Estimated duration {est_sec}s should be <= 45.0s budget"
    # Verify individual stroke duration was scaled down
    for a in optimized:
        assert a["duration"] < 0.8, "Stroke duration should have been scaled down"
        assert a["duration"] >= 0.06, "Stroke duration should not drop below 0.06s"


def test_batch_hard_deadline_timeout_guard(monkeypatch):
    """Verifies that execute_batch_actions safely pauses when hard deadline is reached."""
    import time
    from unittest.mock import MagicMock
    import extra.core.platform.windows.input_engine as ie

    monkeypatch.setattr(ie, "mouse_click", MagicMock())
    monkeypatch.setattr(ie, "mouse_move", MagicMock())
    monkeypatch.setattr(ie, "mouse_down", MagicMock())
    monkeypatch.setattr(ie, "mouse_up", MagicMock())
    monkeypatch.setattr(ie, "send_mouse_move_event", MagicMock())
    monkeypatch.setattr(ie, "_notify_indicator", MagicMock())

    # Create batch of 10 sleep actions of 50ms each with a tiny 0.08s hard deadline
    actions = [{"action": "sleep", "ms": 50} for _ in range(10)]
    res = ie.execute_batch_actions(actions, auto_settle=False, max_duration_sec=0.08)

    assert res["success"] is True
    assert res.get("partial_execution") is True, "Expected partial_execution flag"
    assert res["executed_count"] < 10, "Should have executed only a subset of actions"
    assert res["remaining_count"] > 0, "Should report remaining action count"
    assert "safety" in res.get("message", "").lower() or "paused" in res.get("message", "").lower()

