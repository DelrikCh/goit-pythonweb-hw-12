import jsonpickle as json
import jwt
import os

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from typing import List, Optional
from datetime import date, timedelta, datetime
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from sqlalchemy import extract
from passlib.context import CryptContext
from .cloudinary import upload_image
from .db import (
    get_db,
)
from .email import send_email
from .models import Contact, User
from .redis import RedisDB
from .schemas import (
    ContactCreate,
    ContactRead,
    UserCreate,
    UserUpdateAvatar,
    UserAuthorize,
)

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours in minutes
PENGING_USER_EXPIRATION_TIME = 24 * 60 * 60  # 24 hours in seconds
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def pending_users_db():
    return RedisDB().select(RedisDB.DBs.PENDING_USERS)


def current_active_users_db():
    return RedisDB().select(RedisDB.DBs.CURRENT_ACTIVE_USERS)


# Dependency to verify JWT token
def verify_token(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    payload: dict = Depends(verify_token), db: Session = Depends(get_db)
):
    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = None
    if current_active_users_db().exists(email):
        print("#1")
        user = json.loads(current_active_users_db().get(email))
    if not user:
        print("#2")
        user = db.query(User).filter(User.email == email).first()
        current_active_users_db().set(email, json.dumps(user))
        current_active_users_db().expire(email, ACCESS_TOKEN_EXPIRE_MINUTES * 60)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user


def get_user_contacts(db: Session = Depends(get_db), user_id=Depends(get_current_user)):
    return db.query(Contact).filter(Contact.user_id == user_id.id)


# Create a new contact
@router.post(
    "/contacts/", response_model=ContactRead, status_code=status.HTTP_201_CREATED
)
def create_contact(
    contact: ContactCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    contacts=Depends(get_user_contacts),
):
    # If email exists or phone exists- raise an error
    existing_email = contacts.filter(
        Contact.email == contact.email, Contact.phone_number == contact.phone_number
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contact with this email already exists.",
        )
    db_contact = Contact(
        first_name=contact.first_name,
        last_name=contact.last_name,
        email=contact.email,
        phone_number=contact.phone_number,
        birth_date=contact.birth_date,
        additional_info=contact.additional_info,
        user_id=user.id,
    )
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact


# Get all contacts
@router.get("/contacts/", response_model=List[ContactRead])
def get_contacts(db: Session = Depends(get_db), contacts=Depends(get_user_contacts)):
    return contacts.all()


# Get one contact by id
@router.get("/contacts/{contact_id}", response_model=ContactRead)
def get_contact(
    contact_id: int,
    contacts=Depends(get_user_contacts),
):
    contact = contacts.filter(Contact.id == contact_id).first()
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return contact


# Update an existing contact
@router.put("/contacts/{contact_id}", response_model=ContactRead)
def update_contact(
    contact_id: int,
    contact: ContactCreate,
    db: Session = Depends(get_db),
    contacts=Depends(get_user_contacts),
):
    db_contact = contacts.filter(Contact.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )

    db_contact.first_name = contact.first_name
    db_contact.last_name = contact.last_name
    db_contact.email = contact.email
    db_contact.phone_number = contact.phone_number
    db_contact.birth_date = contact.birth_date
    db_contact.additional_info = contact.additional_info
    db_contact.user_id = contact.user_id

    db.commit()
    db.refresh(db_contact)
    return db_contact


# Delete a contact
@router.delete("/contacts/{contact_id}")
def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    contacts=Depends(get_user_contacts),
):
    db_contact = contacts.filter(Contact.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )

    db.delete(db_contact)
    db.commit()
    return {"message": "Contact deleted successfully"}


# Search contacts by first name, last name, or email
@router.get("/search", response_model=List[ContactRead])
def search_contacts(
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    contacts=Depends(get_user_contacts),
):
    if first_name:
        contacts = contacts.filter(Contact.first_name.ilike(f"%{first_name}%"))
    if last_name:
        contacts = contacts.filter(Contact.last_name.ilike(f"%{last_name}%"))
    if email:
        contacts = contacts.filter(Contact.email.ilike(f"%{email}%"))

    return contacts.all()


# Get contacts with birthdays within the next 7 days
@router.get("/birthdays", response_model=List[ContactRead])
def get_upcoming_birthdays(contacts=Depends(get_user_contacts)):
    today = date.today()
    upcoming_months = [(today + timedelta(days=i)).month for i in range(8)]
    upcoming_days = [(today + timedelta(days=i)).day for i in range(8)]

    result = (
        contacts.filter(
            (extract("month", Contact.birth_date).in_(upcoming_months))
        ).filter(extract("day", Contact.birth_date).in_(upcoming_days))
    ).all()

    return result


# Hash password function
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def generate_confirmation_code():
    return os.urandom(16).hex()


# Registration endpoint
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if the user with the same email already exists
    if pending_users_db().exists(user.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists.",
        )

    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists.",
        )

    # Hash the password
    hashed_password = hash_password(user.password)

    # Create a new user and add to DB
    new_user = User(
        email=user.email,
        password=hashed_password,
        avatar=None,  # Default avatar
    )

    confirmation_code = generate_confirmation_code()

    pending_users_db().hset(
        user.email, mapping={"user": json.dumps(new_user), "code": confirmation_code}
    )
    pending_users_db().expire(user.email, PENGING_USER_EXPIRATION_TIME)
    send_email(
        user.email,
        "Confirm your registration",
        f"Your confirmation code is: {confirmation_code}",
    )

    return {
        "message": "User registered successfully. Please check your email for the confirmation code. You have 24 hours to confirm your registration."
    }


@router.post("/authorize")
def authorize_user(user: UserAuthorize, db: Session = Depends(get_db)):
    if not pending_users_db().exists(user.email):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    code = pending_users_db().hget(user.email, "code")
    if code != user.confirmation_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid confirmation code"
        )
    # If the user is already in the DB, return an error
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists.",
        )
    # Add the user to the DB
    user_data: User = json.loads(pending_users_db().hget(user.email, "user"))
    db.add(user_data)
    db.commit()
    db.refresh(user_data)
    # Remove the user from the pending users DB
    pending_users_db().delete(user.email)
    return {"message": "User authorized successfully"}


# Login endpoint
@router.post("/login")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not pwd_context.verify(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# Function to create a JWT token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=1)  # Default expiry time
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.get("/me", response_model=dict)
@limiter.limit("5/minute")
def get_me(request: Request, current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "avatar_url": current_user.avatar,
    }


@router.post("/updateAvatar")
def update_avatar(
    avatar: UserUpdateAvatar,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    secure_url = upload_image(avatar.url)
    current_user.avatar = secure_url
    db.commit()
    db.refresh(current_user)
    current_active_users_db().set(current_user.email, json.dumps(current_user))
    current_active_users_db().expire(
        current_user.email, ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return {"message": "Avatar updated successfully"}
