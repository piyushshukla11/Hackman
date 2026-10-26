import os
import sys

hackman_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
backend_root = os.path.join(hackman_root, "backend")

for p in [hackman_root, backend_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Set fallback test environment variables before importing any prism_core modules
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://prism_user:prism_pass@localhost:5432/prism_test")
os.environ.setdefault("SECRET_KEY", "testing-secret-key-32-chars-minimum-abc12345")
os.environ.setdefault("ENVIRONMENT", "test")

