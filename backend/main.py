"""
BharatFinanceAI - FastAPI Backend
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.ipo_routes import ipo_router
from app.routes.macro_routes import macro_router
from app.routes.mutual_fund_routes import mutual_fund_router
from app.routes.query_routes import query_router
from app.routes.stock_routes import macd_router
from app.routes.stock_routes import rsi_router
from app.routes.stock_routes import router as stock_router

app = FastAPI(
    title="BharatFinanceAI",
    description="Finance AI Backend API",
    version="0.1.0",
)

# CORS: use CORS_ORIGINS env var (comma-separated) for production, else localhost
_default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
_cors_origins = os.getenv("CORS_ORIGINS", "").strip()
origins = [o.strip() for o in _cors_origins.split(",") if o.strip()] or _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stock_router)
app.include_router(rsi_router)
app.include_router(macd_router)
app.include_router(mutual_fund_router)
app.include_router(ipo_router)
app.include_router(macro_router)
app.include_router(query_router)


@app.get("/")
def root():
    """Health check and API status endpoint."""
    return {"message": "Backend is running"}
