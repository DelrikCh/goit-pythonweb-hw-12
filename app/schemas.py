from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional


class ContactCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: str
    birth_date: date
    additional_info: Optional[str] = None

    class Config:
        orm_mode = True


class ContactRead(ContactCreate):
    id: int

    class Config:
        orm_mode = True


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    class Config:
        orm_mode = True
