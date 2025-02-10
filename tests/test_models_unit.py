import pytest
from app.models import Base, Contact, User
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup the database for testing
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_create_user(db_session):
    user = User(email="test@example.com", password="password123")
    db_session.add(user)
    db_session.commit()
    assert user.id is not None


def test_create_contact(db_session):
    user = User(email="test2@example.com", password="password123")
    db_session.add(user)
    db_session.commit()

    contact = Contact(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone_number="1234567890",
        birth_date=date(1990, 1, 1),
        user_id=user.id,
    )
    db_session.add(contact)
    db_session.commit()
    assert contact.id is not None


def test_contact_belongs_to_user(db_session):
    user = User(email="test3@example.com", password="password123")
    db_session.add(user)
    db_session.commit()

    contact = Contact(
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        phone_number="0987654321",
        birth_date=date(1992, 2, 2),
        user_id=user.id,
    )
    db_session.add(contact)
    db_session.commit()

    retrieved_contact = db_session.query(Contact).filter_by(id=contact.id).first()
    assert retrieved_contact.user_id == user.id


def test_optional_fields(db_session):
    user = User(
        email="test4@example.com",
        password="password123",
        avatar="avatar.png",
        role="ADMIN",
    )
    db_session.add(user)
    db_session.commit()

    contact = Contact(
        first_name="Alice",
        last_name="Smith",
        email="alice.smith@example.com",
        phone_number="1122334455",
        birth_date=date(1985, 5, 5),
        additional_info="Friend from college",
        user_id=user.id,
    )
    db_session.add(contact)
    db_session.commit()

    retrieved_contact = db_session.query(Contact).filter_by(id=contact.id).first()
    assert retrieved_contact.additional_info == "Friend from college"
    assert user.avatar == "avatar.png"
    assert user.role == "ADMIN"
