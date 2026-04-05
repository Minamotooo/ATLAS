"""
example_server.py
-----------------
A minimal FastAPI server demonstrating the full cycle:

    Frontend request
        → query Supabase
        → run domain logic (BKT prediction)
        → return response to frontend

Run:
    uvicorn example_server:app --reload --port 8000

Try it:
    Base URL: http://localhost:8000/
"""

import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client

from bkt import BKTModel, BKTParams
from bloom_taxonomy import get_level_from_mastery
from mastery_updater import MasteryUpdater, UpdateMode

# ------------------------------------------------------------------ setup
app = FastAPI(title="Adaptive Engine Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

# ------------------------------------------------------------------ endpoint
@app.get("/users/{user_name}/")
def get_user(user_name: str):

    result = (
        db.table("users")
        .select("*")
        .eq("user_name", user_name)
        .maybe_single()
        .execute()
    )

    if result.data is None:
        raise HTTPException(status_code=404,
                            detail=f"No data for user '{user_name}'.")

    row = result.data

    return {
        "user_id": row["user_id"],
        "user_name": row["user_name"]
    }