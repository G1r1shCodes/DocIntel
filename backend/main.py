from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.session import engine, Base

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Internal RAG Tool - KDI Power Company")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Internal RAG Tool API is running"}
