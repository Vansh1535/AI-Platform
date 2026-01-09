from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logger
from app.api.ml_routes import router as ml_router
from app.api.rag_routes import router as rag_router
from app.api.agent_routes import router as agent_router
from app.rag.api.docs_router import router as docs_router
from app.api.export_routes import router as export_router
from app.api.auth_routes import router as auth_router
from app.core.db import initialize_database, close_engine, check_database_connection

# Initialize settings and logger
logger = setup_logger(settings.LOG_LEVEL)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ml_router, prefix="/ml", tags=["ML"])
app.include_router(rag_router, prefix="/rag", tags=["RAG"])
app.include_router(agent_router, prefix="/agent", tags=["Agent"])
app.include_router(docs_router)  # Document management endpoints (already has /rag/docs prefix)
app.include_router(export_router)  # Export endpoints (already has /export prefix)
app.include_router(auth_router)  # Authentication endpoints


@app.on_event("startup")
async def startup_event():
    """Initialize application and database on startup."""
    logger.info(f"{settings.APP_NAME} started in {settings.ENV} environment")
    
    # Initialize PostgreSQL database
    try:
        logger.info("Initializing PostgreSQL database...")
        await initialize_database()
        logger.info("✅ Database initialized successfully")
        
        # Verify connection
        is_available, error = await check_database_connection()
        if is_available:
            logger.info("✅ Database connection verified")
        else:
            logger.warning(f"⚠️ Database connection check failed: {error}")
            logger.warning("Application will continue with degraded functionality")
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {str(e)}")
        logger.warning("Application starting without database. Some features may be unavailable.")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down application...")
    
    try:
        await close_engine()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint with database status."""
    # Check database connection
    db_available, db_error = await check_database_connection()
    
    return {
        "status": "ok",
        "database": {
            "available": db_available,
            "error": db_error
        }
    }
