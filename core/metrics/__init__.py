"""
Project Extra Metrics and Privacy-Preserving Telemetry Subsystem.
"""

from extra.core.metrics.config import (
    get_config_path,
    get_metrics_dir,
    get_ledger_path,
    load_config,
    save_config,
    is_telemetry_enabled,
    set_telemetry_enabled,
    get_anonymous_machine_id,
    is_first_run_pending,
    mark_first_run_complete,
    is_first_run_telemetry_allowed,
)
from extra.core.metrics.ledger import ImpactLedger, BASELINES
from extra.core.metrics.sanitizer import ZeroPiiSanitizer
from extra.core.metrics.telemetry import TelemetryClient, emit_first_run_activation
from extra.core.metrics.dashboard import generate_html_dashboard, open_dashboard_in_browser

__all__ = [
    "get_config_path",
    "get_metrics_dir",
    "get_ledger_path",
    "load_config",
    "save_config",
    "is_telemetry_enabled",
    "set_telemetry_enabled",
    "get_anonymous_machine_id",
    "is_first_run_pending",
    "mark_first_run_complete",
    "is_first_run_telemetry_allowed",
    "ImpactLedger",
    "BASELINES",
    "ZeroPiiSanitizer",
    "TelemetryClient",
    "emit_first_run_activation",
    "generate_html_dashboard",
    "open_dashboard_in_browser"
]
