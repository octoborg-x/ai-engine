# pylint: disable=import-error,wrong-import-position
"""Integration tests for Day 5 /ask endpoint."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "week2" / "day5"))
sys.path.insert(0, str(Path(__file__).parent.parent / "week2" / "day4"))

from api import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_ask_endpoint_returns_200():
    """POST /ask should return 200 with valid query."""
    response = client.post("/ask", json={"query": "what is the refund policy?"})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert len(data["sources"]) > 0


def test_ask_endpoint_rejects_empty_query():
    """POST /ask with empty query should return 400."""
    response = client.post("/ask", json={"query": "   "})
    assert response.status_code == 400
