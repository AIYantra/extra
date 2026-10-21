"""
Project Extra — Cloud Desktop Relay Client (Compatibility Shim)
DEPRECATED: relay has moved to extra.relay.client.
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

__all__ = [
    "DEFAULT_ALLOWED_RELAY_TOOLS",
    "DEFAULT_RELAY_URL",
    "execute_local_tool",
    "get_allowed_relay_tools",
    "get_default_device_name",
    "register_tool_executor",
    "run_relay_loop",
    "start_relay",
]
