"""
workflows/tasks/rebuild_product.py

Render Workflows Task: rebuild_product(product_id: str)
Triggered after review batch processing completes:
1. Rebuilds issue graph (graph.rebuild)
2. Classifies defect concentration (p < 0.001)
3. Computes weekly rollups & Wilson confidence intervals (trend.roll_up)
4. Emits real-time SSE issue updates
"""
from __future__ import annotations

import time
from prism_core.db.base import get_sessionmaker
from prism_core.events import emit
from prism_core.graph import rebuild as rebuild_graph
from prism_core.trend import roll_up as rollup_trends


async def execute_rebuild_product(product_id: str, tenant_id: str = "default", attempt: int = 1) -> None:
    """Pure Python task implementation of product rebuild."""
    sessionmaker = get_sessionmaker()
    run_id = f"rebuild_{product_id[:8]}"
    t_start = time.perf_counter()

    async with sessionmaker() as session:
        await emit("rebuild_product", "started", run_id, tenant_id=tenant_id, attempt=attempt, session=session)

        # 1. Graph Rebuild & Defect Concentration
        clusters = await rebuild_graph(product_id=product_id, tenant_id=tenant_id, session=session)

        # 2. Trends & Rollups
        trends = await rollup_trends(product_id=product_id, tenant_id=tenant_id, session=session)

        dur_ms = int((time.perf_counter() - t_start) * 1000)
        await emit(
            "rebuild_product",
            "done",
            run_id,
            tenant_id=tenant_id,
            attempt=attempt,
            duration_ms=dur_ms,
            session=session,
            detail={"clusters_count": len(clusters), "trends_count": len(trends)},
        )

        await session.commit()
