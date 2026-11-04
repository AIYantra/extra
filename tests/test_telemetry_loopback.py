import pytest
from starlette.testclient import TestClient
from extra.mcp.server import create_unified_mcp_app

@pytest.fixture(scope="module")
def client():
    app = create_unified_mcp_app()
    return TestClient(app)

def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "healthy"
    assert "version" in data
    assert "platform" in data

def test_telemetry_endpoint(client):
    res = client.get("/telemetry")
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "online"
    assert "target_window" in data
    assert "latency_ms" in data
    assert "memory_mb" in data
    assert "tokens_saved" in data
    assert "cost_saved_usd" in data
    assert "speed_mode" in data
    assert "is_paused" in data

def test_speed_mode_endpoint(client):
    res = client.post("/api/speed-mode", json={"mode": "turbo"})
    assert res.status_code == 200
    assert res.json().get("speed_mode") == "turbo"

    res = client.post("/api/speed-mode", json={"mode": "balanced"})
    assert res.status_code == 200
    assert res.json().get("speed_mode") == "balanced"

def test_panic_stop_and_resume_endpoints(client):
    from extra.mcp.server import _stall_breaker
    from extra.core.stall_breaker import EmergencyAbortError
    import pytest

    res = client.post("/api/panic-stop")
    assert res.status_code == 200
    assert res.json().get("is_paused") is True
    assert _stall_breaker.is_paused is True

    # Verify safety supervisor aborts when engine is paused
    with pytest.raises(EmergencyAbortError):
        _stall_breaker.check_safety_abort()

    # Verify telemetry reports is_paused == True
    t_res = client.get("/telemetry")
    assert t_res.json().get("is_paused") is True

    res = client.post("/api/resume")
    assert res.status_code == 200
    assert res.json().get("is_paused") is False
    assert _stall_breaker.is_paused is False

    # Verify telemetry reports is_paused == False
    t_res = client.get("/telemetry")
    assert t_res.json().get("is_paused") is False

def test_cors_preflight(client):
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    }
    res = client.options("/telemetry", headers=headers)
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") in ("*", "http://localhost:5173")
