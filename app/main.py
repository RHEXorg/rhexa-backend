import os
import warnings

# Suppress all warnings and HuggingFace messages at startup
warnings.filterwarnings('ignore')
os.environ['HF_HUB_DISABLE_PROGRESSBARS'] = '1'
os.environ['HF_HUB_DISABLE_SYMLINKS'] = '1'
os.environ['TRANSFORMERS_NO_ADVISORY_WARNINGS'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['VERBOSITY'] = 'error'

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import upload, auth, search, chat, organization, data_sources, widget, google_auth, github_auth, analysis, billing
from app.db.session import engine, Base
from app import models

# Create database tables
Base.metadata.create_all(bind=engine)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    app = FastAPI(
        title="RheXa AI Engine",
        description="""
        # RheXa - Enterprise-Grade AI RAG Platform
        
        The intelligent heart of the RheXa ecosystem.
        """,
        version="1.0.0",
        debug=settings.DEBUG,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS middleware for development flexibility
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Include routers
    app.include_router(auth.router, prefix="/api")
    app.include_router(google_auth.router, prefix="/api")
    app.include_router(github_auth.router, prefix="/api")
    app.include_router(upload.router)
    app.include_router(search.router)
    app.include_router(chat.router)
    app.include_router(organization.router)
    app.include_router(data_sources.router, prefix="/api")
    app.include_router(widget.router, prefix="/api")
    app.include_router(analysis.router)
    app.include_router(billing.router)
    
    # Static files (Widget.js)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Serve uploaded files (avatars, etc.)
    uploads_dir = settings.UPLOAD_DIR
    os.makedirs(os.path.join(uploads_dir, "avatars"), exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
    
    # Health check endpoint
    @app.get("/health", tags=["System"])
    def health_check():
        return {
            "status": "ok",
            "service": "rhexa-backend",
            "environment": settings.ENV,
            "version": "1.0.0",
            "message": "System operating within mission parameters."
        }
    
    @app.get("/", tags=["System"])
    def root():
        return {
            "message": "Welcome to RheXa API",
            "version": "1.8.0",
            "docs": "/docs",
            "health": "/health"
        }

    return app


app = create_app()

# Reload trigger for DB update v2 with auth_provider
