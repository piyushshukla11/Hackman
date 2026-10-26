"""
conftest.py  (repo root)

Makes `backend/`, `db/`, and `ml/` importable from the `tests/` directory.
This conftest runs before any test collection so all imports resolve correctly
regardless of the current working directory.
"""
from __future__ import annotations

import os
import sys

# --------------------------------------------------------------------------- #
# Path setup                                                                   #
# --------------------------------------------------------------------------- #
_ROOT = os.path.dirname(os.path.abspath(__file__))

# 1. backend/ — contains prism_core, api, workflows packages
_BACKEND = os.path.join(_ROOT, "backend")
# 2. db/      — standalone SQLAlchemy models and repositories
# 3. ml/      — standalone ML/NLP utilities

for _p in (_BACKEND, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# --------------------------------------------------------------------------- #
# Minimal env vars so Settings() can be instantiated without a .env file      #
# Real env vars (e.g. on Render) always override these test defaults.          #
# --------------------------------------------------------------------------- #
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://prism:prism@localhost:5432/prism_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only-not-for-production")
os.environ.setdefault("MAIL_PROVIDER", "simulated")
os.environ.setdefault("ENVIRONMENT", "test")

# --------------------------------------------------------------------------- #
# Shared pytest settings                                                        #
# --------------------------------------------------------------------------- #
import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration (requires DB/external services)")
    config.addinivalue_line("markers", "slow: mark test as slow (heavy model loading)")
