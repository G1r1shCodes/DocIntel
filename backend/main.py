import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database.session import engine, Base

# Import routers
from api.documents_router import router as documents_router, UPLOAD_DIR
from api.chat_router import router as chat_router
from api.bookmarks_router import router as bookmarks_router
from api.analytics_router import router as analytics_router

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DocIntel - Enterprise AI Document Intelligence Platform",
    description="Enterprise document intelligence platform featuring hybrid RAG, multi-format parsing, citations, PDF highlight rendering, and analytics.",
    version="1.0.0"
)

# Enable CORS for Next.js / Vite frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploaded files static directory so frontend can fetch PDFs for inline display
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Include Routers
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(bookmarks_router)
app.include_router(analytics_router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "app": "DocIntel Enterprise AI Platform",
        "tagline": "Enterprise AI document intelligence platform with hybrid RAG, citations, OCR, and semantic search.",
        "endpoints": {
            "documents": "/api/documents",
            "chat": "/api/chat/query",
            "bookmarks": "/api/bookmarks",
            "analytics": "/api/analytics/dashboard",
            "uploads": "/uploads"
        }
    }
