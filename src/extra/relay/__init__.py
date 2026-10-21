"""
Project Extra — Remote Networking & Relay Subsystem
Outbound WebSocket relay client and Cloudflare Quick Tunnel primitives.
"""

from extra.relay.client import (
    DEFAULT_ALLOWED_RELAY_TOOLS,
    DEFAULT_RELAY_URL,
    execute_local_tool,
    get_allowed_relay_tools,
    get_default_device_name,
    register_tool_executor,
    run_relay_loop,
    start_relay,
)
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
    "DEFAULT_ALLOWED_RELAY_TOOLS",
    "DEFAULT_RELAY_URL",
    "execute_local_tool",
    "get_allowed_relay_tools",
    "get_default_device_name",
    "register_tool_executor",
    "run_relay_loop",
    "start_relay",
    "ensure_cloudflared_installed",
    "find_cloudflared_binary",
    "format_chatgpt_banner",
    "generate_secure_token",
    "get_extra_bin_dir",
    "start_tunnel",
    "stop_tunnel",
]
