import pytest
from unittest.mock import patch, ANY
from app.email_utils import send_email


@pytest.fixture
def email_data():
    return {
        "receiver_email": "test@example.com",
        "subject": "Test Subject",
        "body": "This is a test email body.",
    }


@pytest.fixture
def mock_smtp(mocker):
    return mocker.patch("app.email_utils.smtplib.SMTP")


@pytest.fixture
def mock_getenv(mocker):
    return mocker.patch(
        "app.email_utils.os.getenv", side_effect=["sender@example.com", "password123"]
    )


def test_send_email(mock_getenv, mock_smtp, email_data):
    mock_server = mock_smtp.return_value

    send_email(email_data["receiver_email"], email_data["subject"], email_data["body"])

    mock_getenv.assert_any_call("ENV_EMAIL")
    mock_getenv.assert_any_call("ENV_EMAIL_PASSWORD")
    mock_smtp.assert_called_with("smtp.gmail.com", 587)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("sender@example.com", "password123")
    mock_server.sendmail.assert_called_once_with(
        "sender@example.com", email_data["receiver_email"], ANY
    )
    mock_server.quit.assert_called_once()
