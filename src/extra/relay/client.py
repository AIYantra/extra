"""
Project Extra — Cloud Desktop Relay Client
Maintains a secure, outbound WebSocket link to the Extra Cloud Hub (AWS + Cloudflare).
Executes desktop automation commands dispatched by remote AI agents (e.g. ChatGPT)
directly on the physical glass without exposing any local inbound ports.
"""

import asyncio
import json
import logging
import os
import platform
import socket
import sys
import time
import urllib.parse
from typing import Dict, Any, Optional, Set

logger = logging.getLogger("extra.relay")

DEFAULT_RELAY_URL = "wss://rf4v1b6vul.execute-api.ap-south-1.amazonaws.com/prod"

DEFAULT_ALLOWED_RELAY_TOOLS = frozenset({
    "extra_screenshot",
    "extra_click",
    "extra_click_element",
    "extra_mouse_move",
    "extra_type",
    "extra_hotkey",
    "extra_launch",
    "extra_focus_window",
    "extra_snap_layout",
    "extra_scroll",
    "extra_drag",
    "extra_stroke",
    "extra_inspect_ui",
    "extra_batch_actions",
    "extra_subtask_run",
    "extra_soul_wait",
    "extra_indicate_status",
    "extra_task_start",
    "extra_task_complete",
    "extra_fs_batch",
})


def get_allowed_relay_tools() -> frozenset:
    """Returns the set of tools permitted for remote relay execution."""
    custom_env = os.environ.get("EXTRA_RELAY_ALLOWED_TOOLS")
    if custom_env:
        tools = {t.strip() for t in custom_env.split(",") if t.strip()}
    else:
        tools = set(DEFAULT_ALLOWED_RELAY_TOOLS)

    # Bridge execution (Plane 2 code execution) is strictly disabled unless explicitly enabled
    if os.environ.get("EXTRA_RELAY_ENABLE_BRIDGE") == "1":
        tools.add("extra_execute_bridge")
    else:
        tools.discard("extra_execute_bridge")

    return frozenset(tools)


def get_default_device_name() -> str:
    """Returns a readable name for this workstation."""
    hostname = socket.gethostname()
    os_name = platform.system()
    return f"{hostname} ({os_name})"


_CUSTOM_TOOL_EXECUTOR = None


def register_tool_executor(executor_fn) -> None:
    """Registers an external tool executor callback (e.g. from MCP server or test harness)."""
    global _CUSTOM_TOOL_EXECUTOR
    _CUSTOM_TOOL_EXECUTOR = executor_fn


