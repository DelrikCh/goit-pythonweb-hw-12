import jsonpickle as json
import jwt
import os

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from typing import List, Optional
from datetime import date, timedelta, datetime
from dotenv import load_dotenv
from functools import wraps
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from sqlalchemy import extract
from passlib.context import CryptContext
from app.cloudinary_utils import upload_image
from app.db import (
    get_db,
)
from app.email_utils import send_email
from app.models import Contact, User
from app.redis_client import RedisDB
from app.schemas import (
    ContactCreate,
    ContactRead,
    UserCreate,
    UserUpdateAvatar,
    UserAuthorize,
    UserResetPassword,
)

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours in minutes
PENGING_USER_EXPIRATION_TIME = 24 * 60 * 60  # 24 hours in seconds
PENDING_PASSWORD_RESET_EXPIRATION_TIME = 30 * 60  # 30 minutes in seconds
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def pending_users_db():
    return RedisDB().select(RedisDB.DBs.PENDING_USERS)


def current_active_users_db():
    return RedisDB().select(RedisDB.DBs.CURRENT_ACTIVE_USERS)


def pending_password_resets_db():
    return RedisDB().select(RedisDB.DBs.PENDING_PASSWORD_RESETS)


# Dependency to verify JWT token
def verify_token(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    """
    Verify the JWT token and return the payload

    Args:
        db (Session): The database session
        token (str): The JWT token
    """
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
    """
    Get the current user from the JWT token

    Args:
        payload (dict): The JWT token payload
        db (Session): The database session
    """
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


def get_user_contacts(
    db: Session = Depends(get_db), user_id: User = Depends(get_current_user)
):
    """
    Get the contacts for the current user

    Args:
        db (Session): The database session
        user (User): The user
    """
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
    """
    Create a new contact

    Args:
        contact (ContactCreate): The contact to create
        db (Session): The database session
        user (User): The user
        contacts (List[Contact]): The contacts for the user
    """
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
    """
    Get all contacts for the current user

    Args:
        db (Session): The database session
        contacts (List[Contact]): The contacts for the user
    """
    return contacts.all()


# Get one contact by id
@router.get("/contacts/{contact_id}", response_model=ContactRead)
def get_contact(
    contact_id: int,
    contacts=Depends(get_user_contacts),
):
    """
    Get a contact by id

    Args:
        contact_id (int): The contact id
        contacts (List[Contact]): The contacts for the user
    """
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
    """
    Update an existing contact

    Args:
        contact_id (int): The contact id
        contact (ContactCreate): The contact to update
        db (Session): The database session
        contacts (List[Contact]): The contacts for the user
    """
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
    """
    Delete a contact

    Args:
        contact_id (int): The contact id
        db (Session): The database session
        contacts (List[Contact]): The contacts for the user
    """
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
    """
    Search contacts by first name, last name, or email

    Args:
        first_name (Optional[str]): The first name to search for
        last_name (Optional[str]): The last name to search for
        email (Optional[str]): The email to search for
        contacts (List[Contact]): The contacts for the user
    """
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
    """
    Get contacts with birthdays within the next 7 days

    Args:
        contacts (List[Contact]): The contacts for the user
    """
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


def admin_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get current_user from the arguments
        current_user: User = kwargs.get("current_user")

        # Check if the current_user is an admin
        if current_user is None or current_user.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for non-admin users",
            )

        # Call the actual route function
        return func(*args, **kwargs)

    return wrapper


# Registration endpoint
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user

    Args:
        user (UserCreate): The user to register
        db (Session): The database session
    """
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
        # TODO: Consider using privilege level in a future, or scopes instead of role="USER"|"ADMIN"
        role="USER",  # Default role
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


@router.post("/authorize/register")
def authorize_user(user: UserAuthorize, db: Session = Depends(get_db)):
    """
    Authorize a user

    Args:
        user (UserAuthorize): The user to authorize
        db (Session): The database session
    """
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


@router.post("/authorize/reset")
def authorize_reset(user: UserAuthorize, db: Session = Depends(get_db)):
    """
    Authorize a user for password reset

    Args:
        user (UserAuthorize): The user data to authorize
        db (Session): The database session
    """
    if not pending_password_resets_db().exists(user.email):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    code = pending_password_resets_db().hget(user.email, "code")
    if code != user.confirmation_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid confirmation code"
        )
    # If the user is not in the DB, return an error
    existing_user = db.query(User).filter(User.email == user.email).first()
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    # Update the user's password
    hashed_password = pending_password_resets_db().hget(user.email, "password")
    existing_user.password = hashed_password
    db.commit()
    db.refresh(existing_user)
    # Remove the user from the pending users DB
    pending_password_resets_db().delete(user.email)
    # Drop it from the current active users DB for security reasons
    current_active_users_db().delete(user.email)
    return {"message": "Password reset successfully"}


# Login endpoint
@router.post("/login")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Login a user and return an access token

    Args:
        form_data (OAuth2PasswordRequestForm): The form with login data
        db (Session): The database session
    """
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
    """
    Create a JWT token

    Args:
        data (dict): The data to encode in the token
        expires_delta (timedelta): The expiration time of the token
    """
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
def get_me(request: Request, user: User = Depends(get_current_user)):
    """
    Get the user info

    Args:
        request (Request): The request object
        current_user (User): The current user
    """
    return {
        "id": user.id,
        "email": user.email,
        "avatar_url": user.avatar,
    }


@router.post("/updateAvatar")
@admin_only
def update_avatar(
    avatar: UserUpdateAvatar,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Update the user's avatar

    Args:
        avatar (UserUpdateAvatar): The avatar to update
        db (Session): The database session
        user (User): The user
    """
    secure_url = upload_image(avatar.url)
    user.avatar = secure_url
    db.commit()
    db.refresh(user)
    current_active_users_db().set(user.email, json.dumps(user))
    current_active_users_db().expire(user.email, ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return {"message": "Avatar updated successfully"}


@router.post("/resetPassword")
def reset_password(
    user: UserResetPassword,
    db: Session = Depends(get_db),
):
    """
    Reset the user's password

    Args:
        user (UserResetPassword): The user to reset the password for
        db (Session): The database session
    """
    # Check if the user with the same email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email does not exist.",
        )
    # Check if the user has a pending password reset request
    if pending_password_resets_db().exists(user.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Password reset request already exists.",
        )

    hashed_password = hash_password(user.new_password)
    confirmation_code = generate_confirmation_code()
    pending_password_resets_db().hset(
        user.email, mapping={"code": confirmation_code, "password": hashed_password}
    )
    pending_password_resets_db().expire(
        user.email, PENDING_PASSWORD_RESET_EXPIRATION_TIME
    )

    send_email(
        user.email,
        "Confirm your password reset",
        f"Your confirmation code is: {confirmation_code}",
    )

    return {
        "message": "Password reset request created successfully. Please check your email for the confirmation code. You have 30 minutes to confirm your password reset."
    }
