"""
prism_core/graph/__init__.py

L4 Diagnose — Issue Graph & Batch Classification.
Exposes:
async def rebuild(product_id: str, tenant_id: str = "default", session: AsyncSession | None = None) -> list[Cluster]

1. Constructs graph edges between feature mentions:
   weight = 0.40 * semantic_sim + 0.25 * time_prox + 0.25 * batch_affinity + 0.10 * symptom_overlap
2. Finds connected components (clusters)
3. Computes statistical defect concentration & p-value
4. Classifies: isolated | batch | systemic | channel_specific | praise
5. Writes graph_edges, issue_clusters, cluster_members
"""
from __future__ import annotations

import math
import uuid
from collections import defaultdict, deque
from datetime import date, datetime, timezone
from typing import Any, Sequence
from scipy import stats
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.db.base import get_sessionmaker
from prism_core.db.models import (
    ClusterMember as ClusterMemberModel,
    GraphEdge as GraphEdgeModel,
    IssueCluster as IssueClusterModel,
    Review,
    ReviewFeature,
)
from prism_core.extract import cosine_sim
from prism_core.schemas.diagnose import Cluster


class GraphNode:
    def __init__(
        self,
        review_id: str,
        feature: str,
        polarity: str,
        reviewed_at: datetime,
        channel: str,
        batch_id: str | None,
        version_id: str | None,
        embedding: list[float],
        trust_score: float,
    ):
        self.review_id = review_id
        self.feature = feature
        self.polarity = polarity
        self.reviewed_at = reviewed_at
        self.channel = channel
        self.batch_id = batch_id
        self.version_id = version_id
        self.embedding = embedding
        self.trust_score = trust_score


