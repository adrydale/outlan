import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    db_fd, db_path = tempfile.mkstemp()
    app.config["TESTING"] = True
    # Patch the DB_PATH used in routes.py
    import app.routes

    app.routes.DB_PATH = db_path

    with app.test_client() as client:
        with app.app_context():
            from app.routes import init_db

            init_db()
        yield client

    os.close(db_fd)
    os.unlink(db_path)


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    # Adjust as needed
    assert b"IPAM" in response.data or b"ipam" in response.data


def test_root_route(client):
    response = client.get("/")
    assert response.status_code == 200


def test_init_db(client):
    response = client.post("/init_db", follow_redirects=True)
    # The database might already be initialized, so we accept both 200 and 400
    assert response.status_code in [200, 400]
    # Optionally, check for content that should appear after DB init
