import os
import sys
from pathlib import Path

# Ensure project root is on sys.path for module resolution
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load .env.test if available to set test-safe environment
ENV_PATH = ROOT / ".env.test"
try:
    if ENV_PATH.exists():
        # Minimal .env loader to avoid extra deps if python-dotenv isn't installed in some envs
        # Prefer python-dotenv when available for robust parsing
        try:
            from dotenv import load_dotenv  # type: ignore
        except Exception:
            load_dotenv = None
        if load_dotenv:
            load_dotenv(dotenv_path=str(ENV_PATH), override=True)
        else:
            # Fallback: simple line parser for KEY=VALUE pairs
            for line in ENV_PATH.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
except Exception:
    # Do not fail test collection if .env parsing fails; tests will surface issues
    pass

# Ensure a default SQLite DB for local tests to avoid import-time DB hangs
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_archangel.db")

# Do not eagerly initialize DB schema here to avoid deadlocks during collection.
# Tests that need a database should import app.db_pg.init() explicitly or use helpers.
