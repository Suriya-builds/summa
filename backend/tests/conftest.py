import os
import sys
import tempfile
from pathlib import Path

import pytest

_TMP = tempfile.mkdtemp(prefix="summa-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TMP) / 'test.db'}"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ["ANTHROPIC_API_KEY"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.security import rate_limiter  # noqa: E402


@pytest.fixture(scope="session")
def _app():
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def client(_app):
    rate_limiter.reset()
    _app.cookies.clear()
    return _app


_counter = {"n": 0}


@pytest.fixture()
def user(client):
    _counter["n"] += 1
    r = client.post("/api/auth/signup", json={"name": "Test", "email": f"user{_counter['n']}@example.com", "password": "correct horse"})
    assert r.status_code == 201, r.text
    return r.json()["user"]
