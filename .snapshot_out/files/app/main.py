"""
Main FastAPI application entry point
"""

from app.api import app

# Export the app instance for uvicorn
__all__ = ["app"]