# ============================================
# USERS ROUTES
# ============================================

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm

import os
import secrets
import aiosmtplib
from email.message import EmailMessage

from database import get_db
from models import User
from schemas import (
    UserCreate,
    UserResponse,
    TokenResponse
)

from pwdlib import PasswordHash

from auth import (
    get_current_user,
    SECRET_KEY,
    ALGORITHM
)

import jwt
from datetime import datetime, timedelta, timezone


# ============================================
# CREATE ROUTER
# ============================================

router = APIRouter()


# ============================================
# PASSWORD HASHING
# ============================================

password_hash = PasswordHash.recommended()


# ============================================
# SEND OTP EMAIL
# ============================================

async def send_otp_email(
    to_email: str,
    username: str,
    otp: str
):

    # Get email settings from Environment Variables
    smtp_host = os.getenv("EMAIL_HOST")
    smtp_port = int(os.getenv("EMAIL_PORT", "587"))
    smtp_username = os.getenv("EMAIL_USERNAME")
    smtp_password = os.getenv("EMAIL_PASSWORD")

    # Check email configuration
    if not smtp_host:
        raise RuntimeError("EMAIL_HOST is missing")

    if not smtp_username:
        raise RuntimeError("EMAIL_USERNAME is missing")

    if not smtp_password:
        raise RuntimeError("EMAIL_PASSWORD is missing")

    # Create email
    message = EmailMessage()

    message["From"] = smtp_username
    message["To"] = to_email
    message["Subject"] = "TaskFlow - Email Verification OTP"

    message.set_content(
        f"""
Hello {username},

Welcome to TaskFlow!

Your email verification OTP is:

{otp}

This OTP will expire in 10 minutes.

If you did not create this account, you can ignore this email.

Regards,
TaskFlow Team
"""
    )

    # Send email through Gmail SMTP
    await aiosmtplib.send(
        message,
        hostname=smtp_host,
        port=smtp_port,
        username=smtp_username,
        password=smtp_password,
        start_tls=True
    )


# ============================================
# 1. REGISTER + SEND OTP
# ============================================

@router.post("/register")
async def register(
    user_data: UserCreate,
    db=Depends(get_db)
):

    # ----------------------------------------
    # Check existing username
    # ----------------------------------------

    existing_user = db.query(User).filter(
        User.username == user_data.username
    ).first()

    if existing_user and existing_user.is_verified:
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    # ----------------------------------------
    # Check existing email
    # ----------------------------------------

    existing_email = db.query(User).filter(
        User.email == user_data.email
    ).first()

    if existing_email and existing_email.is_verified:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    # ----------------------------------------
    # Generate 6-digit OTP
    # ----------------------------------------

    otp = f"{secrets.randbelow(1000000):06d}"

    # OTP expires after 10 minutes
    otp_expiry = (
        datetime.now(timezone.utc)
        + timedelta(minutes=10)
    ).isoformat()

    # ----------------------------------------
    # Hash password
    # ----------------------------------------

    hashed_password = password_hash.hash(
        str(user_data.password)
    )

    # ----------------------------------------
    # Update existing unverified user
    # ----------------------------------------

    if existing_user:

        existing_user.email = user_data.email
        existing_user.password = hashed_password
        existing_user.otp = otp
        existing_user.otp_expiry = otp_expiry

        user = existing_user

    # ----------------------------------------
    # Create new user
    # ----------------------------------------

    else:

        user = User(
            username=user_data.username,
            email=user_data.email,
            password=hashed_password,
            is_verified=False,
            otp=otp,
            otp_expiry=otp_expiry
        )

        db.add(user)

    # Save user
    db.commit()
    db.refresh(user)

    # ----------------------------------------
    # SEND OTP TO USER EMAIL
    # ----------------------------------------

    try:

        await send_otp_email(
            to_email=user_data.email,
            username=user_data.username,
            otp=otp
        )

    except Exception as error:

        print("Email sending failed:", error)

        raise HTTPException(
            status_code=500,
            detail="Unable to send OTP email. Please try again."
        )

    return {
        "message": "OTP sent successfully to your email."
    }


# ============================================
# 2. VERIFY OTP
# ============================================

@router.post("/verify-otp")
def verify_otp(
    username: str,
    otp: str,
    db=Depends(get_db)
):

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if user.is_verified:

        raise HTTPException(
            status_code=400,
            detail="Account is already verified"
        )

    # Check OTP
    if user.otp != otp:

        raise HTTPException(
            status_code=400,
            detail="Invalid OTP"
        )

    # ----------------------------------------
    # Check OTP expiry
    # ----------------------------------------

    expiry_time = datetime.fromisoformat(
        user.otp_expiry
    )

    if datetime.now(timezone.utc) > expiry_time:

        raise HTTPException(
            status_code=400,
            detail="OTP has expired"
        )

    # ----------------------------------------
    # Verify account
    # ----------------------------------------

    user.is_verified = True

    # Remove OTP after verification
    user.otp = None
    user.otp_expiry = None

    db.commit()

    return {
        "message": "Email verified successfully. Account created."
    }


# ============================================
# 3. LOGIN
# ============================================

@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db=Depends(get_db)
):

    # ----------------------------------------
    # Find user
    # ----------------------------------------

    user = db.query(User).filter(
        User.username == form_data.username
    ).first()

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # ----------------------------------------
    # Check email verification
    # ----------------------------------------

    if not user.is_verified:

        raise HTTPException(
            status_code=403,
            detail="Please verify your email before login"
        )

    # ----------------------------------------
    # Verify password
    # ----------------------------------------

    password_correct = password_hash.verify(
        form_data.password,
        user.password
    )

    if not password_correct:

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # ----------------------------------------
    # JWT PAYLOAD
    # ----------------------------------------

    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=30)
    }

    # ----------------------------------------
    # CREATE TOKEN
    # ----------------------------------------

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# ============================================
# 4. PROTECTED PROFILE
# ============================================

@router.get(
    "/profile",
    response_model=UserResponse
)
def profile(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):

    user = db.query(User).filter(
        User.id == current_user["user_id"]
    ).first()

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user


# ============================================
# 5. GET MY TASKS
# ============================================

@router.get("/users/me/tasks")
def get_my_tasks(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):

    user = db.query(User).filter(
        User.id == current_user["user_id"]
    ).first()

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    result = [

        {
            "id": task.id,
            "title": task.title,
            "completed": task.completed,
            "user_id": task.user_id
        }

        for task in user.tasks
    ]

    return result