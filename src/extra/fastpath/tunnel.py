"""
Project Extra — Automated Tunneling Subsystem (Compatibility Shim)
DEPRECATED: tunnel has moved to extra.relay.tunnel.
"""

from extra.relay.tunnel import (
    ensure_cloudflared_installed,
    find_cloudflared_binary,
    format_chatgpt_banner,
    generate_secure_token,
    get_extra_bin_dir,
    start_tunnel,
    stop_tunnel,
)

__all__ = [
    "ensure_cloudflared_installed",
    "find_cloudflared_binary",
    "format_chatgpt_banner",
    "generate_secure_token",
    "get_extra_bin_dir",
    "start_tunnel",
    "stop_tunnel",
]
