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


def _extract_supabase_payload(response):
    """
    Normalize Supabase execute() responses across client versions.

    Returns
    -------
    (data, error)
    """
    if response is None:
        return None, None

    if isinstance(response, dict):
        return response.get("data"), response.get("error")

    return getattr(response, "data", None), getattr(response, "error", None)


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

    data, error = _extract_supabase_payload(result)

    if error:
        raise HTTPException(status_code=500, detail=str(error))

    if data is None:
        raise HTTPException(status_code=404,
                            detail=f"No data for user '{user_name}'.")

    row = data
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

        # maybe_single() can return None-style empty responses when user doesn't exist.
        data, error = _extract_supabase_payload(result)

        if error:
            raise HTTPException(status_code=500, detail=str(error))

        if data is not None:
            raise HTTPException(status_code=409, detail=f"User '{user.user_name}' already exists.")

        # Insert user
        insert_result = (
            db.table("users")
            .insert({"user_name": user.user_name})
            .execute()
        )

        insert_data, insert_error = _extract_supabase_payload(insert_result)

        if insert_error:
            # Optional graceful conflict handling when DB has unique constraints.
            if "duplicate" in str(insert_error).lower() or "unique" in str(insert_error).lower():
                raise HTTPException(status_code=409, detail=f"User '{user.user_name}' already exists.")
            raise HTTPException(status_code=500, detail=f"Insert failed: {insert_error}")

        if insert_data is None:
            # Some Supabase/PostgREST configurations return minimal response on insert.
            # In that case, fetch the newly created user explicitly.
            lookup_result = (
                db.table("users")
                .select("*")
                .eq("user_name", user.user_name)
                .maybe_single()
                .execute()
            )
            insert_data, lookup_error = _extract_supabase_payload(lookup_result)
            if lookup_error:
                raise HTTPException(status_code=500, detail=f"Insert lookup failed: {lookup_error}")
            if insert_data is None:
                raise HTTPException(status_code=500, detail="Insert succeeded but no user row was returned.")

        row = insert_data[0] if isinstance(insert_data, list) else insert_data
        return {"user_id": row["user_id"], "user_name": row["user_name"]}

    except HTTPException:
        raise

    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))