"""Telemetry stub for CUA compatibility."""


def is_telemetry_enabled() -> bool:
    """Check if telemetry is enabled."""
    return False


def record_event(event_name: str, **kwargs) -> None:
    """Record telemetry event (no-op)."""
    pass
