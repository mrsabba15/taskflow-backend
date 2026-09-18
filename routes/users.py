# ============================================
# USERS ROUTES
# ============================================

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm

import os
import secrets
import requests

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
# SEND OTP EMAIL USING RESEND
# ============================================

def send_otp_email(
    to_email: str,
    username: str,
    otp: str
):

    # Get Resend API key
    resend_api_key = os.getenv("RESEND_API_KEY")

    # Sender email
    resend_from_email = os.getenv(
        "RESEND_FROM_EMAIL",
        "TaskFlow <onboarding@resend.dev>"
    )

    if not resend_api_key or resend_api_key in {
        "your_resend_api_key",
        "PASTE_YOUR_RESEND_API_KEY_HERE"
    }:
        raise RuntimeError(
            "RESEND_API_KEY is missing or still uses the placeholder value"
        )

    # Email payload
    payload = {
        "from": resend_from_email,
        "to": [to_email],
        "subject": "TaskFlow - Email Verification OTP",
        "html": f"""
        <html>
        <body style="font-family: Arial, sans-serif;">

            <h2>Welcome to TaskFlow</h2>

            <p>Hello <strong>{username}</strong>,</p>

            <p>Your email verification OTP is:</p>

            <h1 style="letter-spacing: 6px;">
                {otp}
            </h1>

            <p>
                This OTP will expire in
                <strong>10 minutes</strong>.
            </p>

            <p>
                If you did not create this account,
                you can ignore this email.
            </p>

            <p>
                Regards,<br>
                TaskFlow Team
            </p>

        </body>
        </html>
        """
    }

    try:

        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=20
        )

    except requests.RequestException as error:

        print("Resend connection error:", error)

        raise RuntimeError(
            "Could not connect to Resend."
        )

    # Resend rejected the request
    if not response.ok:

        print(
            "Resend API error:",
            response.status_code,
            response.text
        )

        raise RuntimeError(
            "Resend rejected the email request."
        )

    return response.json()


# ============================================
# 1. REGISTER + SEND OTP
# ============================================

@router.post("/register")
def register(
    user_data: UserCreate,
    db=Depends(get_db)
):

    # ----------------------------------------
    # Clean user input
    # ----------------------------------------

    username = user_data.username.strip()
    email = user_data.email.strip().lower()

    # ----------------------------------------
    # Find username
    # ----------------------------------------

    existing_user = db.query(User).filter(
        User.username == username
    ).first()

    # ----------------------------------------
    # Find email
    # ----------------------------------------

    existing_email = db.query(User).filter(
        User.email == email
    ).first()

    # ----------------------------------------
    # Username already verified
    # ----------------------------------------

    if existing_user and existing_user.is_verified:

        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    # ----------------------------------------
    # Email already verified
    # ----------------------------------------

    if (
        existing_email
        and existing_email.is_verified
        and (
            not existing_user
            or existing_email.id != existing_user.id
        )
    ):

        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    # ----------------------------------------
    # Username and email belong to
    # different users
    # ----------------------------------------

    if (
        existing_user
        and existing_email
        and existing_user.id != existing_email.id
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Username and email are associated "
                "with different accounts"
            )
        )

    # ----------------------------------------
    # Generate OTP
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
    # Reuse existing unverified user
    # ----------------------------------------

    if existing_user:

        user = existing_user

        user.email = email
        user.password = hashed_password
        user.otp = otp
        user.otp_expiry = otp_expiry
        user.is_verified = False

    # ----------------------------------------
    # Reuse existing unverified email record
    # ----------------------------------------

    elif existing_email:

        user = existing_email

        user.username = username
        user.password = hashed_password
        user.otp = otp
        user.otp_expiry = otp_expiry
        user.is_verified = False

    # ----------------------------------------
    # Create completely new user
    # ----------------------------------------

    else:

        user = User(
            username=username,
            email=email,
            password=hashed_password,
            is_verified=False,
            otp=otp,
            otp_expiry=otp_expiry
        )

        db.add(user)

    # ----------------------------------------
    # Save user
    # ----------------------------------------

    db.commit()
    db.refresh(user)

    # ----------------------------------------
    # Send OTP email
    # ----------------------------------------

    try:

        send_otp_email(
            to_email=email,
            username=username,
            otp=otp
        )

    except Exception as error:

        print("Email sending failed:", error)

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to send OTP email. "
                "Please try again."
            )
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

    # Check expiry
    expiry_time = datetime.fromisoformat(
        user.otp_expiry
    )

    if datetime.now(timezone.utc) > expiry_time:

        raise HTTPException(
            status_code=400,
            detail="OTP has expired"
        )

    # Verify account
    user.is_verified = True

    # Remove OTP
    user.otp = None
    user.otp_expiry = None

    db.commit()

    return {
        "message": (
            "Email verified successfully. "
            "Account created."
        )
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

    # Find user
    user = db.query(User).filter(
        User.username == form_data.username
    ).first()

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # Check verification
    if not user.is_verified:

        raise HTTPException(
            status_code=403,
            detail=(
                "Please verify your email "
                "before login"
            )
        )

    # Verify password
    password_correct = password_hash.verify(
        form_data.password,
        user.password
    )

    if not password_correct:

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # JWT payload
    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": (
            datetime.now(timezone.utc)
            + timedelta(minutes=30)
        )
    }

    # Create token
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