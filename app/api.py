from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import date, timedelta
from .models import Contact
from .schemas import ContactCreate, ContactRead
from sqlalchemy.orm import Session
from sqlalchemy import extract
from .db import (
    get_db,
)

router = APIRouter()


# Create a new contact
@router.post("/contacts/", response_model=ContactRead)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    db_contact = Contact(
        first_name=contact.first_name,
        last_name=contact.last_name,
        email=contact.email,
        phone_number=contact.phone_number,
        birth_date=contact.birth_date,
        additional_info=contact.additional_info,
    )
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact


# Get all contacts
@router.get("/contacts/", response_model=List[ContactRead])
def get_contacts(db: Session = Depends(get_db)):
    contacts = db.query(Contact).all()
    return contacts


# Get one contact by id
@router.get("/contacts/{contact_id}", response_model=ContactRead)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


# Update an existing contact
@router.put("/contacts/{contact_id}", response_model=ContactRead)
def update_contact(
    contact_id: int, contact: ContactCreate, db: Session = Depends(get_db)
):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    db_contact.first_name = contact.first_name
    db_contact.last_name = contact.last_name
    db_contact.email = contact.email
    db_contact.phone_number = contact.phone_number
    db_contact.birth_date = contact.birth_date
    db_contact.additional_info = contact.additional_info

    db.commit()
    db.refresh(db_contact)
    return db_contact


# Delete a contact
@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    db.delete(db_contact)
    db.commit()
    return {"message": "Contact deleted successfully"}


# Search contacts by first name, last name, or email
@router.get("/search", response_model=List[ContactRead])
def search_contacts(
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Contact)

    if first_name:
        query = query.filter(Contact.first_name.ilike(f"%{first_name}%"))
    if last_name:
        query = query.filter(Contact.last_name.ilike(f"%{last_name}%"))
    if email:
        query = query.filter(Contact.email.ilike(f"%{email}%"))

    contacts = query.all()
    return contacts


# Get contacts with birthdays within the next 7 days
@router.get("/birthdays", response_model=List[ContactRead])
def get_upcoming_birthdays(db: Session = Depends(get_db)):
    today = date.today()
    upcoming_months = [(today + timedelta(days=i)).month for i in range(8)]
    upcoming_days = [(today + timedelta(days=i)).day for i in range(8)]

    contacts = (
        db.query(Contact)
        .filter((extract("month", Contact.birth_date).in_(upcoming_months)))
        .filter(extract("day", Contact.birth_date).in_(upcoming_days))
    ).all()

    return contacts
