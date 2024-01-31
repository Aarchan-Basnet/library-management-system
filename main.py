from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import Session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Annotated, Optional, List
from datetime import date

#setup sqlite database

db_url = "sqlite:///./database.db"
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

#create models for database

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    membership_date = Column(String)
    borrowed_books = relationship("BorrowedBooks", back_populates="user")

class Book(Base):
    __tablename__ = "books"
    book_id = Column(Integer, primary_key=True)
    title = Column(String)
    isbn = Column(String)
    published_date = Column(String)
    genre = Column(String)
    details = relationship("BookDetails", back_populates="book")
    borrowed_books = relationship("BorrowedBooks", back_populates="book")

class BookDetails(Base):
    __tablename__ = "book_details"
    details_id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey("books.book_id"))
    number_of_pages = Column(Integer)
    publisher = Column(String)
    language = Column(String)
    book = relationship("Book", back_populates="details")

class BorrowedBooks(Base):
    __tablename__ = "borrowed_books"
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    book_id = Column(Integer, ForeignKey("books.book_id"), unique=True)
    borrow_date = Column(String)
    return_date = Column(String)
    user = relationship("User", back_populates="borrowed_books")
    book = relationship("Book", back_populates="borrowed_books")

# Pydantic models for validation

class UserBase(BaseModel):
    name: str
    email: str
    membership_date: str

class BookBase(BaseModel):
    title: str
    isbn: str
    published_date: str
    genre: str

class BookDetailsUpdate(BaseModel):
    number_of_pages: Optional[int]
    publisher: Optional[str]
    language: Optional[str]


# create all tables and columns
Base.metadata.create_all(bind=engine)

#create fastapi app
app = FastAPI()

# dependency to connect to database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

#endpoints

@app.get("/")
def home():
    message = {
        "detail": "Welcome to Library Management System."
    }
    return message

@app.post("/user/create/")
def create_user(user: UserBase, db: db_dependency):
    db_user = User(name=user.name,
                   email=user.email,
                   membership_date=user.membership_date
                   )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/user/all/")
def all_users_list(db: db_dependency):
    result = db.query(User).all()
    return result

@app.get("/user/{user_id}/")
def get_user_by_id(user_id: int, db: db_dependency):
    result = db.query(User).filter(User.user_id == user_id).first()
    if not result:
        raise HTTPException(status_code=404,
                            detail="User not founnd.")
    return result

@app.post("/book/create/")
def create_book(book: BookBase, db: db_dependency):
    db_book = Book(title=book.title,
                   isbn=book.isbn,
                   published_date=book.published_date,
                   genre=book.genre
                   )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

@app.get("/book/all/")
def all_book_list(db: db_dependency):
    result = db.query(Book).all()
    return result

@app.get("/book/{book_id}/")
def get_book_by_id(book_id: int, db: db_dependency):
    result = db.query(Book).filter(Book.book_id == book_id).first()
    if not result:
        raise HTTPException(status_code=404,
                            detail="Book not found.")
    return result

@app.put("/book/{book_id}/details/")
def update_book_details(book_id: int, details: BookDetailsUpdate, db: db_dependency):
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(status_code=404,
                            detail="Book not found.")

    existing_details = db.query(BookDetails).filter(BookDetails.book_id == book_id).first()
    if existing_details:
        existing_details.number_of_pages = details.number_of_pages
        existing_details.publisher = details.publisher
        existing_details.language = details.language
    else:
        # details.book_id = book_id
        new_details = BookDetails(**details.dict(), book_id=book_id)
        db.add(new_details)

    db.commit()
    db.refresh(existing_details)
    return existing_details

@app.post("/borrowed-books/borrow/")
def borrow_book(user_id: int, book_id: int, db: db_dependency):
    user = db.query(User).filter(User.user_id == user_id).first()
    book = db.query(Book).filter(Book.book_id == book_id).first()

    if user is None or book is None:
        raise HTTPException(status_code=404,
                            detail="User or Book not vfound.")

    borrowed_book = BorrowedBooks(user_id=user_id, book_id=book_id, borrow_date=date.today())
    db.add(borrowed_book)
    db.commit()
    db.refresh(borrowed_book)
    return borrowed_book

@app.put("/borrowed-books/return/")
def return_book(user_id: int, book_id: int, db: db_dependency):
    borrowed_book = (db.query(BorrowedBooks).
                     filter(BorrowedBooks.user_id == user_id,
                            BorrowedBooks.book_id == book_id)
                     .first())

    if not borrowed_book:
        raise HTTPException(status_code=404,
                            detail="Borrowed book not found.")

    borrowed_book.return_date = date.today()
    db.commit()
    db.refresh(borrowed_book)
    return borrowed_book

@app.get("/borrowed-books/all/")
def list_all_borrowed_books(db: db_dependency):
    result = db.query(BorrowedBooks).all()
    return result