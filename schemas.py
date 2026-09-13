# ============================================
# PYDANTIC SCHEMAS
# ============================================

from pydantic import BaseModel, Field


# ============================================
# TASK CREATE
# ============================================

class TaskCreate(BaseModel):

    title: str = Field(
        min_length=3,
        max_length=100
    )

    completed: bool = False


# ============================================
# TASK RESPONSE
# ============================================

class TaskResponse(BaseModel):

    id: int
    title: str
    completed: bool
    user_id: int


# ============================================
# USER CREATE
# ============================================

class UserCreate(BaseModel):

    username: str = Field(
        min_length=3,
        max_length=50
    )

    email: str = Field(
        min_length=5,
        max_length=100
    )

    password: str = Field(
        min_length=6,
        max_length=100
    )


# ============================================
# USER RESPONSE
# ============================================

class UserResponse(BaseModel):

    id: int
    username: str


# ============================================
# LOGIN SCHEMA
# ============================================

class UserLogin(BaseModel):

    username: str
    password: str


# ============================================
# TOKEN RESPONSE
# ============================================
# Defines the response returned after login.
# ============================================

class TokenResponse(BaseModel):

    access_token: str
    token_type: str