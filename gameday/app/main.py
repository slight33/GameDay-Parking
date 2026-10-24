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

SECRET = os.environ.get("JWT_SECRET", "dev-only-change-me")
STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="gamedayParking")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])  # tighten in prod
app.mount("/static", StaticFiles(directory=STATIC), name="static")
bearer = HTTPBearer(auto_error=False)

@app.on_event("startup")
def _startup(): 
    init_db()

def get_db():
    with SessionLocal() as s:
        yield s


DB = Annotated[Session, Depends(get_db)]

# ---------- auth ----------
def make_token(uid: str) -> str:
    return jwt.encode({"sub": uid, "exp": datetime.now(timezone.utc) + timedelta(days=7)}, SECRET, "HS256")

def current_user(db: DB, cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    try:
        uid = jwt.decode(cred.credentials, SECRET, ["HS256"])["sub"]
    except Exception:
        raise HTTPException(401, "Sign in required.")
    u = db.get(User, uid)
    if not u: raise HTTPException(401, "Sign in required.")
    return u
Me = Annotated[User, Depends(current_user)]



class SignupIn(BaseModel):
    name: str = Field(min_length=1); 
    username: str = Field(min_length=1)
    email: EmailStr; phone: str = Field(min_length=1); 
    password: str = Field(min_length=8)

class LoginIn(BaseModel):
    username: str; 
    password: str

class UserOut(BaseModel):
    id: str; 
    name: str; 
    username: str; 
    email: str; 
    phone: str; 
    role: str; 
    address: str | None
    model_config = {"from_attributes": True}

class TokenOut(BaseModel):
    token: str; 
    user: UserOut

@app.post("/auth/signup", response_model=TokenOut, status_code=201)
def signup(d: SignupIn, db: DB):
    if db.query(User).filter(User.username == d.username.strip().lower()).first():
        raise HTTPException(409, "That username is taken. Choose another.")
    if db.query(User).filter(User.email == d.email.lower()).first():
        raise HTTPException(409, "An account with that email already exists.")
    u = User(name=d.name.strip(), username=d.username.strip().lower(), email=d.email.lower(),
             phone=d.phone.strip(), pw_hash=bcrypt.hashpw(d.password.encode(), bcrypt.gensalt()).decode())
    db.add(u); 
    db.commit()
    return TokenOut(token=make_token(u.id), user=u)

@app.post("/auth/login", response_model=TokenOut)
def login(d: LoginIn, db: DB):
    u = db.query(User).filter(User.username == d.username.strip().lower()).first()
    if not u or not bcrypt.checkpw(d.password.encode(), u.pw_hash.encode()):
        raise HTTPException(401, "Username or password doesn't match. Check both and try again.")
    return TokenOut(token=make_token(u.id), user=u)

@app.get("/me", response_model=UserOut)
def me(u: Me): 
    return u


# ---------- pages ----------

@app.get("/", include_in_schema=False)
@app.get("/login", include_in_schema=False)
def login_page():
    return FileResponse(STATIC / "login.html")

@app.get("/register", include_in_schema=False)
def register_page():
    return FileResponse(STATIC / "register.html")
