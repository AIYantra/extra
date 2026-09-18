"""
Project Extra — Hardware Input Engine (PAL Facade)
Re-exports input injection functions and classes from the active platform backend.
"""

from __future__ import annotations

from extra.core.platform import (
    atomic_clipboard_paste,
    execute_batch_actions,
    instant_type,
    mouse_click,
    mouse_double_click,
    mouse_down,
    mouse_drag,
    mouse_move,
    mouse_scroll,
    mouse_up,
    send_hotkey,
)

__all__ = [
    "atomic_clipboard_paste",
    "execute_batch_actions",
    "instant_type",
    "mouse_click",
    "mouse_double_click",
    "mouse_down",
    "mouse_drag",
    "mouse_move",
    "mouse_scroll",
    "mouse_up",
    "send_hotkey",
]
