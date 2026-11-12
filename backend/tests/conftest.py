import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture
def client():
    with tempfile.TemporaryDirectory() as folder:
        os.environ["RPG_DB_PATH"] = os.path.join(folder, "testing.sqlite3")
        with TestClient(app) as test_client:
            yield test_client
        os.environ.pop("RPG_DB_PATH", None)
