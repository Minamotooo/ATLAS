# ATLAS Backend

FastAPI adaptive engine: Bayesian Knowledge Tracing over a prerequisite skill DAG,
serving admission-test (BUET/KUET/RUET) Mathematics, Physics and Chemistry.

## Run

```bash
python -m venv .venv && .venv/Scripts/activate      # Windows
pip install -r requirements.txt
# copy .env.example to .env and fill in SUPABASE_URL, SUPABASE_SERVICE_KEY and AUTH_SECRET
uvicorn server:app --reload --port 8000
```

## Accounts

Login is username + password (`auth.py`): scrypt hashes in `users.password_hash`,
HS256 bearer tokens signed with `AUTH_SECRET`. Admin accounts and password resets go
through the CLI, since self-signup refuses names in `ADMIN_USERNAMES`:

```bash
python set_password.py <username> [--create]
python set_password.py --list-missing
```

Deployment (Render + Vercel) is covered in [`../DEPLOY.md`](../DEPLOY.md).

## Ontology

The served ontology is compiled from `../Ontology/full_corpus_rebuild/` (1,688 skills)
into the files the server loads. Always pass `--source-dir`: without it the script
reads the legacy 430-skill `tree_data/ontology_source/`, which is kept only as a
reference.

```bash
python tree_data/build_from_ontology.py --source-dir ../Ontology/full_corpus_rebuild --report-only   # inspect
python tree_data/build_from_ontology.py --source-dir ../Ontology/full_corpus_rebuild --out-dir tree_data --force
node tree_data/generate_ontology_sync_sql.js                   # regenerate the SQL
# then run tree_data/sync_ontology_to_supabase.sql in Supabase
```

Editorial decisions (topic aliases, display labels, course/section layout) live in
`tree_data/ontology_config.json`. Everything else is derived.

## Tests

```bash
.venv/Scripts/python.exe smoke_test_engine.py
```

Runs the diagnostic, mastery propagation and topic-practice spillover end to end
against an in-memory stand-in for Supabase, then drives signup/login, token checks,
per-learner and session ownership, admin gating and login throttling over HTTP.
No credentials needed.

## Schema

`schema.sql` is the live Supabase DDL, kept by hand. Read the header notes before
writing anything to these tables.
