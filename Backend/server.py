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
from pydantic import BaseModel
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

class UserCreate(BaseModel):
    user_name: str

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

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    if result.get("data") is None:
        raise HTTPException(status_code=404,
                            detail=f"No data for user '{user_name}'.")

    row = result["data"]
    return {
        "user_id": row["user_id"],
        "user_name": row["user_name"]
    }


@app.post("/users/")
def create_user(user: UserCreate):
    try:
        result = (
            db.table("users")
            .select("*")
            .eq("user_name", user.user_name)
            .maybe_single()
            .execute()
        )

        # Check for None (old client behavior)
        if result is None:
            raise HTTPException(status_code=500, detail="Supabase query returned None. Check your URL and service key.")

        # Support new client: result is a dict with 'data' and 'error'
        data = getattr(result, "data", None) or result.get("data", None)  # works with object or dict
        error = getattr(result, "error", None) or result.get("error", None)

        if error:
            raise HTTPException(status_code=500, detail=str(error))

        if data is not None:
            raise HTTPException(status_code=409, detail=f"User '{user.user_name}' already exists.")

        # Insert user
        insert_result = (
            db.table("users")
            .insert({"user_name": user.user_name})
            .select("*")
            .single()
            .execute()
        )

        if insert_result is None:
            raise HTTPException(status_code=500, detail="Supabase insert returned None.")

        insert_data = getattr(insert_result, "data", None) or insert_result.get("data", None)
        insert_error = getattr(insert_result, "error", None) or insert_result.get("error", None)

        if insert_error or insert_data is None:
            raise HTTPException(status_code=500, detail=f"Insert failed: {insert_error}")

        row = insert_data
        return {"user_id": row["user_id"], "user_name": row["user_name"]}

    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))