"""Tests for the Flask API.

These are deliberately small but real — they gate the pipeline, so a broken
endpoint fails the build before anything is shipped.
"""

import pytest

from app.main import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_version(client):
    resp = client.get("/version")
    assert resp.status_code == 200
    assert "version" in resp.get_json()


def test_echo_valid(client):
    resp = client.post("/echo", json={"message": "hello"})
    assert resp.status_code == 200
    assert resp.get_json() == {"message": "hello"}


def test_echo_missing_field(client):
    resp = client.post("/echo", json={"nope": 1})
    assert resp.status_code == 400


def test_echo_non_string(client):
    resp = client.post("/echo", json={"message": 123})
    assert resp.status_code == 400


def test_echo_too_long(client):
    resp = client.post("/echo", json={"message": "x" * 501})
    assert resp.status_code == 400
