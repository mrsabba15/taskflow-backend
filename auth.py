# ============================================
# JWT AUTHENTICATION
# ============================================

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from dotenv import load_dotenv
import os
import jwt


# ============================================
# LOAD ENVIRONMENT VARIABLES
# ============================================

# Read variables from .env
load_dotenv()


# Get JWT settings from .env
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


# Make sure SECRET_KEY exists
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is missing from .env")


# ============================================
# OAUTH2 CONFIGURATION
# ============================================

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/login"
)


# ============================================
# VERIFY CURRENT USER
# ============================================

def get_current_user(
    token: str = Depends(oauth2_scheme)
):
    try:

        # Decode and verify JWT token
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        # Get user information
        user_id = payload.get("user_id")
        username = payload.get("username")

        # Check required data
        if user_id is None or username is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        return {
            "user_id": user_id,
            "username": username
        }

    except jwt.InvalidTokenError:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )