"""
Nivesh FastAPI Application — internal service proxied by Next.js.
Handles PDF parsing, mfapi.in integration, and portfolio operations.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import upload, portfolio, analytics, holdings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

app = FastAPI(
    title="Nivesh API",
    description="Internal API for PDF parsing and portfolio management",
    version="3.0.0",
)

# CORS — only Next.js server should call this, but allow localhost for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(portfolio.router)
app.include_router(analytics.router)
app.include_router(holdings.router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "Nivesh FastAPI"}
