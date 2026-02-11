"""
Authentication endpoints for Todo Application
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select
from typing import Optional
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import os
import hashlib

from app.models.user import User, UserCreate, UserResponse, Token, TokenData
from app.db.database import get_session

router = APIRouter()

# Password hashing - using pbkdf2 instead of bcrypt to avoid installation issues
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "argon2"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-and-long-random-string-here-change-this-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def authenticate_user(session: Session, email: str, password: str) -> Optional[User]:
    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except jwt.PyJWTError:
        raise credentials_exception

    statement = select(User).where(User.email == token_data.email)
    user = session.exec(statement).first()

    if user is None:
        raise credentials_exception
    return user

class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/signup", response_model=Token)
@router.post("/register", response_model=Token)
def signup(user_data: RegisterRequest, session: Session = Depends(get_session)):
    # Check if user already exists
    statement = select(User).where(User.email == user_data.email)
    existing_user = session.exec(statement).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash the password
    hashed_password = get_password_hash(user_data.password)

    # Create new user
    db_user = User(
        email=user_data.email,
        password_hash=hashed_password
    )

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )

    # Create user response
    user_response = UserResponse(
        id=db_user.id,
        email=db_user.email,
        created_at=db_user.created_at,
        is_active=db_user.is_active
    )

    return Token(access_token=access_token, token_type="bearer", user=user_response)

@router.post("/login", response_model=Token)
def login(login_request: LoginRequest, session: Session = Depends(get_session)):
    user = authenticate_user(session, login_request.email, login_request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    user_response = UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
        is_active=user.is_active
    )

    return Token(access_token=access_token, token_type="bearer", user=user_response)