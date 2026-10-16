"""Tests for the new console-facing endpoints: observability, compare,
evaluation, recruitment screening, and the security policy surface.

All LLM calls are stubbed so the suite stays hermetic.
"""

import os

os.environ.setdefault("API_AUTH_TOKEN", "test-auth-token")

import pytest
from fastapi.testclient import TestClient

import app.main as api
from app.recruitment import screening
from app.security.rate_limit import rate_limiter
from app.telemetry import records

client = TestClient(api.app)
auth_headers = {"Authorization": "Bearer test-auth-token"}


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    rate_limiter._hits.clear()
    yield


# --- observability records -------------------------------------------------


def test_observability_records_are_captured_and_protected():
    records.reset()
    client.get("/health")
    response = client.get("/observability/requests", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert any(r["path"] == "/health" for r in data["requests"])
    assert "llm_calls" in data


def test_observability_requires_auth():
    assert client.get("/observability/requests").status_code == 401


def test_observability_records_store_no_prompt_content():
    records.reset()
    client.post("/chat", json={"prompt": "super-secret-prompt"}, headers=auth_headers)
    payload = client.get("/observability/requests", headers=auth_headers).json()
    assert "super-secret-prompt" not in str(payload)


# --- compare ---------------------------------------------------------------


def test_compare_runs_every_tier(monkeypatch):
    async def fake_ask(prompt, tier=None):
        return {
            "response": "A response mentioning request and response and software.",
            "model": f"{tier}/model",
            "route": tier,
            "route_reason": "tier pinned by request",
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "estimated_cost_usd": 0.0,
            "latency_ms": 12.0,
            "success": True,
        }

    monkeypatch.setattr("app.evals.compare.ask", fake_ask)
    response = client.get("/compare?limit=2", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert [r["tier"] for r in data["results"]] == [
        "main",
        "cheap",
        "balanced",
        "powerful",
    ]
    for result in data["results"]:
        assert result["cases"] == 2
        assert result["latency_ms"]["p95"] is not None
        assert "pass_rate" in result


def test_compare_requires_auth():
    assert client.get("/compare").status_code == 401


# --- evaluations -----------------------------------------------------------


def test_eval_suites_lists_case_counts():
    response = client.get("/evals/suites", headers=auth_headers)
    assert response.status_code == 200
    suites = {s["name"]: s["cases"] for s in response.json()["suites"]}
    assert suites["chat"] == 40
    assert suites["extraction"] == 40
    assert suites["classification"] == 10
    assert suites["adversarial"] == 20


def test_evals_run_reports_measured_accuracy(monkeypatch):
    async def fake_ask(prompt, tier=None):
        return {
            "response": "request response software",
            "model": "m",
            "route": "balanced",
            "route_reason": "r",
            "prompt_tokens": 3,
            "completion_tokens": 2,
            "estimated_cost_usd": 0.0,
            "latency_ms": 5.0,
            "success": True,
        }

    monkeypatch.setattr("app.evals.engine.ask", fake_ask)
    response = client.post(
        "/evals/run",
        json={"suites": ["chat"], "limit": 3},
        headers=auth_headers,
    )
    assert response.status_code == 200
    report = response.json()
    assert report["suites"][0]["suite"] == "chat"
    assert report["suites"][0]["total_cases"] == 3
    assert report["totals"]["evaluated_cases"] == 3


def test_evals_run_requires_auth():
    assert client.post("/evals/run", json={}).status_code == 401


def test_evals_run_without_body_defaults_to_all_suites(monkeypatch):
    """An omitted body must not error; it falls back to the packaged suites."""

    async def fake_ask(prompt, tier=None):
        return {
            "response": "request response software",
            "model": "m",
            "route": "balanced",
            "route_reason": "r",
            "prompt_tokens": 3,
            "completion_tokens": 2,
            "estimated_cost_usd": 0.0,
            "latency_ms": 5.0,
            "success": True,
        }

    monkeypatch.setattr("app.evals.engine.ask", fake_ask)
    response = client.post("/evals/run", headers=auth_headers)
    assert response.status_code == 200
    names = [suite["suite"] for suite in response.json()["suites"]]
    assert "retrieval" in names


def test_evals_run_rejects_malformed_body():
    response = client.post(
        "/evals/run",
        content=b"not-json",
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert response.status_code == 422


# --- recruitment screening -------------------------------------------------


def _profile():
    return screening.CandidateProfile(
        name="Ada",
        years_experience=6,
        skills=["Python", "FastAPI", "Docker"],
        education="MSc",
        highlights=[],
    )


def _requirements():
    return screening.JobRequirements(
        role="Backend Engineer",
        required_skills=["Python", "FastAPI", "Kubernetes"],
        min_years=5,
        nice_to_have=["Docker"],
        responsibilities=[],
    )


def test_score_candidate_is_deterministic_and_explainable():
    score, matched, missing, evidence = screening.score_candidate(
        _profile(), _requirements()
    )
    # 2/3 required skills + full experience + docker bonus.
    assert matched == ["Python", "FastAPI"]
    assert missing == ["Kubernetes"]
    assert 0 < score <= 100
    assert any(e.criterion.startswith("Required skill") for e in evidence)
    assert screening.score_candidate(_profile(), _requirements())[0] == score


def test_recommendation_thresholds():
    assert screening._recommendation(90) == "advance"
    assert screening._recommendation(60) == "hold"
    assert screening._recommendation(10) == "reject"


def test_screen_endpoint_end_to_end(monkeypatch):
    async def fake_complete_json(prompt, task="extraction", tier=None):
        if "recruiter" in prompt:
            data = {
                "role": "Backend Engineer",
                "required_skills": ["Python", "Kubernetes"],
                "min_years": 5,
                "nice_to_have": ["Docker"],
                "responsibilities": [],
            }
        else:
            data = {
                "name": "Ada",
                "years_experience": 6,
                "skills": ["Python", "Docker"],
                "education": "MSc",
                "highlights": [],
            }
        meta = {
            "model": "main/model",
            "route": tier or "main",
            "route_reason": "candidate screening pinned to main tier",
            "prompt_tokens": 20,
            "completion_tokens": 10,
            "estimated_cost_usd": 0.0,
            "latency_ms": 8.0,
        }
        return data, meta

    monkeypatch.setattr(screening, "complete_json", fake_complete_json)
    response = client.post(
        "/recruitment/screen",
        json={
            "job_description": "Backend engineer with Python and Kubernetes.",
            "resume": "Ada, 6 years, Python and Docker.",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    report = response.json()
    assert report["recommendation"] in {"advance", "hold", "reject"}
    assert "Python" in report["matched_skills"]
    assert "Kubernetes" in report["missing_skills"]
    assert report["evidence"]


def test_screen_requires_auth():
    response = client.post(
        "/recruitment/screen",
        json={"job_description": "x" * 20, "resume": "y" * 20},
    )
    assert response.status_code == 401


# --- models & retrieval ----------------------------------------------------


def test_models_lists_tiers_without_secrets(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "main/model")
    monkeypatch.setenv("MODEL_CHEAP", "cheap/model")
    response = client.get("/models", headers=auth_headers)
    assert response.status_code == 200
    tiers = {t["tier"]: t for t in response.json()["tiers"]}
    assert set(tiers) == {"main", "cheap", "balanced", "powerful"}
    assert tiers["main"]["model"] == "main/model"
    assert tiers["main"]["env_var"] == "MODEL_NAME"
    assert tiers["cheap"]["model"] == "cheap/model"
    assert "API_AUTH_TOKEN" not in str(response.json())


def test_rag_retrieve_returns_candidates_and_citations():
    response = client.post(
        "/rag/retrieve",
        json={"query": "what is the refund policy?", "recall_k": 5, "final_k": 2},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sources"]
    assert data["candidates"]
    assert "[S1]" in data["context"]
    assert any(c["kept"] for c in data["candidates"])


def test_rag_retrieve_requires_auth():
    assert client.post("/rag/retrieve", json={"query": "x"}).status_code == 401


# --- security policy -------------------------------------------------------


def test_security_policy_exposes_no_secrets():
    response = client.get("/security/policy", headers=auth_headers)
    assert response.status_code == 200
    policy = response.json()
    assert policy["auth"]["enabled"] is True
    assert policy["rate_limit"]["limit"] >= 1
    assert "POST /chat" in policy["protected_routes"]
    flat = str(policy)
    assert "test-auth-token" not in flat


# --- saved results --------------------------------------------------------


def test_results_index_lists_saved_slots(monkeypatch, tmp_path):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))

    (tmp_path / "compare-example-1.json").write_text(
        '{"timestamp": "t", "cases_per_tier": 3, "results": []}',
        encoding="utf-8",
    )
    response = client.get("/results", headers=auth_headers)
    assert response.status_code == 200
    compare = response.json()["results"]["compare"]
    assert [e["key"] for e in compare] == ["compare-example-1"]


def test_results_saved_serves_existing_result(monkeypatch, tmp_path):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    (tmp_path / "evals-example-2.json").write_text(
        '{"timestamp": "t", "suites": [], "totals": {}}', encoding="utf-8"
    )
    response = client.get(
        "/results/saved", params={"tab": "evals", "slot": 2}, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["_meta"]["slot"] == 2
    assert data["_meta"]["key"] == "evals-example-2"


def test_results_saved_falls_back_to_bundled_seeds(monkeypatch, tmp_path):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    # No writable results: the store must serve the shipped example files so
    # the dashboard works even on a backend-only deploy.
    response = client.get(
        "/results/saved", params={"tab": "compare"}, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["cases_per_tier"] == 5
    assert data["_meta"]["key"] == "compare-example-3"
    assert "seed_results" in data["_meta"]["path"]


def test_results_save_persists_and_rotates(monkeypatch, tmp_path):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    first = client.post(
        "/results/save",
        json={"tab": "compare", "result": {"run": 1}},
        headers=auth_headers,
    )
    assert first.status_code == 200
    assert first.json()["slot"] == 1
    second = client.post(
        "/results/save",
        json={"tab": "compare", "result": {"run": 2}},
        headers=auth_headers,
    )
    assert second.status_code == 200
    assert second.json()["slot"] == 2
    saved = client.get(
        "/results/saved", params={"tab": "compare"}, headers=auth_headers
    )
    assert saved.json()["run"] == 2


def test_results_save_rejects_unknown_tab():
    response = client.post(
        "/results/save",
        json={"tab": "nope", "result": {}},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_results_retrieval_tab_served_from_bundled_seeds(monkeypatch, tmp_path):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    # The retrieval dashboard also consumes the saved-results store.
    response = client.get(
        "/results/saved", params={"tab": "retrieval"}, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["_meta"]["key"] == "retrieval-example-3"
    assert data["suites"][0]["suite"] == "retrieval"
    assert "seed_results" in data["_meta"]["path"]


def test_results_recruitment_tab_served_from_bundled_seeds(monkeypatch, tmp_path):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    # The Recruitment panel consumes the same saved-results store.
    response = client.get(
        "/results/saved", params={"tab": "recruitment"}, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["_meta"]["key"] == "recruitment-example-3"
    assert "candidate" in data and "recommendation" in data
    assert data["candidate"]["name"]
    assert "seed_results" in data["_meta"]["path"]


def test_results_require_auth():
    assert client.get("/results").status_code == 401
    assert client.get("/results/saved").status_code == 401
    assert (
        client.post("/results/save", json={"tab": "compare", "result": {}}).status_code
        == 401
    )


# --- retrieval quality suite ----------------------------------------------


def test_retrieval_suite_reports_measured_metrics():
    response = client.post(
        "/evals/run", json={"suites": ["retrieval"], "limit": 10}, headers=auth_headers
    )
    assert response.status_code == 200
    suite = response.json()["suites"][0]
    assert suite["suite"] == "retrieval"
    assert suite["total_cases"] == 10
    metrics = suite["retrieval"]
    assert 0.0 <= metrics["hit_rate_at_k"] <= 1.0
    assert 0.0 <= metrics["recall_at_k"] <= 1.0
    assert 0.0 <= metrics["precision_at_k"] <= 1.0
    assert 0.0 <= metrics["mrr"] <= 1.0
    # Labeled questions are answerable from the corpus, so recall must be real.
    assert metrics["hit_rate_at_k"] > 0.5
    # Deterministic pipeline: no provider cost.
    assert suite["cost"]["total_usd"] == 0.0
    assert suite["tokens"]["total"] == 0
