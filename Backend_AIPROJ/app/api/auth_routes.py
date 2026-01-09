"""
Simple admin authentication for single-user deployment.
Credentials stored in environment variables.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import jwt
import os
from datetime import datetime, timedelta
from app.core.logging import setup_logger

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = setup_logger("INFO")

# Load admin credentials from environment
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production-to-random-secret")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    token_type: str
    role: str
    username: str


class TokenVerifyRequest(BaseModel):
    """Token verification request"""
    token: str


class TokenVerifyResponse(BaseModel):
    """Token verification response"""
    valid: bool
    role: str | None = None
    username: str | None = None


@router.post("/login", response_model=LoginResponse)
async def admin_login(request: LoginRequest):
    """
    Admin login endpoint.
    
    Checks credentials against environment variables.
    Returns JWT token valid for 7 days.
    """
    logger.info(f"Login attempt for user: {request.username}")
    
    # Check credentials
    if request.username != ADMIN_USERNAME or request.password != ADMIN_PASSWORD:
        logger.warning(f"Failed login attempt for: {request.username}")
        raise HTTPException(
            status_code=401, 
            detail="Invalid credentials"
        )
    
    # Generate JWT token
    token_data = {
        "username": ADMIN_USERNAME,
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    
    token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")
    
    logger.info(f"Successful login for admin: {ADMIN_USERNAME}")
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": "admin",
        "username": ADMIN_USERNAME
    }


@router.post("/verify", response_model=TokenVerifyResponse)
async def verify_token(request: TokenVerifyRequest):
    """
    Verify JWT token validity.
    
    Returns user role and username if valid.
    """
    try:
        payload = jwt.decode(request.token, SECRET_KEY, algorithms=["HS256"])
        
        return {
            "valid": True,
            "role": payload.get("role"),
            "username": payload.get("username")
        }
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token verification failed: expired")
        raise HTTPException(
            status_code=401, 
            detail="Token expired"
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=401, 
            detail="Invalid token"
        )


@router.get("/status")
async def auth_status():
    """
    Get authentication system status.
    """
    return {
        "status": "active",
        "admin_configured": bool(ADMIN_USERNAME and ADMIN_PASSWORD),
        "jwt_configured": bool(SECRET_KEY != "change-me-in-production-to-random-secret")
    }