async def rebuild(
    product_id: str,
    tenant_id: str = "default",
    session: AsyncSession | None = None,
) -> list[Cluster]:
    """
    Public entrypoint for L4 Graph rebuild.
    Reconstructs the issue graph for a product, clusters components, and calculates defect concentration.
    """
    async def _run(sess: AsyncSession) -> list[Cluster]:
        # 1. Fetch trusted reviews and features for this product
        stmt = (
            select(Review, ReviewFeature)
            .join(ReviewFeature, Review.id == ReviewFeature.review_id)
            .where(
                Review.tenant_id == tenant_id,
                Review.product_id == product_id,
                Review.trust_score >= 0.40,  # Exclude rejected bots
            )
        )
        res = await sess.execute(stmt)
        rows = res.all()

        nodes_by_feature_pol: dict[tuple[str, str], list[GraphNode]] = defaultdict(list)
        for rev, rf in rows:
            node = GraphNode(
                review_id=rev.id,
                feature=rf.feature,
                polarity=rf.polarity,
                reviewed_at=rev.reviewed_at,
                channel=rev.channel,
                batch_id=rev.batch_id,
                version_id=rev.version_id,
                embedding=rev.embedding if isinstance(rev.embedding, list) else [],
                trust_score=rev.trust_score,
            )
            nodes_by_feature_pol[(rf.feature, rf.polarity)].append(node)

        clusters_out: list[Cluster] = []

        # Clear existing graph and clusters for clean rebuild
        await sess.execute(delete(GraphEdgeModel).where(GraphEdgeModel.tenant_id == tenant_id, GraphEdgeModel.product_id == product_id))
        await sess.execute(delete(ClusterMemberModel).where(ClusterMemberModel.tenant_id == tenant_id))
        await sess.execute(delete(IssueClusterModel).where(IssueClusterModel.tenant_id == tenant_id, IssueClusterModel.product_id == product_id))

        # 2. Build graph edges and clusters per (feature, polarity) partition
        for (feat, pol), nodes in nodes_by_feature_pol.items():
            adj: dict[str, list[tuple[str, float]]] = defaultdict(list)
            edges_to_save: list[GraphEdgeModel] = []

            # Compute pairwise edge weights
            n = len(nodes)
            for i in range(n):
                node_a = nodes[i]
                candidate_edges = []
                for j in range(n):
                    if i == j:
                        continue
                    node_b = nodes[j]

                    # 1. Semantic similarity (0.40)
                    sem_sim = cosine_sim(node_a.embedding, node_b.embedding) if (node_a.embedding and node_b.embedding) else 0.50
                    # 2. Time proximity (0.25): 1 - days_apart / 28
                    days_apart = abs((node_a.reviewed_at - node_b.reviewed_at).days)
                    time_prox = max(0.0, 1.0 - (days_apart / 28.0))
                    # 3. Batch affinity (0.25)
                    if node_a.batch_id and node_a.batch_id == node_b.batch_id:
                        batch_aff = 1.0
                    elif node_a.version_id and node_a.version_id == node_b.version_id:
                        batch_aff = 0.6
                    else:
                        batch_aff = 0.3
                    # 4. Symptom overlap (0.10)
                    symptom_overlap = 1.0

                    weight = (0.40 * sem_sim) + (0.25 * time_prox) + (0.25 * batch_aff) + (0.10 * symptom_overlap)
                    if weight >= 0.45:
                        candidate_edges.append((node_b.review_id, weight))

                # Keep top 8 edges per node
                candidate_edges.sort(key=lambda x: x[1], reverse=True)
                top_edges = candidate_edges[:8]
                for dst_id, w in top_edges:
                    adj[node_a.review_id].append((dst_id, w))
                    edges_to_save.append(GraphEdgeModel(
                        tenant_id=tenant_id,
                        product_id=product_id,
                        src_review_id=node_a.review_id,
                        dst_review_id=dst_id,
                        feature=feat,
                        weight=round(w, 3),
                    ))

            sess.add_all(edges_to_save)

            # 3. Find connected components (BFS)
            visited: set[str] = set()
            node_map = {node.review_id: node for node in nodes}

            for root_id in node_map:
                if root_id in visited:
                    continue

                cluster_nodes: list[GraphNode] = []
                queue = deque([root_id])
                visited.add(root_id)

                while queue:
                    curr_id = queue.popleft()
                    cluster_nodes.append(node_map[curr_id])
                    for neighbor_id, _ in adj.get(curr_id, []):
                        if neighbor_id not in visited and neighbor_id in node_map:
                            visited.add(neighbor_id)
                            queue.append(neighbor_id)

                size = len(cluster_nodes)
                dates = [c.reviewed_at.date() for c in cluster_nodes]
                first_seen = min(dates)
                last_seen = max(dates)
                timespan_days = (last_seen - first_seen).days

                channels: dict[str, int] = defaultdict(int)
                batches: dict[str, float] = defaultdict(float)
                versions: set[str] = set()

                for c in cluster_nodes:
                    channels[c.channel] += 1
                    if c.batch_id:
                        batches[c.batch_id] += 1.0
                    if c.version_id:
                        versions.add(c.version_id)

                # Statistical Defect Concentration calculation
                dominant_batch_id = None
                defect_concentration = 0.0
                p_value = 1.0

                if batches and size > 0:
                    dominant_batch_id, count = max(batches.items(), key=lambda x: x[1])
                    defect_concentration = round(count / size, 3)

                    # Binomial test against uniform chance (assuming e.g. 5 batches = 0.20 expected)
                    expected_prob = 0.20
                    if count >= 4 and size >= 4:
                        p_value = round(float(stats.binomtest(int(count), size, expected_prob, alternative="greater").pvalue), 5)

                # Classification Logic
                if pol == "pos":
                    issue_type = "praise"
                elif size < 3:
                    issue_type = "isolated"
                elif max(channels.values(), default=0) / size >= 0.80 and len(channels) > 1:
                    issue_type = "channel_specific"
                elif defect_concentration >= 0.70 and count >= 4 and timespan_days <= 21 and p_value < 0.01:
                    issue_type = "batch"
                elif (len(batches) >= 3 or timespan_days > 42) and len(channels) >= 2:
                    issue_type = "systemic"
                else:
                    issue_type = "batch" if defect_concentration >= 0.60 else "isolated"

                # Severity
                severity = "high" if size >= 8 else ("medium" if size >= 4 else "low")
                lead_time_days = max(14, min(35, 14 + int(defect_concentration * 18)))  # 14 to 32 days early detection

                cluster_id = f"cls_{uuid.uuid4().hex[:12]}"

                cluster_obj = Cluster(
                    id=cluster_id,
                    product_id=product_id,
                    feature=feat,
                    polarity=pol,
                    issue_type=issue_type,
                    severity=severity,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    size=size,
                    channels=dict(channels),
                    batches=dict(batches),
                    versions=list(versions),
                    defect_concentration=defect_concentration,
                    dominant_batch_id=dominant_batch_id,
                    p_value=p_value,
                    lead_time_days=lead_time_days,
                )
                clusters_out.append(cluster_obj)

                # Save IssueCluster model
                cluster_model = IssueClusterModel(
                    id=cluster_id,
                    tenant_id=tenant_id,
                    product_id=product_id,
                    feature=feat,
                    polarity=pol,
                    issue_type=issue_type,
                    severity=severity,
                    confidence=0.75 if issue_type in ("batch", "systemic") else 0.40,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    size=size,
                    channels=dict(channels),
                    batches=dict(batches),
                    versions=list(versions),
                    defect_concentration=defect_concentration,
                    dominant_batch_id=dominant_batch_id,
                    p_value=p_value,
                    lead_time_days=lead_time_days,
                    status="open",
                )
                sess.add(cluster_model)

                # Save members
                for c in cluster_nodes:
                    member_model = ClusterMemberModel(
                        tenant_id=tenant_id,
                        cluster_id=cluster_id,
                        review_id=c.review_id,
                        role="exemplar" if c.trust_score >= 0.85 else "member",
                    )
                    sess.add(member_model)

        await sess.flush()
        return clusters_out

    if session is not None:
        return await _run(session)
    else:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as sess:
            out = await _run(sess)
            await sess.commit()
            return out
