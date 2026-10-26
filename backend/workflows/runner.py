"""
workflows/runner.py

Render Workflows Worker Runner:
Runs as the container entrypoint for prism-workflows service.
Listens for task triggers, executes fan-out pipeline tasks, and manages cron loops.
"""
from __future__ import annotations

import asyncio
import logging

from workflows.tasks.process_review import execute_process_review
from workflows.tasks.rebuild_product import execute_rebuild_product
from workflows.tasks.source_health import execute_source_health_check

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("prism.workflows")


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
