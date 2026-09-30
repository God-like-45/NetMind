import time
from typing import Optional, List
from jose import jwt, JWTError
from fastapi import HTTPException, Security
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from passlib.context import CryptContext

SECRET_KEY = "netmind-production-secret-key-do-not-use-in-prod"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/token")

class Role:
    VIEWER = "VIEWER"
    ENGINEER = "ENGINEER"
    INCIDENT_COMMANDER = "INCIDENT_COMMANDER"
    ADMIN = "ADMIN"

class TokenData(BaseModel):
    username: str
    roles: List[str]

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[int] = None):
    to_encode = data.copy()
    expire = time.time() + (expires_delta or ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Security(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        roles: List[str] = payload.get("roles", [])
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, roles=roles)
    except JWTError:
        raise credentials_exception
    return token_data

def require_roles(required_roles: List[str]):
    """Dependency to enforce RBAC."""
    def role_checker(current_user: TokenData = Security(get_current_user)):
        if Role.ADMIN in current_user.roles:
            return current_user # Admins have all access
        for role in required_roles:
            if role in current_user.roles:
                return current_user
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return role_checker
