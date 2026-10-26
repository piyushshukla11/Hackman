"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Ensure pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(32), server_default='member', nullable=False),
        sa.Column('role_title', sa.String(128), nullable=True),
        sa.Column('selected_views', postgresql.JSONB(), server_default='[]', nullable=True),
        sa.Column('has_completed_onboarding', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('tenant_id', 'email', name='uq_users_tenant_email'),
    )

    # 2. api_keys
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('key_hash', sa.String(255), nullable=False, index=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('role', sa.String(32), server_default='admin', nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 3. feature_taxonomies
    op.create_table(
        'feature_taxonomies',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('category', sa.String(128), nullable=False, index=True),
        sa.Column('features', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 4. products
    op.create_table(
        'products',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(128), nullable=False, index=True),
        sa.Column('taxonomy_id', sa.String(64), sa.ForeignKey('feature_taxonomies.id'), nullable=True),
        sa.Column('custom_features', postgresql.JSONB(), server_default='[]', nullable=False),
        sa.Column('specs', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 5. product_versions
    op.create_table(
        'product_versions',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('product_id', sa.String(64), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('label', sa.String(64), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 6. modifications
    op.create_table(
        'modifications',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('product_id', sa.String(64), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('from_version', sa.String(64), nullable=False),
        sa.Column('to_version', sa.String(64), nullable=False),
        sa.Column('change_note', sa.Text(), nullable=False),
        sa.Column('target_feature', sa.String(128), nullable=False),
        sa.Column('target_issue_id', sa.String(64), nullable=True),
        sa.Column('effective_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 7. batches
    op.create_table(
        'batches',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('product_id', sa.String(64), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('version_id', sa.String(64), sa.ForeignKey('product_versions.id'), nullable=True),
        sa.Column('code', sa.String(64), nullable=False, index=True),
        sa.Column('mfg_start', sa.Date(), nullable=True),
        sa.Column('mfg_end', sa.Date(), nullable=True),
        sa.Column('ship_start', sa.Date(), nullable=True),
        sa.Column('ship_end', sa.Date(), nullable=True),
        sa.Column('warehouse', sa.String(64), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 8. sources
    op.create_table(
        'sources',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('kind', sa.String(64), nullable=False),
        sa.Column('adapter', sa.String(64), nullable=True),
        sa.Column('display_name', sa.String(128), nullable=False),
        sa.Column('config', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('cursor', sa.String(255), nullable=True),
        sa.Column('enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 9. source_health
    op.create_table(
        'source_health',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('source_id', sa.String(64), sa.ForeignKey('sources.id'), nullable=False, index=True),
        sa.Column('checked_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('status', sa.String(32), server_default='healthy', nullable=False),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lag_seconds', sa.Integer(), server_default='0', nullable=False),
        sa.Column('items_24h', sa.Integer(), server_default='0', nullable=False),
        sa.Column('expected_24h', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_rate', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('schema_drift', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 10. raw_reviews
    op.create_table(
        'raw_reviews',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('source_id', sa.String(64), sa.ForeignKey('sources.id'), nullable=False, index=True),
        sa.Column('idempotency_key', sa.String(64), nullable=False, unique=True, index=True),
        sa.Column('kind', sa.String(32), server_default='review', nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 11. reviews (Canonical)
    op.create_table(
        'reviews',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('raw_id', sa.String(64), sa.ForeignKey('raw_reviews.id'), nullable=False, index=True),
        sa.Column('product_id', sa.String(64), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('source_id', sa.String(64), sa.ForeignKey('sources.id'), nullable=False, index=True),
        sa.Column('channel', sa.String(64), nullable=False, index=True),
        sa.Column('rating', sa.Numeric(2, 1), nullable=False),
        sa.Column('rating_raw', sa.String(64), nullable=True),
        sa.Column('rating_scale', sa.String(32), nullable=True),
        sa.Column('text_original', sa.Text(), nullable=True),
        sa.Column('text_en', sa.Text(), nullable=True),
        sa.Column('lang', sa.String(32), nullable=True),
        sa.Column('script', sa.String(32), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('dispatch_date', sa.Date(), nullable=True),
        sa.Column('warehouse', sa.String(64), nullable=True),
        sa.Column('seller', sa.String(128), nullable=True),
        sa.Column('verified_purchase', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('author_hash', sa.String(64), nullable=True, index=True),
        sa.Column('media', postgresql.JSONB(), server_default='[]', nullable=False),
        sa.Column('batch_id', sa.String(64), sa.ForeignKey('batches.id'), nullable=True, index=True),
        sa.Column('batch_method', sa.String(8), nullable=True),
        sa.Column('batch_conf', sa.Float(), nullable=True),
        sa.Column('version_id', sa.String(64), sa.ForeignKey('product_versions.id'), nullable=True, index=True),
        sa.Column('text_status', sa.String(32), server_default='accepted', nullable=False),
        sa.Column('rating_status', sa.String(32), server_default='counted', nullable=False),
        sa.Column('trust_score', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('ambiguity', sa.String(32), server_default='none', nullable=False),
        sa.Column('ambiguity_mult', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('embedding', pgvector.sqlalchemy.Vector(384), nullable=True),
        sa.Column('stage_versions', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_reviews_tenant_product_reviewed', 'reviews', ['tenant_id', 'product_id', 'reviewed_at'])
    op.execute(
        "CREATE INDEX ix_reviews_embedding_hnsw ON reviews USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"
    )

    # 12. review_features
    op.create_table(
        'review_features',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('review_id', sa.String(64), sa.ForeignKey('reviews.id'), nullable=False, index=True),
        sa.Column('feature', sa.String(128), nullable=False, index=True),
        sa.Column('polarity', sa.String(16), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('ambiguity', sa.String(32), server_default='none', nullable=False),
        sa.Column('sentence_idx', sa.Integer(), server_default='0', nullable=False),
        sa.Column('anchor_sim', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 13. trust_gate_log
    op.create_table(
        'trust_gate_log',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('review_id', sa.String(64), sa.ForeignKey('reviews.id'), nullable=False, index=True),
        sa.Column('gate', sa.String(8), nullable=False),
        sa.Column('verdict', sa.String(16), nullable=False),
        sa.Column('reason_code', sa.String(64), nullable=False),
        sa.Column('score_delta', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('detail', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 14. graph_edges
    op.create_table(
        'graph_edges',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('src_review_id', sa.String(64), sa.ForeignKey('reviews.id'), nullable=False, index=True),
        sa.Column('dst_review_id', sa.String(64), sa.ForeignKey('reviews.id'), nullable=False, index=True),
        sa.Column('product_id', sa.String(64), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('feature', sa.String(128), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 15. issue_clusters
    op.create_table(
        'issue_clusters',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('product_id', sa.String(64), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('feature', sa.String(128), nullable=False, index=True),
        sa.Column('polarity', sa.String(16), server_default='neg', nullable=False),
        sa.Column('issue_type', sa.String(32), nullable=False),
        sa.Column('severity', sa.String(16), server_default='medium', nullable=False),
        sa.Column('confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('confidence_parts', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('first_seen', sa.Date(), nullable=False),
        sa.Column('last_seen', sa.Date(), nullable=False),
        sa.Column('size', sa.Integer(), server_default='0', nullable=False),
        sa.Column('channels', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('batches', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('versions', postgresql.JSONB(), server_default='[]', nullable=False),
        sa.Column('defect_concentration', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('dominant_batch_id', sa.String(64), sa.ForeignKey('batches.id'), nullable=True),
        sa.Column('p_value', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('lead_time_days', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', sa.String(32), server_default='open', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 16. cluster_members
    op.create_table(
        'cluster_members',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('cluster_id', sa.String(64), sa.ForeignKey('issue_clusters.id'), nullable=False, index=True),
        sa.Column('review_id', sa.String(64), sa.ForeignKey('reviews.id'), nullable=False, index=True),
        sa.Column('role', sa.String(32), server_default='member', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 17. metric_rollups
    op.create_table(
        'metric_rollups',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('product_id', sa.String(64), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('version_id', sa.String(64), nullable=True, index=True),
        sa.Column('batch_id', sa.String(64), nullable=True, index=True),
        sa.Column('channel', sa.String(64), nullable=False, index=True),
        sa.Column('feature', sa.String(128), nullable=False, index=True),
        sa.Column('week', sa.Date(), nullable=False, index=True),
        sa.Column('n_reviews', sa.Integer(), server_default='0', nullable=False),
        sa.Column('n_neg', sa.Integer(), server_default='0', nullable=False),
        sa.Column('n_pos', sa.Integer(), server_default='0', nullable=False),
        sa.Column('rating_w_sum', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('rating_w', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('rating_n_all', sa.Integer(), server_default='0', nullable=False),
        sa.Column('rating_sum_all', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_metric_rollups_lookup', 'metric_rollups', ['tenant_id', 'product_id', 'feature', 'week'])

    # 18. trend_points
    op.create_table(
        'trend_points',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('product_id', sa.String(64), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('feature', sa.String(128), nullable=False, index=True),
        sa.Column('channel', sa.String(64), nullable=False),
        sa.Column('window', sa.Date(), nullable=False, index=True),
        sa.Column('n', sa.Integer(), server_default='0', nullable=False),
        sa.Column('neg_rate', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('neg_ci_low', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('neg_ci_high', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('rating_mean_trusted', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('rating_mean_all', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('pattern', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 19. serious_complaints
    op.create_table(
        'serious_complaints',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('review_id', sa.String(64), sa.ForeignKey('reviews.id'), nullable=False, index=True),
        sa.Column('category', sa.String(64), nullable=False),
        sa.Column('severity', sa.String(16), server_default='high', nullable=False),
        sa.Column('urgency', sa.String(16), server_default='high', nullable=False),
        sa.Column('status', sa.String(32), server_default='open', nullable=False),
        sa.Column('alerted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 20. surveys
    op.create_table(
        'surveys',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('issue_id', sa.String(64), sa.ForeignKey('issue_clusters.id'), nullable=False, index=True),
        sa.Column('review_id', sa.String(64), sa.ForeignKey('reviews.id'), nullable=False, index=True),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True, index=True),
        sa.Column('questions', postgresql.JSONB(), server_default='[]', nullable=False),
        sa.Column('status', sa.String(32), server_default='sent', nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 21. survey_responses
    op.create_table(
        'survey_responses',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('survey_id', sa.String(64), sa.ForeignKey('surveys.id'), nullable=False, index=True),
        sa.Column('answers', postgresql.JSONB(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('confidence_delta', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 22. email_outbox
    op.create_table(
        'email_outbox',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('template', sa.String(64), nullable=False),
        sa.Column('to_hash', sa.String(64), nullable=False, index=True),
        sa.Column('payload', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('status', sa.String(32), server_default='queued', nullable=False),
        sa.Column('provider_id', sa.String(128), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 23. alerts
    op.create_table(
        'alerts',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('product_id', sa.String(64), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('kind', sa.String(64), nullable=False),
        sa.Column('severity', sa.String(16), server_default='medium', nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('triggered_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 24. reports
    op.create_table(
        'reports',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('product_id', sa.String(64), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('range_start', sa.Date(), nullable=False),
        sa.Column('range_end', sa.Date(), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 25. pipeline_events
    op.create_table(
        'pipeline_events',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('run_id', sa.String(64), nullable=False, index=True),
        sa.Column('review_id', sa.String(64), nullable=True, index=True),
        sa.Column('stage', sa.String(64), nullable=False, index=True),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('attempt', sa.Integer(), server_default='1', nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('detail', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 26. eval_runs
    op.create_table(
        'eval_runs',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('dataset', sa.String(128), nullable=False),
        sa.Column('metrics', postgresql.JSONB(), nullable=False),
        sa.Column('git_sha', sa.String(40), nullable=True),
        sa.Column('at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 27. returns_series
    op.create_table(
        'returns_series',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('product_id', sa.String(64), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('version_id', sa.String(64), sa.ForeignKey('product_versions.id'), nullable=True),
        sa.Column('batch_id', sa.String(64), sa.ForeignKey('batches.id'), nullable=True),
        sa.Column('week', sa.Date(), nullable=False, index=True),
        sa.Column('returns_n', sa.Integer(), server_default='0', nullable=False),
        sa.Column('units_n', sa.Integer(), server_default='0', nullable=False),
        sa.Column('simulated', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('returns_series')
    op.drop_table('eval_runs')
    op.drop_table('pipeline_events')
    op.drop_table('reports')
    op.drop_table('alerts')
    op.drop_table('email_outbox')
    op.drop_table('survey_responses')
    op.drop_table('surveys')
    op.drop_table('serious_complaints')
    op.drop_table('trend_points')
    op.drop_table('metric_rollups')
    op.drop_table('cluster_members')
    op.drop_table('issue_clusters')
    op.drop_table('graph_edges')
    op.drop_table('trust_gate_log')
    op.drop_table('review_features')
    op.drop_table('reviews')
    op.drop_table('raw_reviews')
    op.drop_table('source_health')
    op.drop_table('sources')
    op.drop_table('batches')
    op.drop_table('modifications')
    op.drop_table('product_versions')
    op.drop_table('products')
    op.drop_table('feature_taxonomies')
    op.drop_table('api_keys')
    op.drop_table('users')
