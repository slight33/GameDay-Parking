# This Code Was Ai Generated
 # Standard Utilities: Sets up environment variables (os), text pattern matching (re), date formatting (datetime), file path management (Path), and advanced type hints (typing).
 # Security & Authentication: Imports bcrypt for password hashing and jwt for generating secure JSON Web Tokens.
 # FastAPI Ecosystem: Pulls in components to create the web app, manage cross-origin restrictions (CORS), and protect routes.
 # Data Validation & ORM: Imports pydantic to enforce data types and sqlalchemy to manage database sessions.
import os, re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal

import bcrypt, jwt
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from .models import SessionLocal, User, init_db
from fastapi.staticfiles import StaticFiles
# Environment Constants: Sets a secret key for security signatures.
# CORS Settings: Enables broad Cross-Origin Resource Sharing (*) so external frontend clients can communicate with the backend.
# Auth Protocol: Instantiates HTTPBearer to intercept incoming Authorization: Bearer <token> request headers.

SECRET = os.environ.get("JWT_SECRET", "dev-only-change-me")
STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="gamedayParking")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])  # tighten in prod
app.mount("/static", StaticFiles(directory=STATIC), name="static")
bearer = HTTPBearer(auto_error=False)
# App Startup: Triggers init_db() to automatically spin up or verify your database tables when the web server first boots.
# Session Lifecycle: get_db() yields a temporary database connection block. Using Python's context manager (with), it guarantees 
# the session automatically closes after a request finishes.

@app.on_event("startup")
def _startup(): 
    init_db()

def get_db():
    with SessionLocal() as s:
        yield s


DB = Annotated[Session, Depends(get_db)]
# make_token: Packages a user's unique ID (uid) into a secure JSON Web Token that expires exactly 7 days after issue.
# ---------- auth ----------
def make_token(uid: str) -> str:
    return jwt.encode({"sub": uid, "exp": datetime.now(timezone.utc) + timedelta(days=7)}, SECRET, "HS256")

# current_user: Intercepts incoming bearer credentials, decodes the JWT using the SECRET key, and grabs the user's ID. If the token is fake, expired,
# or doesn't map to a real database user, it immediately stops execution and drops a 401 Unauthorized error.
def current_user(db: DB, cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    try:
        uid = jwt.decode(cred.credentials, SECRET, ["HS256"])["sub"]
    except Exception:
        raise HTTPException(401, "Sign in required.")
    u = db.get(User, uid)
    if not u: raise HTTPException(401, "Sign in required.")
    return u
# Me Shortcut: Serves as a reusable dependency injection tag. Any API route featuring u: Me will automatically enforce authentication before running.
Me = Annotated[User, Depends(current_user)]

#  SignupIn: Validates the payload when a new user registers. It requires name, username, phone, and a password at least 8 characters long, plus a valid formatted email via Pydantic's EmailStr.
class SignupIn(BaseModel):
    name: str = Field(min_length=1); 
    username: str = Field(min_length=1)
    email: EmailStr; 
    phone: str = Field(min_length=1); 
    password: str = Field(min_length=8)

# LoginIn: Simple schema expecting a username and password for logging in.
class LoginIn(BaseModel):
    username: str; 
    password: str

# UserOut: Defines what user data is returned to the client (hiding sensitive fields like password hashes).
class UserOut(BaseModel):
    id: str; 
    name: str; 
    username: str; 
    email: str; 
    phone: str; 
    role: str; 
    address: str | None
    # allows it to read data straight from a SQLAlchemy database model instance:
    model_config = {"from_attributes": True}

# TokenOut: Wraps an authentication token string and the associated UserOut object together in the response.
class TokenOut(BaseModel):
    token: str; 
    user: UserOut

# Queries the database to make sure neither the username nor the email already exists. If found, it raises a 409 Conflict HTTP error.
# Strips whitespace and lowercases the username and email so logins are case-insensitive and clean.
@app.post("/auth/signup", response_model=TokenOut, status_code=201)
def signup(d: SignupIn, db: DB):
    if db.query(User).filter(User.username == d.username.strip().lower()).first():
        raise HTTPException(409, "That username is taken. Choose another.")
    if db.query(User).filter(User.email == d.email.lower()).first():
        raise HTTPException(409, "An account with that email already exists.")
    #Uses bcrypt with a generated salt to safely hash the plaintext password before saving it.
    u = User(name=d.name.strip(), username=d.username.strip().lower(), email=d.email.lower(),
             phone=d.phone.strip(), pw_hash=bcrypt.hashpw(d.password.encode(), bcrypt.gensalt()).decode())
    # Adds the new User object to the session and commits it
    db.add(u); 
    db.commit()
    return TokenOut(token=make_token(u.id), user=u)


@app.post("/auth/login", response_model=TokenOut)
def login(d: LoginIn, db: DB):
    # Finds the user in the database by matching the lowercased, stripped username.
    u = db.query(User).filter(User.username == d.username.strip().lower()).first()
    # Checks if the user exists and verifies the incoming password against the stored bcrypt hash.
    if not u or not bcrypt.checkpw(d.password.encode(), u.pw_hash.encode()):
        #If the username or password fails to match, it throws a 401 Unauthorized error with a generic message.
        raise HTTPException(401, "Username or password doesn't match. Check both and try again.")
    # Token Issuance: If valid, it returns a new auth token and user profile via TokenOut.
    return TokenOut(token=make_token(u.id), user=u)

#Fetches the currently authenticated user's profile at GET /me.
@app.get("/me", response_model=UserOut)
def me(u: Me): 
    return u


# ---------- pages ----------
#Serves frontend HTML files for the root, login, and registration pages.
@app.get("/", include_in_schema=False)
@app.get("/login", include_in_schema=False)
def login_page():
    return FileResponse(STATIC / "login.html")

@app.get("/register", include_in_schema=False)
def register_page():
    return FileResponse(STATIC / "register.html")
