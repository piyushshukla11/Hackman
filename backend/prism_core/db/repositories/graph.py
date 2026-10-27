"""
prism_core/db/repositories/graph.py

Repositories for Issue Graph: Graph Edges, Issue Clusters, and Cluster Members.
Includes support for Click-to-Verify Audit Drawer and defect concentration metrics.
"""
from __future__ import annotations

from typing import Sequence
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.db.models import ClusterMember, GraphEdge, IssueCluster, Review, TrustGateLog
from prism_core.db.repositories.base import BaseRepository


class GraphEdgeRepository(BaseRepository[GraphEdge]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(GraphEdge, session, tenant_id)

    async def list_by_product(self, product_id: str) -> Sequence[GraphEdge]:
        stmt = self._scoped_query(GraphEdge.product_id == product_id).order_by(desc(GraphEdge.weight))
        res = await self.session.execute(stmt)
        return res.scalars().all()


class IssueClusterRepository(BaseRepository[IssueCluster]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(IssueCluster, session, tenant_id)

    async def list_by_product(
        self,
        product_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[IssueCluster]:
        clauses = []
        if product_id:
            clauses.append(IssueCluster.product_id == product_id)
        if status:
            clauses.append(IssueCluster.status == status)

        stmt = self._scoped_query(*clauses).order_by(desc(IssueCluster.confidence)).limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def get_audit_drawer_data(self, issue_id: str) -> dict:
        """
        Pull full audit data for Click-to-Verify Audit Drawer:
        - Issue cluster details (defect concentration, p-value, lead time)
        - Member reviews (unedited original text, verified purchase badge, author, channel, reviewed_at)
        - Trust gate audit logs per review
        """
        cluster = await self.get_by_id(issue_id)
        if not cluster:
            return {}

        # Fetch cluster members
        member_stmt = (
            select(ClusterMember, Review)
            .join(Review, ClusterMember.review_id == Review.id)
            .where(
                ClusterMember.tenant_id == self.tenant_id,
                ClusterMember.cluster_id == issue_id,
            )
        )
        member_res = await self.session.execute(member_stmt)
        members_data = []

        for cm, rev in member_res.all():
            # Get trust gates for this review
            gates_stmt = select(TrustGateLog).where(
                TrustGateLog.tenant_id == self.tenant_id,
                TrustGateLog.review_id == rev.id,
            )
            gates_res = await self.session.execute(gates_stmt)
            gates = [
                {
                    "gate": g.gate,
                    "verdict": g.verdict,
                    "reason_code": g.reason_code,
                    "score_delta": g.score_delta,
                }
                for g in gates_res.scalars().all()
            ]

            members_data.append({
                "review_id": rev.id,
                "role": cm.role,
                "text_original": rev.text_original,
                "text_en": rev.text_en,
                "rating": float(rev.rating),
                "channel": rev.channel,
                "verified_purchase": rev.verified_purchase,
                "batch_id": rev.batch_id,
                "batch_method": rev.batch_method,
                "reviewed_at": rev.reviewed_at.isoformat(),
                "trust_score": rev.trust_score,
                "trust_gates": gates,
            })

        return {
            "cluster_id": cluster.id,
            "feature": cluster.feature,
            "issue_type": cluster.issue_type,
            "severity": cluster.severity,
            "confidence": cluster.confidence,
            "confidence_parts": cluster.confidence_parts,
            "defect_concentration": cluster.defect_concentration,
            "dominant_batch_id": cluster.dominant_batch_id,
            "p_value": cluster.p_value,
            "lead_time_days": cluster.lead_time_days,
            "size": cluster.size,
            "members": members_data,
        }


class ClusterMemberRepository(BaseRepository[ClusterMember]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(ClusterMember, session, tenant_id)

    async def list_by_cluster(self, cluster_id: str) -> Sequence[ClusterMember]:
        stmt = self._scoped_query(ClusterMember.cluster_id == cluster_id)
        res = await self.session.execute(stmt)
        return res.scalars().all()