def generate_relay_safe_b64(file_path: str, max_b64_len: int = 18000) -> Optional[str]:
    """Generates an optimized, low-latency base64 thumbnail (< 18KB) compliant with AWS API Gateway 32KB frame limits."""
    if not file_path or not os.path.exists(file_path):
        return None
    try:
        from PIL import Image
        import io
        import base64
        im = Image.open(file_path)
        w, h = im.size
        for target_w, quality in [(640, 45), (512, 35), (400, 30), (320, 25)]:
            target_h = max(1, int(h * (target_w / w)))
            thumb = im.resize((target_w, target_h), Image.Resampling.BILINEAR)
            buf = io.BytesIO()
            thumb.save(buf, format="JPEG", quality=quality, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            if len(b64) <= max_b64_len:
                return b64
        return b64
    except Exception:
        return None


async def execute_local_tool(tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes an Extra tool locally on the glass and returns the outcome.
    Enforces a strict tool allowlist to prevent unauthorized remote code execution.
    """
    if not tool_name or not isinstance(tool_name, str):
        return {"success": False, "error": "Invalid or missing tool name."}

    # Block dunder methods, private functions, and reflection attempts
    if tool_name.startswith("_"):
        return {"success": False, "error": f"Tool '{tool_name}' is not permitted."}

    # Enforce strict remote execution allowlist
    allowed_tools = get_allowed_relay_tools()
    if tool_name not in allowed_tools:
        logger.warning("Remote tool execution rejected: '%s' is not in ALLOWED_RELAY_TOOLS", tool_name)
        return {
            "success": False,
            "error": f"Security Policy Violation: Tool '{tool_name}' is restricted from remote cloud execution."
        }

    try:
        safe_args = dict(arguments) if isinstance(arguments, dict) else {}

        # 1. Pluggable tool executor callback (decoupled from mcp.server)
        if _CUSTOM_TOOL_EXECUTOR is not None:
            if asyncio.iscoroutinefunction(_CUSTOM_TOOL_EXECUTOR):
                res = await _CUSTOM_TOOL_EXECUTOR(tool_name, safe_args)
            else:
                res = _CUSTOM_TOOL_EXECUTOR(tool_name, safe_args)
            outcome = {"success": True, "result": res}
        else:
            # 2. Lazy fallback to extra.mcp.server
            from extra.mcp import server as mcp_server

            # Map tool names to native implementations
            tool_func = getattr(mcp_server, tool_name, None)
            if not tool_func or not callable(tool_func):
                return {"success": False, "error": f"Tool '{tool_name}' not found on local Extra engine."}

            # Handle async vs sync tool calls
            if asyncio.iscoroutinefunction(tool_func):
                res = await tool_func(**safe_args)
            else:
                res = tool_func(**safe_args)

            outcome = {"success": True, "result": res}

        # Cloud Relay Invariant: Remote cloud agents (e.g. ChatGPT on chatgpt.com) run on external
        # servers and have zero access to the local workstation filesystem (C:\Users\...).
        # Attach a compressed relay-safe base64 thumbnail (< 18KB) so the remote AI can see the visual desktop
        # without exceeding AWS API Gateway's 32KB WebSocket frame limit (Error 1009).
        if tool_name == "extra_screenshot" and isinstance(outcome.get("result"), dict):
            inner_res = outcome["result"]
            if not inner_res.get("screenshot_base64"):
                fp = inner_res.get("file_path")
                if fp:
                    safe_b64 = generate_relay_safe_b64(fp, max_b64_len=18000)
                    if safe_b64:
                        inner_res["screenshot_base64"] = safe_b64
                        inner_res["is_compressed_relay_thumbnail"] = True

        return outcome
    except Exception as e:
        logger.error("Error executing local tool %s: %s", tool_name, e)
        return {"success": False, "error": str(e)}


async def run_relay_loop(
    hub_url: str = DEFAULT_RELAY_URL,
    token: str = "anonymous",
    device_id: Optional[str] = None,
    device_name: Optional[str] = None,
    reconnect_delay: float = 3.0,
) -> None:
    """
    Main background event loop maintaining the outbound WebSocket relay.
    """
    import websockets

    if not device_id:
        import uuid
        device_id = "dev_" + uuid.uuid4().hex[:10]

    if not device_name:
        device_name = get_default_device_name()

    params = {
        "token": token,
        "device_id": device_id,
        "device_name": device_name,
    }
    encoded_url = f"{hub_url}?{urllib.parse.urlencode(params)}"

    while True:
        try:
            logger.info("Connecting to Extra Cloud Hub: %s...", hub_url)
            print(f"[*] Connecting to Extra Cloud Hub ({device_name})...", flush=True)

            async with websockets.connect(encoded_url) as ws:
                banner = f"""
==================================================================
  [EXTRA] Desktop Relay Active - Connected to Cloud Hub
==================================================================
  [*] Hub:            {hub_url}
  [*] Device:         {device_name}
  [*] Status:         Online & Listening for ChatGPT actions
------------------------------------------------------------------
  >> ChatGPT can now automate this desktop in real time.
  Press Ctrl+C to disconnect.
==================================================================
"""
                print(banner, flush=True)
                logger.info("Connected to relay hub successfully as %s", device_name)

                # Keep heartbeat & message listener
                while True:
                    try:
                        # Wait for incoming command with timeout to send ping
                        message_raw = await asyncio.wait_for(ws.recv(), timeout=25.0)
                        data = json.loads(message_raw)

                        action = data.get("action")
                        if action == "execute":
                            action_id = data.get("action_id")
                            tool_name = data.get("tool")
                            tool_args = data.get("arguments", {})

                            logger.info("Executing remote tool: %s (%s)", tool_name, action_id)
                            print(f"[ACTION] Received: {tool_name} -> executing on glass...", flush=True)

                            # Run tool locally
                            outcome = await execute_local_tool(tool_name, tool_args)

                            # Send result back across relay
                            resp = {
                                "action": "result",
                                "action_id": action_id,
                                "result": outcome,
                                "timestamp": int(time.time() * 1000)
                            }
                            raw_payload = json.dumps(resp)
                            # Hard Guard: AWS API Gateway drops connections if frame > 32,768 bytes (Error 1009)
                            if len(raw_payload.encode("utf-8")) > 30000:
                                inner = resp.get("result", {}).get("result", {})
                                if isinstance(inner, dict) and "screenshot_base64" in inner:
                                    inner["screenshot_base64"] = "[Image omitted: exceeded 30KB frame limit. Use extra_inspect_ui]"
                                raw_payload = json.dumps(resp)

                            await ws.send(raw_payload)
                            logger.info("Completed action %s: success=%s", action_id, outcome.get("success"))
                            print(f"[ACTION] Completed: {tool_name} (success={outcome.get('success')})", flush=True)

                    except asyncio.TimeoutError:
                        # Send ping heartbeat
                        try:
                            pong_waiter = await ws.ping()
                            await asyncio.wait_for(pong_waiter, timeout=10.0)
                        except Exception:
                            logger.warning("Heartbeat ping timed out, reconnecting...")
                            break

        except (websockets.ConnectionClosed, ConnectionResetError, OSError) as e:
            logger.warning("Relay connection lost: %s. Reconnecting in %ss...", e, reconnect_delay)
            print(f"[!] Connection dropped. Reconnecting in {reconnect_delay}s...", flush=True)
            await asyncio.sleep(reconnect_delay)
        except asyncio.CancelledError:
            logger.info("Relay loop cancelled, shutting down.")
            break
        except Exception as e:
            logger.error("Unexpected error in relay loop: %s", e)
            print(f"[!] Relay error: {e}. Reconnecting in {reconnect_delay}s...", flush=True)
            await asyncio.sleep(reconnect_delay)


def start_relay(
    hub_url: str = DEFAULT_RELAY_URL,
    token: str = "anonymous",
    device_id: Optional[str] = None,
    device_name: Optional[str] = None,
) -> None:
    """Synchronous entry point to start the relay event loop."""
    try:
        asyncio.run(run_relay_loop(
            hub_url=hub_url,
            token=token,
            device_id=device_id,
            device_name=device_name,
        ))
    except KeyboardInterrupt:
        print("\n[*] Disconnected from Extra Cloud Hub. Goodbye!", flush=True)
