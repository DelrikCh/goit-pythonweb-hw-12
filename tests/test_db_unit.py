import pytest
from unittest.mock import patch, MagicMock
from app.db import get_db


@pytest.fixture
def mock_db_session():
    """Fixture to provide a mocked database session."""
    return MagicMock()


@pytest.fixture
def mock_session_local(mock_db_session):
    """Fixture to mock SessionLocal so get_db() returns the mock session."""
    with patch("app.db.SessionLocal", return_value=mock_db_session):
        yield mock_db_session


def test_get_db(mock_session_local):
    """Test that get_db() yields the mocked session."""
    db_session = next(get_db())
    assert db_session is mock_session_local
    db_session.close.assert_called_once()
