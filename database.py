# ============================================
# DATABASE CONFIGURATION
# ============================================

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from dotenv import load_dotenv
import os


# ============================================
# LOAD ENVIRONMENT VARIABLES
# ============================================

load_dotenv()


# ============================================
# DATABASE URL
# ============================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing from .env"
    )


# ============================================
# DATABASE ENGINE
# ============================================

# Use psycopg driver for PostgreSQL
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1
    )

engine = create_engine(
    DATABASE_URL
)

# ============================================
# DATABASE SESSION
# ============================================

SessionLocal = sessionmaker(
    bind=engine
)


# ============================================
# BASE MODEL
# ============================================

Base = declarative_base()


# ============================================
# DATABASE DEPENDENCY
# ============================================
# FastAPI will use this function to create
# and automatically close database sessions.
# ============================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()