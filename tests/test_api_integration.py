import pytest
from app.main import app as fastapp
import app.api
import app.main
from fastapi.testclient import TestClient
from datetime import date
from unittest.mock import patch

import app.models


class ContactsQueryMock:
    def __init__(self):
        self._data = [
            app.models.Contact(
                id=1,
                first_name="John",
                last_name="Doe",
                email="email@m.m",
                phone_number="123456789",
                birth_date=date(1990, 10, 1),
                user_id=1,
            ),
            app.models.Contact(
                id=2,
                first_name="Jane",
                last_name="Doe",
                email="email@m.m",
                phone_number="987654321",
                birth_date=date(1990, 1, 1),
                user_id=1,
            ),
        ]

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self._data


class DBMock:
    def __init__(self):
        pass

    def query(self, model):
        # If type user- return user
        if model == app.models.User:
            return UserQueryMock()
        return ContactsQueryMock()

    def commit(self):
        pass

    def refresh(self, obj):
        pass


class UserQueryMock:
    _data = [
        app.models.User(
            id=1,
            email="user@example.com",
            password="hashed_password",
            avatar="http://example.com/avatar.png",
        )
    ]

    def filter(self, *args, **kwargs):
        self._data = list(filter(lambda x: x.email == args[0].right.value, self._data))
        return self

    def first(self):
        if len(self._data) == 0:
            return None
        return self._data[0]


@pytest.fixture
def client():
    fastapp.dependency_overrides[app.api.get_current_user] = lambda: app.models.User(
        id=1,
        email="user@example.com",
        avatar="http://example.com/avatar.png",
        role="USER",
    )
    fastapp.dependency_overrides[app.api.get_user_contacts] = (
        lambda: ContactsQueryMock()
    )
    fastapp.dependency_overrides[app.db.get_db] = lambda: DBMock()
    with TestClient(fastapp) as c:
        yield c


class RedisMock:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.data = {}
        return cls._instance

    def exists(self, key):
        return key in self.data.keys()

    def hset(self, key, mapping):
        self.data[key] = mapping

    def expire(self, key, seconds):
        pass

    def hget(self, key, field):
        return self.data[key][field]

    def delete(self, key):
        if key in self.data:
            del self.data[key]


def pending_users_db_mock():
    return RedisMock()


def pending_password_resets_db_mock():
    return RedisMock()


def test_get_me(client):
    response = client.get("/me")
    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "email": "user@example.com",
        "avatar_url": "http://example.com/avatar.png",
    }


def test_get_birthdays(client):
    response = client.get("/birthdays")
    assert response.status_code == 200
    assert response.json() is not None


@patch("app.api.pending_users_db", new=pending_users_db_mock)
def test_register(client):
    with patch("app.api.send_email"):
        response = client.post(
            "/register",
            json={
                "email": "userssr@example.com",
                "password": "password",
            },
        )
    print(f"Roma_log: {response.json()}")
    assert "User registered successfully" in response.json().get("message")
    assert response.status_code == 201


@patch("app.api.pending_password_resets_db", new=pending_password_resets_db_mock)
@patch("app.api.current_active_users_db", new=pending_users_db_mock)
def test_authorize_reset(client):
    # Use patched(mocked) db here to test
    pending_password_resets_db_mock()._instance.data["user@example.com"] = {}
    pending_password_resets_db_mock()._instance.data["user@example.com"][
        "code"
    ] = "123456"
    pending_password_resets_db_mock()._instance.data["user@example.com"][
        "password"
    ] = "hashed_password"
    with patch("app.api.send_email"):
        response = client.post(
            "/authorize/reset",
            json={
                "email": "user@example.com",
                "confirmation_code": "123456",
            },
        )
    print(f"Roma: {response.json()}")
    assert response.status_code == 200


def test_updateAvatar_user(client):
    with patch("app.api.send_email"):
        response = client.post(
            "/updateAvatar",
            json={
                "url": "http://example.com/avatar.png",
            },
        )
    print(f"Roma: {response.json()}")
    assert response.status_code == 403
