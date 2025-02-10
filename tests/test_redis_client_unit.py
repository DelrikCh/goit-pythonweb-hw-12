import pytest
from app.redis_client import RedisDB
from unittest.mock import patch, MagicMock


@pytest.fixture
def redis_mock():
    with patch("redis.Redis", MagicMock()) as mock:
        yield mock


def test_singleton_instance(redis_mock):
    instance1 = RedisDB()
    instance2 = RedisDB()
    assert instance1 is instance2


def test_redis_clients_initialization(redis_mock):
    instance = RedisDB()
    for db in RedisDB.DBs:
        assert db in instance._clients
        assert isinstance(instance._clients[db], MagicMock)


def test_select_method(redis_mock):
    instance = RedisDB()
    for db in RedisDB.DBs:
        client = instance.select(db)
        assert client is instance._clients[db]
