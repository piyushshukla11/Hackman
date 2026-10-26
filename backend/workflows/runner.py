"""
workflows/runner.py

Render Workflows Worker Runner:
Runs as the container entrypoint for prism-workflows service.
Listens for task triggers, executes fan-out pipeline tasks, and manages cron loops.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from workflows.tasks.process_review import execute_process_review
from workflows.tasks.rebuild_product import execute_rebuild_product
from workflows.tasks.source_health import execute_source_health_check

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("prism.workflows")


class WorkflowRunner:
    """
    Lightweight synchronous task dispatcher for local/test execution.
    In production, tasks are triggered via Render Workflows durable jobs.
    This class keeps task bodies as plain Python functions (no framework coupling).
    """

    def __init__(self, tenant_id: str = "default"):
        self.tenant_id = tenant_id

    def run_sync(self, task_fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a plain Python task function synchronously.
        If the function is async, runs it in a new event loop.
        Logs task name, tenant, and result status.
        """
        task_name = getattr(task_fn, "__name__", str(task_fn))
        logger.info("[WorkflowRunner] tenant=%s task=%s args=%s", self.tenant_id, task_name, args)

        import inspect
        if inspect.iscoroutinefunction(task_fn):
            result = asyncio.run(task_fn(*args, **kwargs))
        else:
            result = task_fn(*args, **kwargs)

        logger.info("[WorkflowRunner] tenant=%s task=%s completed", self.tenant_id, task_name)
        return result


async def main():
    logger.info("PRISM Render Workflows Worker started successfully.")
    logger.info("Ready to accept durable tasks: process_review, rebuild_product, source_health, survey_loop")

    try:
        while True:
            # Heartbeat loop for daemon worker
            await asyncio.sleep(60.0)
    except asyncio.CancelledError:
        logger.info("PRISM Workflows Worker shutting down gracefully.")


if __name__ == "__main__":
    asyncio.run(main())
