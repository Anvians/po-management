from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os
import httpx

router = APIRouter()
security = HTTPBearer()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/callback/google")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.get("/google/url")
def get_google_auth_url():
    """Get Google OAuth URL for frontend redirect."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID env var.")
    
    scope = "openid email profile"
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scope}"
    )
    return {"url": url}


@router.get("/callback/google")
async def google_callback(code: str):
    """Exchange Google OAuth code for JWT token."""
    try:
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            token_res.raise_for_status()
            google_tokens = token_res.json()

            user_res = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {google_tokens['access_token']}"},
            )
            user_res.raise_for_status()
            user_info = user_res.json()

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google OAuth failed: {str(e)}")

    access_token = create_access_token(
        data={"sub": user_info["email"], "name": user_info.get("name"), "picture": user_info.get("picture")}
    )
    return {"access_token": access_token, "token_type": "bearer", "user": user_info}


@router.post("/demo-login")
def demo_login():
    """
    Demo login endpoint for development/testing.
    Returns a JWT token for a demo user.
    """
    demo_user = {"sub": "demo@po-management.com", "name": "Demo User", "picture": None}
    access_token = create_access_token(data=demo_user)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"email": "demo@po-management.com", "name": "Demo User"}
    }


@router.get("/me")
def get_current_user(payload: dict = Depends(verify_token)):
    return {"email": payload.get("sub"), "name": payload.get("name")}
