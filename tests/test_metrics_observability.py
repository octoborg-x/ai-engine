from fastapi.testclient import TestClient

from app.main import app
from app.telemetry.metrics import MetricsCollector

client = TestClient(app)


def test_metrics_endpoint_available():
    MetricsCollector.reset()
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "http_requests_total" in data
    assert "llm_calls_total" in data


def test_chat_increments_http_metrics():
    MetricsCollector.reset()
    client.post("/chat", json={"prompt": "hello"})
    metrics = client.get("/metrics").json()
    assert any(
        "POST" in str(k) and "/chat" in str(k)
        for k in metrics.get("http_requests_total", {})
    )


def test_correlation_ids_remain_present():
    response = client.get("/health")
    assert "x-request-id" in response.headers
    assert "x-trace-id" in response.headers


def test_failed_llm_increments_error_metrics():
    MetricsCollector.reset()
    MetricsCollector.record_llm(model="test/model", status="error", latency_ms=100.0)
    metrics = MetricsCollector.snapshot()
    assert metrics["llm_calls_total"].get("('test/model', 'error')", 0) >= 1


def test_token_cost_aggregated():
    MetricsCollector.reset()
    MetricsCollector.record_llm(
        model="m",
        status="success",
        latency_ms=50,
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
    )
    m = MetricsCollector.snapshot()
    assert m["llm_input_tokens_total"] == 100
    assert m["llm_output_tokens_total"] == 50
    assert m["llm_total_tokens_total"] == 150
    assert m["llm_estimated_cost_usd_total"] == 0.001


def test_metrics_contain_no_sensitive_content():
    MetricsCollector.reset()
    MetricsCollector.record_http("POST", "/chat", 200, 12.3)
    MetricsCollector.record_llm(
        "cohere/north-mini-code:free", "success", 45.6, 10, 5, 0.0
    )
    flat = str(MetricsCollector.snapshot())
    assert "secret" not in flat and "prompt" not in flat
