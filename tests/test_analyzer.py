
import pytest
from app.analyzer import analyze
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def mock_files(tmp_path):
    # Create small test files
    f1 = tmp_path / "sample.csv"
    f1.write_text("endpoint,response_time,status_code\n/api/data,200,200\n")

    f2 = tmp_path / "app.log"
    f2.write_text("2025-07-26 12:00:01 INFO Request received\n")

    return [
        {"name": "sample.csv", "path": str(f1)},
        {"name": "app.log", "path": str(f2)}
    ]

@pytest.fixture
def test_context():
    return {
        "Type": "Smoke Test",
        "Duration": "5 minutes",
        "Virtual Users": "10",
        "Target": "Node.js API on GCP"
    }

def test_analyze_basic(monkeypatch, mock_files, test_context):
    # Mock ask_gpt to avoid real API call
    from app import ai_engine

    fake_response = """SUMMARY:
The system behaved correctly under light load.

INSIGHTS:
No errors were observed. Latency was acceptable.

RECOMMENDATIONS:
Try increasing virtual users to test scalability."""

    monkeypatch.setattr(ai_engine, "ask_gpt", lambda prompt: fake_response)

    result = analyze(mock_files, test_context)

    assert isinstance(result.get("summary"), str)
    assert isinstance(result.get("insights"), str)
    assert isinstance(result.get("recommendations"), str)

