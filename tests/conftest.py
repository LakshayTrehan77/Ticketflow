import os
import tempfile
from pathlib import Path

# these have to be set before the app is imported, the settings are read once
MODEL_FILE = Path(tempfile.mkdtemp()) / "classifier.joblib"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"
os.environ["AGENT_EMAILS"] = "agent@example.com"
os.environ["MODEL_PATH"] = str(MODEL_FILE)
os.environ.pop("REDIS_URL", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.cache import get_cache  # noqa: E402
from ml.train import train  # noqa: E402

train(out_path=MODEL_FILE)


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    get_cache().clear()
    with TestClient(app) as test_client:
        yield test_client


def make_headers(client: TestClient, email: str, password: str = "password123") -> dict:
    client.post("/auth/register", json={"email": email, "password": password})
    res = client.post("/auth/login", data={"username": email, "password": password})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture()
def user_headers(client):
    return make_headers(client, "user@example.com")


@pytest.fixture()
def other_user_headers(client):
    return make_headers(client, "other@example.com")


@pytest.fixture()
def agent_headers(client):
    return make_headers(client, "agent@example.com")
