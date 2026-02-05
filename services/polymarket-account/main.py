"""
Polymarket Account Service
Placeholder - to be implemented when Polymarket integration is ready
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Polymarket Account Service",
    description="Account management for Polymarket (placeholder)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "ok", "service": "polymarket-account", "ready": False}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/accounts")
async def list_accounts():
    """List accounts - returns empty list until implemented"""
    return []


@app.post("/accounts")
async def create_account():
    """Create account - not implemented"""
    raise HTTPException(501, "Polymarket integration not yet implemented")


@app.get("/accounts/{account_id}")
async def get_account(account_id: str):
    """Get account - not implemented"""
    raise HTTPException(501, "Polymarket integration not yet implemented")


@app.put("/accounts/{account_id}")
async def update_account(account_id: str):
    """Update account - not implemented"""
    raise HTTPException(501, "Polymarket integration not yet implemented")


@app.delete("/accounts/{account_id}")
async def delete_account(account_id: str):
    """Delete account - not implemented"""
    raise HTTPException(501, "Polymarket integration not yet implemented")


@app.post("/trade")
async def execute_trade():
    """Execute trade - not implemented"""
    raise HTTPException(501, "Polymarket integration not yet implemented")


@app.get("/positions/{account_id}")
async def get_positions(account_id: str):
    """Get positions - returns empty list until implemented"""
    return []


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
