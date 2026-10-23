"""
Project Extra — Screen UI Distiller Engine
Translates native desktop accessibility trees and edge-detected controls into an
ultra-dense, token-optimized textual representation (Markdown / Compact / JSON).
Saves 90%+ prompt tokens and eliminates latency overhead compared to sending raw screenshots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from extra.core.focus import find_window_by_title, get_foreground_window, get_window_info
from extra.core.platform.base import AbstractAccessibilityPlane, UIElement
from extra.core.platform import get_accessibility_plane

logger = logging.getLogger("Extra-UIDistiller")

# Standard control categories across Win32 UIA, macOS AX, and Linux AT-SPI2
INPUT_CONTROL_TYPES: Set[str] = {
    "Edit",
    "ComboBox",
    "Slider",
    "Spinner",
    "Document",
    "ScrollBar",
    "AXTextField",
    "AXTextArea",
    "AXComboBox",
    "AXSlider",
}

ACTION_CONTROL_TYPES: Set[str] = {
    "Button",
    "Hyperlink",
    "CheckBox",
    "RadioButton",
    "MenuItem",
    "SplitButton",
    "TabItem",
    "ListItem",
    "TreeItem",
    "AXButton",
    "AXLink",
    "AXCheckBox",
    "AXRadioButton",
    "AXMenuItem",
    "AXTab",
    "AXRow",
}

INFO_CONTROL_TYPES: Set[str] = {
    "Text",
    "StatusBar",
    "Header",
    "HeaderItem",
    "ProgressBar",
    "ToolTip",
    "AXStaticText",
    "AXHeading",
    "AXProgressIndicator",
}

CONTAINER_CONTROL_TYPES: Set[str] = {
    "Pane",
    "Group",
    "Window",
    "TitleBar",
    "ToolBar",
    "Table",
    "DataGrid",
    "DataItem",
    "Custom",
    "Separator",
    "SemanticZoom",
    "AppBar",
    "AXGroup",
    "AXWindow",
    "AXToolbar",
    "AXTable",
}


@dataclass
class DistillationResult:
    """
    Structured outcome of a screen/window distillation.
    Provides compact representations alongside performance and token metrics.
    """
    window_title: str
    process_name: str
    hwnd: int
    is_foreground: bool
    content: str
    format: str
    element_count: int
    interactive_count: int
    approx_tokens: int
    token_savings_pct: float
    elements: List[UIElement] = field(default_factory=list)
    work_surface: Optional[Dict[str, Any]] = None
    source: str = "uia_tier0"
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serializes distillation result for MCP response dispatch."""
        return {
            "success": True,
            "source": self.source,
            "window_title": self.window_title,
            "process_name": self.process_name,
            "hwnd": self.hwnd,
            "is_foreground": self.is_foreground,
            "work_surface": self.work_surface,
            "element_count": self.element_count,
            "interactive_count": self.interactive_count,
            "approx_tokens": self.approx_tokens,
            "token_savings_pct": self.token_savings_pct,
            "duration_ms": round(self.duration_ms, 2),
            "content": self.content,
            "elements": [el.to_dict() for el in self.elements],
        }



