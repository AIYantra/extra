"""
Extra Scout Subsystem — Just-In-Time (JIT) Application Intelligence
Autonomously discovers CLI flags, hotkeys, and scripting APIs before taking GUI actions.
"""

from extra.core.scout.detector import detect_app_profile, AppProfile
from extra.core.scout.scraper import get_app_intelligence
from extra.core.scout.synthesizer import scout_and_generate_skill
from extra.core.scout.cdp_sniffer import NetworkSniffer, CapturedRequest
from extra.core.scout.session_vault import SessionVault, ServiceSession

__all__ = [
    "detect_app_profile",
    "AppProfile",
    "get_app_intelligence",
    "scout_and_generate_skill",
    "NetworkSniffer",
    "CapturedRequest",
    "SessionVault",
    "ServiceSession",
]
