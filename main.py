# ============================================
# MAIN FASTAPI APPLICATION
# ============================================

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from database import Base, engine

from routes.tasks import router
from routes.users import router as user_router

from fastapi.middleware.cors import CORSMiddleware


# ============================================
# CREATE FASTAPI APP
# ============================================

app = FastAPI()

# ============================================
# CORS CONFIGURATION
# ============================================
# Allows our React frontend to communicate
# with the FastAPI backend.
# ============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# CREATE DATABASE TABLES
# ============================================

Base.metadata.create_all(bind=engine)


# ============================================
# INCLUDE ROUTES
# ============================================

app.include_router(router)
app.include_router(user_router)


# ============================================
# HOME ROUTE
# ============================================

@app.get("/")
def home():

    return {
        "message": "Backend is working!"
    }


# ============================================
# GLOBAL ERROR HANDLER
# ============================================
# This handles unexpected errors that happen
# anywhere inside our application.
#
# Instead of exposing technical information
# to the client, we return a clean response.
# ============================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception
):

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "Something went wrong on the server."
        }
    )