class UIDistiller:
    """
    Extracts, filters, and formats accessibility trees into token-minimized
    semantic UI representations for host AI agents.
    """

    def __init__(self, plane: Optional[AbstractAccessibilityPlane] = None) -> None:
        self._plane = plane

    @property
    def plane(self) -> AbstractAccessibilityPlane:
        if self._plane is None:
            self._plane = get_accessibility_plane()
        return self._plane

    def distill_window(
        self,
        hwnd: Optional[int] = None,
        window_title: Optional[str] = None,
        format: str = "markdown",
        include_coordinates: bool = True,
        max_elements: int = 50,
        interactive_only: bool = False,
        group_by_type: bool = True,
        force_vision: bool = False,
    ) -> DistillationResult:
        """
        Distills a target window into a concise representation.
        
        Args:
            hwnd: Direct native window handle.
            window_title: Window title query substring (if hwnd is not provided).
            format: Output format ('markdown', 'compact', 'json'). Default: 'markdown'.
            include_coordinates: If True, outputs physical [x, y] coordinates for each control.
            max_elements: Maximum elements to present in output.
            interactive_only: If True, discards passive text/labels and retains only actionable controls.
            group_by_type: If True in markdown format, groups into Inputs, Actions, and Info sections.
            force_vision: If True, forces edge computer vision parsing even if UIA accessibility is present.
        """
        t0 = time.perf_counter()

        # 1. Resolve Target Window
        target_hwnd = hwnd
        win_info = None
        if target_hwnd is None and window_title:
            win_info = find_window_by_title(window_title)
            if win_info:
                target_hwnd = win_info.hwnd

        fg_win = get_foreground_window()
        if target_hwnd is None:
            win_info = fg_win
            target_hwnd = fg_win.hwnd if fg_win else 0
        elif win_info is None and target_hwnd:
            win_info = get_window_info(target_hwnd)

        title = win_info.title if win_info else (window_title or "Unknown Window")
        proc_name = win_info.process_name if win_info else "unknown"
        is_fg = bool(fg_win and fg_win.hwnd == target_hwnd)

        if not target_hwnd:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            empty_msg = f"No active window found matching query '{window_title}'."
            return DistillationResult(
                window_title=title,
                process_name=proc_name,
                hwnd=0,
                is_foreground=False,
                content=empty_msg,
                format=format,
                element_count=0,
                interactive_count=0,
                approx_tokens=len(empty_msg.split()),
                token_savings_pct=99.0,
                duration_ms=duration_ms,
            )

        # 2. Extract Raw Elements via Semantic Accessibility Plane
        # Pull slightly more elements to allow intelligent filtering & deduplication across tabs/documents
        raw_elements = self.plane.inspect_window(
            hwnd=target_hwnd,
            interactive_only=False,
            max_elements=max(max_elements * 4, 150),
        )

        # 3. Filter, Prune, and Classify (with strict window viewport boundary enforcement)
        win_rect = win_info.rect if (win_info and win_info.rect and win_info.width > 10 and win_info.height > 10) else None
        filtered_elements = self._prune_and_filter(raw_elements, interactive_only=interactive_only, window_rect=win_rect)

        # Determine default source
        plat_src = "uia_tier0"
        if sys.platform == "darwin":
            plat_src = "ax_tier0"
        elif sys.platform.startswith("linux"):
            plat_src = "atspi_tier0"

        # Content elements check: exclude pure window frame buttons (e.g. Minimize/Maximize/Close)
        content_elements = [
            el for el in filtered_elements
            if getattr(el, "class_name", "") != "WinCaptionButton"
            and (el.name or "").lower() not in {"minimize", "maximize", "close", "restore"}
        ]

        # Edge Vision Fallback: If accessibility returned an opaque canvas (<= 2 content controls) or force_vision is active
        if (len(content_elements) <= 2 or force_vision) and target_hwnd:
            try:
                from extra.core.soul.vision_parser import EdgeVisionParser
                if not hasattr(self, "_vision_parser") or self._vision_parser is None:
                    self._vision_parser = EdgeVisionParser()
                vision_elements = self._vision_parser.parse_window(target_hwnd, max_elements=max_elements)
                if vision_elements:
                    filtered_elements = vision_elements
                    plat_src = "vision_tier1"
            except Exception as ex:
                logger.debug("Edge Vision fallback skipped: %s", ex)

        # 4. Discover High-Contrast Work Surface / Custom Canvas Viewport (< 5ms)
        work_surface_dict = None
        if target_hwnd:
            try:
                from extra.core.soul.vision_parser import EdgeVisionParser
                if not hasattr(self, "_vision_parser") or self._vision_parser is None:
                    self._vision_parser = EdgeVisionParser()
                ws = self._vision_parser.detect_work_surface_in_window(target_hwnd)
                if ws:
                    work_surface_dict = ws.to_dict()

                    # Universal Hybrid Canvas Vision:
                    # Detect opaque, custom-rendered surfaces (e.g. Qt/WebGL/DirectX canvas viewports,
                    # chat lists, artboards) where accessibility provides zero/minimal child elements.
                    ws_left, ws_top, ws_right, ws_bottom = ws.left, ws.top, ws.right, ws.bottom
                    elements_inside_ws = [
                        el for el in filtered_elements
                        if ws_left <= el.center[0] <= ws_right and ws_top <= el.center[1] <= ws_bottom
                    ]

                    # If the work surface spans a major area (>= 160x160 px) but has <= 2 accessibility controls inside it:
                    if ws.width >= 160 and ws.height >= 160 and len(elements_inside_ws) <= 2:
                        try:
                            canvas_crop = (ws_left, ws_top, ws_right, ws_bottom)
                            vision_canvas_elements = self._vision_parser.parse_window(
                                target_hwnd, max_elements=max_elements, crop_box=canvas_crop
                            )
                            if vision_canvas_elements:
                                existing_names = {
                                    (el.name or "").lower().strip()
                                    for el in filtered_elements if el.name
                                }
                                for vel in vision_canvas_elements:
                                    vel_name = (vel.name or "").strip().lower()
                                    if not vel_name or vel_name not in existing_names:
                                        filtered_elements.append(vel)
                                        if vel_name:
                                            existing_names.add(vel_name)
                        except Exception as c_ex:
                            logger.debug("Canvas vision parsing skipped: %s", c_ex)
            except Exception as ex:
                logger.debug("Work surface viewport detection skipped: %s", ex)

        # Truncate to max_elements limit
        final_elements = filtered_elements[:max_elements]

        # 4.5 Spatially Sort (Top-to-Bottom, Left-to-Right by rows)
        sorted_elements = self._spatial_sort(final_elements)

        # Count interactives
        interactive_count = sum(
            1 for el in sorted_elements
            if el.control_type in ACTION_CONTROL_TYPES or el.control_type in INPUT_CONTROL_TYPES
        )

        # 5. Format Content
        fmt_clean = format.lower().strip()
        if fmt_clean == "compact":
            content = self._format_compact(
                sorted_elements,
                title=title,
                proc_name=proc_name,
                is_fg=is_fg,
                include_coordinates=include_coordinates,
                work_surface=work_surface_dict,
            )
        elif fmt_clean == "json":
            content = self._format_json(
                sorted_elements,
                title=title,
                proc_name=proc_name,
                is_fg=is_fg,
                include_coordinates=include_coordinates,
                work_surface=work_surface_dict,
            )
        else:
            # Default: Markdown
            content = self._format_markdown(
                sorted_elements,
                title=title,
                proc_name=proc_name,
                is_fg=is_fg,
                include_coordinates=include_coordinates,
                group_by_type=group_by_type,
                work_surface=work_surface_dict,
            )

        # 6. Metrics & Token Economics
        duration_ms = (time.perf_counter() - t0) * 1000.0
        approx_tokens = max(1, int(len(content.split()) * 1.35))
        # Standard screenshot on 1080p/4K is ~1600 tokens
        savings_pct = max(0.0, round((1.0 - (approx_tokens / 1600.0)) * 100.0, 1))

        return DistillationResult(
            window_title=title,
            process_name=proc_name,
            hwnd=target_hwnd,
            is_foreground=is_fg,
            content=content,
            format=fmt_clean,
            element_count=len(sorted_elements),
            interactive_count=interactive_count,
            approx_tokens=approx_tokens,
            token_savings_pct=savings_pct,
            elements=sorted_elements,
            work_surface=work_surface_dict,
            source=plat_src,
            duration_ms=duration_ms,
        )


    def _prune_and_filter(
        self,
        elements: List[UIElement],
        interactive_only: bool = False,
        window_rect: Optional[Tuple[int, int, int, int]] = None,
    ) -> List[UIElement]:
        """Prunes noisy container nodes, deduplicates overlapping elements, and drops offscreen items."""
        pruned: List[UIElement] = []
        seen_keys: Set[Tuple[int, int, str]] = set()

        for el in elements:
            # Universal Viewport Boundary Check:
            # Discard any element whose bounding box is strictly outside the target window viewport
            if window_rect:
                w_left, w_top, w_right, w_bottom = window_rect
                b_left, b_top, b_right, b_bottom = el.bounding_box
                if b_bottom <= w_top or b_top >= w_bottom or b_right <= w_left or b_left >= w_right:
                    continue

            # Fallback: Reject extreme negative-Y/X coordinates from virtualized Qt/Chromium containers
            if el.bounding_box[1] < -8000 or el.bounding_box[0] < -8000:
                continue

            c_type = el.control_type or "Unknown"
            name = (el.name or "").strip()
            auto_id = (el.automation_id or "").strip()

            # Ignore offscreen or degenerate bounds
            if el.is_offscreen or el.width <= 2 or el.height <= 2:
                continue

            # Classify role
            is_input = c_type in INPUT_CONTROL_TYPES
            is_action = c_type in ACTION_CONTROL_TYPES
            is_info = c_type in INFO_CONTROL_TYPES
            is_container = c_type in CONTAINER_CONTROL_TYPES
            has_stream = " | Buffer:" in name or getattr(el, "source", "") in ("text_pattern", "ocr")

            if interactive_only and not (is_input or is_action or has_stream):
                continue

            # Discard unnamed, non-interactive containers with no ID
            if is_container and not name and not auto_id:
                continue

            # For passive text, ignore purely decorative or empty strings
            if is_info and not name:
                continue

            # Deduplication key based on center point and name
            cx, cy = el.center
            # Bucket center within 4px to catch duplicate bounding boxes from wrapper frames
            grid_key = (cx // 4, cy // 4, name)
            if grid_key in seen_keys:
                continue
            seen_keys.add(grid_key)

            pruned.append(el)

        return pruned

    def _spatial_sort(self, elements: List[UIElement], row_tolerance_px: int = 16) -> List[UIElement]:
        """
        Sorts UI elements in natural reading order (Top-to-Bottom, Left-to-Right).
        Groups controls into vertical row bands so inline buttons sort cleanly by X.
        """
        if not elements:
            return []

        # Sort primarily by row-banded Y, then X
        def sort_key(el: UIElement) -> Tuple[int, int]:
            cx, cy = el.center
            row_bucket = cy // row_tolerance_px
            return (row_bucket, cx)

        return sorted(elements, key=sort_key)

    def _format_markdown(
        self,
        elements: List[UIElement],
        title: str,
        proc_name: str,
        is_fg: bool,
        include_coordinates: bool = True,
        group_by_type: bool = True,
        work_surface: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Serializes elements into structured, human- and LLM-friendly Markdown."""
        fg_status = "Foreground (Active)" if is_fg else "Background"
        lines: List[str] = [
            f"### Window: [{title}] | Process: {proc_name} | State: {fg_status}",
        ]

        if work_surface:
            lines.append(
                f"#### 🎨 Canvas / Work Surface Viewport:\n"
                f"- Bounds: ({work_surface['left']}, {work_surface['top']}) to ({work_surface['right']}, {work_surface['bottom']}) | "
                f"Size: {work_surface['width']} × {work_surface['height']} px | Center: ({work_surface['center'][0]}, {work_surface['center'][1]})"
            )

        if not elements:
            lines.append("*(No accessible UI controls detected in active window)*")
            return "\n".join(lines)


        if not group_by_type:
            # Linear spatial list
            lines.append("#### Controls (Spatial Reading Order):")
            for el in elements:
                lines.append(self._format_element_line(el, include_coordinates=include_coordinates))
            return "\n".join(lines)

        # Categorized Grouping
        inputs: List[UIElement] = []
        actions: List[UIElement] = []
        info: List[UIElement] = []
        others: List[UIElement] = []

        for el in elements:
            c = el.control_type
            if c in INPUT_CONTROL_TYPES:
                inputs.append(el)
            elif c in ACTION_CONTROL_TYPES:
                actions.append(el)
            elif c in INFO_CONTROL_TYPES:
                info.append(el)
            else:
                others.append(el)

        if info:
            lines.append("#### ℹ️ Information & Display:")
            for el in info:
                lines.append(self._format_element_line(el, include_coordinates=include_coordinates))

        if inputs:
            lines.append("#### 📝 Inputs & Fields:")
            for el in inputs:
                lines.append(self._format_element_line(el, include_coordinates=include_coordinates))

        if actions:
            lines.append("#### ⚡ Actions & Buttons:")
            # Group consecutive buttons on similar Y into single horizontal lines for token density
            lines.extend(self._format_compact_action_rows(actions, include_coordinates=include_coordinates))

        if others:
            lines.append("#### 📦 Other Elements:")
            for el in others:
                lines.append(self._format_element_line(el, include_coordinates=include_coordinates))

        return "\n".join(lines)

    def _get_provenance_tag(self, el: UIElement) -> str:
        """Determines the semantic provenance tag for the given element."""
        src = str(getattr(el, "source", "uia") or "uia").lower()
        if "ocr" in src:
            return "[OCR]"
        elif "txt" in src or "text_pattern" in src or " | Buffer:" in el.name:
            return "[TXT]"
        elif "soul" in src:
            return "[SOUL]"
        return "[UIA]"

    def _format_element_line(self, el: UIElement, include_coordinates: bool = True) -> str:
        """Formats a single UI element bullet with provenance."""
        name = f"'{el.name}'" if el.name else "(unnamed)"
        coord_str = f" [Center: {el.center[0]}, {el.center[1]}]" if include_coordinates else ""
        auto_id_str = f" (id: {el.automation_id})" if el.automation_id and el.automation_id != el.name else ""
        enabled_str = " (disabled)" if not el.is_enabled else ""
        tag = self._get_provenance_tag(el)

        return f"- {tag} [ID: {el.element_id}] {el.control_type}: {name}{auto_id_str}{enabled_str}{coord_str}"

    def _format_compact_action_rows(
        self, actions: List[UIElement], include_coordinates: bool = True, row_tolerance: int = 14
    ) -> List[str]:
        """Groups nearby horizontal action buttons into single markdown lines to save tokens."""
        if not actions:
            return []

        rows: List[List[UIElement]] = []
        curr_row: List[UIElement] = [actions[0]]

        for el in actions[1:]:
            last_el = curr_row[-1]
            if abs(el.center[1] - last_el.center[1]) <= row_tolerance:
                curr_row.append(el)
            else:
                rows.append(curr_row)
                curr_row = [el]
        rows.append(curr_row)

        output_lines: List[str] = []
        for row in rows:
            items: List[str] = []
            for el in row:
                name = f"'{el.name}'" if el.name else "(unnamed)"
                coord_str = f" ({el.center[0]},{el.center[1]})" if include_coordinates else ""
                items.append(f"[ID: {el.element_id}] {el.control_type} {name}{coord_str}")
            output_lines.append("- " + " | ".join(items))

        return output_lines

    def _format_compact(
        self,
        elements: List[UIElement],
        title: str,
        proc_name: str,
        is_fg: bool,
        include_coordinates: bool = True,
        work_surface: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Formats into an ultra-dense, token-minimal representation."""
        fg_tag = "Focused" if is_fg else "Background"
        parts = [f"[WIN: {title} | Proc: {proc_name} | {fg_tag}]"]

        if work_surface:
            parts.append(
                f"CANVAS: [Box: ({work_surface['left']},{work_surface['top']}) to ({work_surface['right']},{work_surface['bottom']}) | "
                f"Size: {work_surface['width']}x{work_surface['height']} | Center: ({work_surface['center'][0]},{work_surface['center'][1]})]"
            )

        # Streams & Buffers (Terminals, Console stdout, Rich Documents, OCR Text)
        stream_items = []
        for el in elements:
            src_tag = self._get_provenance_tag(el)
            if src_tag in ("[TXT]", "[OCR]") or " | Buffer:" in el.name:
                coords = f"({el.center[0]},{el.center[1]})" if include_coordinates else ""
                stream_items.append(f"{src_tag} [{el.element_id}] {el.name}{coords}")
        if stream_items:
            parts.append("STREAMS: " + " | ".join(stream_items[:4]))

        info_items = [
            f"{el.name}" for el in elements
            if el.control_type in INFO_CONTROL_TYPES and el.name
        ]
        if info_items:
            parts.append("INFO: " + "; ".join(info_items[:8]))

        input_items = []
        for el in elements:
            if el.control_type in INPUT_CONTROL_TYPES:
                coords = f"({el.center[0]},{el.center[1]})" if include_coordinates else ""
                input_items.append(f"[{el.element_id}] {el.name or el.control_type}{coords}")
        if input_items:
            parts.append("INPUTS: " + " | ".join(input_items))

        action_items = []
        for el in elements:
            if el.control_type in ACTION_CONTROL_TYPES:
                coords = f"({el.center[0]},{el.center[1]})" if include_coordinates else ""
                action_items.append(f"[{el.element_id}] '{el.name or el.control_type}'{coords}")
        if action_items:
            parts.append("ACTIONS: " + " | ".join(action_items))

        return "\n".join(parts)

    def _format_json(
        self,
        elements: List[UIElement],
        title: str,
        proc_name: str,
        is_fg: bool,
        include_coordinates: bool = True,
        work_surface: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Serializes elements into structured JSON string."""
        import json
        payload = {
            "window": {
                "title": title,
                "process": proc_name,
                "is_foreground": is_fg,
            },
            "work_surface": work_surface,
            "controls": [
                {
                    "id": el.element_id,
                    "type": el.control_type,
                    "name": el.name,
                    "provenance": self._get_provenance_tag(el),
                    "source": getattr(el, "source", "uia"),
                    "center": list(el.center) if include_coordinates else None,
                    "enabled": el.is_enabled,
                }

                for el in elements
            ],
        }
        return json.dumps(payload, indent=2)


_default_distiller = UIDistiller()


def distill_screen(
    hwnd: Optional[int] = None,
    window_title: Optional[str] = None,
    format: str = "markdown",
    include_coordinates: bool = True,
    max_elements: int = 50,
    interactive_only: bool = False,
    group_by_type: bool = True,
    force_vision: bool = False,
) -> DistillationResult:
    """Convenience top-level function for screen distillation."""
    return _default_distiller.distill_window(
        hwnd=hwnd,
        window_title=window_title,
        format=format,
        include_coordinates=include_coordinates,
        max_elements=max_elements,
        interactive_only=interactive_only,
        group_by_type=group_by_type,
        force_vision=force_vision,
    )

