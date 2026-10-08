"""
set_password.py
---------------
Set (or reset) an ATLAS account's password directly in Supabase.

This is the only way to:
  - give a password to an account created before passwords existed, and
  - create an admin account (self-signup refuses names in ADMIN_USERNAMES).

Run from Backend/ with Backend/.env in place:
    python set_password.py <username>            # existing account
    python set_password.py <username> --create   # create it if missing
    python set_password.py --list-missing        # accounts with no password yet

The password is prompted for (twice) and never echoed or passed on the command line.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys

from dotenv import load_dotenv
from supabase import create_client

from auth import PASSWORD_MIN_LENGTH, hash_password


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("username", nargs="?")
    parser.add_argument("--create", action="store_true", help="create the account if it does not exist")
    parser.add_argument("--list-missing", action="store_true", help="list accounts that have no password")
    args = parser.parse_args()

    load_dotenv()
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    if args.list_missing:
        rows = db.table("users").select("user_name").is_("password_hash", "null").order("user_name").execute().data
        for row in rows or []:
            print(row["user_name"])
        print(f"{len(rows or [])} account(s) without a password", file=sys.stderr)
        return 0

    if not args.username:
        parser.error("username is required unless --list-missing is given")
    user_name = args.username.strip()

    existing = db.table("users").select("user_id").eq("user_name", user_name).execute().data
    if not existing and not args.create:
        print(f"No account named '{user_name}'. Re-run with --create to make one.", file=sys.stderr)
        return 1

    password = getpass.getpass(f"New password for '{user_name}': ")
    if len(password) < PASSWORD_MIN_LENGTH:
        print(f"Password must be at least {PASSWORD_MIN_LENGTH} characters.", file=sys.stderr)
        return 1
    if getpass.getpass("Repeat password: ") != password:
        print("Passwords do not match.", file=sys.stderr)
        return 1

    password_hash = hash_password(password)
    if existing:
        db.table("users").update({"password_hash": password_hash}).eq("user_name", user_name).execute()
        print(f"Password updated for '{user_name}'.")
    else:
        db.table("users").insert({"user_name": user_name, "password_hash": password_hash}).execute()
        print(f"Created '{user_name}' with the given password.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
