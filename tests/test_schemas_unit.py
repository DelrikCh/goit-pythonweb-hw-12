import pytest
from pydantic import ValidationError
from datetime import date
from app.schemas import (
    ContactCreate,
    ContactRead,
    UserCreate,
    UserAuthorize,
    UserUpdateAvatar,
    UserResetPassword,
)


def test_contact_create_valid():
    contact = ContactCreate(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone_number="1234567890",
        birth_date=date(1990, 1, 1),
        additional_info="Some info",
    )
    assert contact.first_name == "John"
    assert contact.last_name == "Doe"
    assert contact.email == "john.doe@example.com"
    assert contact.phone_number == "1234567890"
    assert contact.birth_date == date(1990, 1, 1)
    assert contact.additional_info == "Some info"


def test_contact_create_invalid_email():
    with pytest.raises(ValidationError):
        ContactCreate(
            first_name="John",
            last_name="Doe",
            email="not-an-email",
            phone_number="1234567890",
            birth_date=date(1990, 1, 1),
        )


def test_contact_read_valid():
    contact = ContactRead(
        id=1,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone_number="1234567890",
        birth_date=date(1990, 1, 1),
        additional_info="Some info",
    )
    assert contact.id == 1


def test_user_create_valid():
    user = UserCreate(email="user@example.com", password="securepassword")
    assert user.email == "user@example.com"
    assert user.password == "securepassword"


def test_user_create_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", password="securepassword")


def test_user_authorize_valid():
    user = UserAuthorize(email="user@example.com", confirmation_code="123456")
    assert user.email == "user@example.com"
    assert user.confirmation_code == "123456"


def test_user_update_avatar_valid():
    user = UserUpdateAvatar(url="http://example.com/avatar.png")
    assert user.url == "http://example.com/avatar.png"


def test_user_reset_password_valid():
    user = UserResetPassword(email="user@example.com", new_password="newsecurepassword")
    assert user.email == "user@example.com"
    assert user.new_password == "newsecurepassword"
