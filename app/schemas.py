from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional


class ContactCreate(BaseModel):
    """
    ContactCreate schema for creating a new contact.
    """

    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    birth_date: date
    additional_info: Optional[str] = None

    class Config:
        orm_mode = True


class ContactRead(ContactCreate):
    """
    ContactRead schema for reading contact data.
    """

    id: int

    class Config:
        orm_mode = True


class UserCreate(BaseModel):
    """
    UserCreate schema for creating a new user.
    """

    email: EmailStr
    password: str

    class Config:
        orm_mode = True


class UserAuthorize(BaseModel):
    """
    UserAuthorize schema for user authorization.
    """

    email: EmailStr
    confirmation_code: str

    class Config:
        orm_mode = True


class UserUpdateAvatar(BaseModel):
    """
    UserUpdateAvatar schema for updating user avatar.
    """

    url: str

    class Config:
        orm_mode = True


class UserResetPassword(BaseModel):
    """
    UserResetPassword schema for resetting user password.
    """

    email: EmailStr
    new_password: str

    class Config:
        orm_mode = True
