# ============================================
# DATABASE MODELS
# ============================================

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


# ============================================
# USER MODEL
# ============================================

class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    username = Column(
        String,
        unique=True,
        index=True
    )

    # NEW
    email = Column(
        String,
        unique=True,
        index=True
    )

    password = Column(String)

    # NEW
    is_verified = Column(
        Boolean,
        default=False
    )

    # NEW
    otp = Column(
        String,
        nullable=True
    )

    # NEW
    otp_expiry = Column(
        String,
        nullable=True
    )

    # ========================================
    # ONE-TO-MANY RELATIONSHIP
    # ========================================

    tasks = relationship(
        "Task",
        back_populates="owner"
    )

# ============================================
# TASK MODEL
# ============================================

class Task(Base):

    __tablename__ = "tasks"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    title = Column(String)

    completed = Column(
        Boolean,
        default=False
    )

    # ========================================
    # FOREIGN KEY
    # ========================================
    # Connects this task to a User.
    # ========================================

    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    # ========================================
    # TASK → USER RELATIONSHIP
    # ========================================
    # Each Task belongs to one User.
    # ========================================

    owner = relationship(
        "User",
        back_populates="tasks"
    )