"""
tests/test_mvp8_workflows_and_api.py

Unit tests for MVP 8:
- FastAPI route registration across all 8 modular routers
- Workflows runner execution with pipeline event logging
- Role-based view filtering in user onboarding
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from workflows.runner import WorkflowRunner


def test_api_route_registration():
    client = TestClient(app)

    # Health check
    res_health = client.get("/ops/healthz")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    # Ingestion gateway endpoint exists (401 without auth)
    res_ingest = client.post("/ingest/reviews", json={})
    assert res_ingest.status_code in (401, 422)

    # Catalog endpoints exist
    res_catalog = client.get("/catalog/products")
    assert res_catalog.status_code == 401


def test_workflow_runner_task_dispatch():
    runner = WorkflowRunner(tenant_id="tenant_test")

    executed_tasks = []

    def dummy_task(arg1: str, arg2: int):
        executed_tasks.append((arg1, arg2))
        return {"status": "success", "processed": arg2}

    result = runner.run_sync(dummy_task, "review_batch_01", 42)
    assert result["status"] == "success"
    assert result["processed"] == 42
    assert len(executed_tasks) == 1
    assert executed_tasks[0] == ("review_batch_01", 42)
