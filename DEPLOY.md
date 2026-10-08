# Deploying ATLAS

The frontend runs on **Vercel**, the API on **Render** (free tier, Docker), and the
database stays on the existing **Supabase** project.

```
Browser ──▶ Vercel (Frontend/, static SPA) ──HTTPS + Bearer token──▶ Render (Backend/, Docker) ──▶ Supabase
```

Both hosts build from GitHub, so the code has to be pushed before you start.
Everything else in this guide is a one-time setup.

---

## 0. Before you start

- **The Supabase project must be active.** Free-tier projects are paused after a
  stretch of inactivity, and a paused project's hostname stops resolving. If the
  backend fails with `getaddrinfo failed` or `Name or service not known`, open the
  project in the Supabase dashboard and restore it first.
- You need a Render account and a Vercel account. Both can sign in with GitHub, and
  both need access to the repository.

## 1. Prepare the database (once)

Passwords are stored as salted scrypt hashes in a new `users.password_hash` column.
In the Supabase dashboard, open **SQL Editor** and run:

```sql
alter table public.users add column if not exists password_hash text;
```

Then, from `Backend/` on your machine (with `Backend/.env` in place), create the
admin account. Self-signup refuses any name listed in `ADMIN_USERNAMES`, so this
script is the only way to make one:

```bash
python set_password.py admin --create
```

Accounts created before passwords existed can't log in until they have one. To deal
with them:

```bash
python set_password.py --list-missing     # which accounts still have no password
python set_password.py <username>         # set one (you are prompted; it is never echoed)
```

## 2. Deploy the API on Render

1. In the Render dashboard, choose **New → Blueprint** and pick this repository.
   Render reads [`render.yaml`](render.yaml) and proposes one web service,
   `atlas-api`.
2. When prompted, paste `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`, the same values as
   in your `Backend/.env`. `AUTH_SECRET` is generated for you. `ADMIN_USERNAMES=admin`
   and `DEMO_SHOW_ANSWERS=0` come from the file.
3. Wait for the first deploy to finish (a few minutes). Then open
   `https://<your-service>.onrender.com/catalog`; the exact URL is shown at the top of
   the service page. You should get JSON with a `courses` array.

`render.yaml` sets the region to Singapore. If your Supabase project is in another
region, change it to the closest one before the first deploy, because every API
request makes several database round trips.

## 3. Deploy the frontend on Vercel

1. In Vercel, choose **Add New → Project** and import this repository.
2. Set **Root Directory** to `Frontend`. Vercel detects Vite on its own.
3. Under **Environment Variables**, add `VITE_API_BASE_URL` set to the Render URL from
   step 2, with no trailing slash.
4. Deploy. [`Frontend/vercel.json`](Frontend/vercel.json) already rewrites every path
   to `index.html`, so deep links like `/courses/...` work.

`VITE_API_BASE_URL` is baked in at build time. If the API URL ever changes, update the
variable and redeploy the frontend.

## 4. Check that it works

- Sign up with a new username and password. You should land on `/courses`.
- Log out, then try to log in with the wrong password. You should see
  *"Incorrect username or password."*
- Log in as `admin`. The admin links should appear in the navbar.

## 5. Optional: restrict CORS to your site

By default the API accepts requests from any origin. That's acceptable here because
sign-in uses bearer tokens, not cookies. To lock it down, set
`CORS_ORIGINS=https://<your-app>.vercel.app` in Render under **atlas-api →
Environment**. Separate several origins with commas.

---

## What to expect on the free tier

- **Cold starts.** A free Render service sleeps after about 15 minutes without
  traffic. The next request wakes it, which takes about a minute.
- **In-progress sessions are lost** on every sleep, restart or redeploy, because
  diagnostic and topic-practice sessions live in memory (see ARCHITECTURE.md §9). Mastery
  already written to Supabase is safe, and learners stay logged in because their
  tokens are signed with the stable `AUTH_SECRET`.
- **Admin ontology edits don't persist.** The editor at `/admin/ontology` writes to
  the container's disk, which is reset on every restart. Make ontology edits locally
  and commit them.
- **Login throttling counters reset** on restart. After 5 failed attempts per IP and
  username, logins are refused for 15 minutes.

## Configuration reference

| Variable | Set where | Purpose |
|---|---|---|
| `SUPABASE_URL` | Render (secret) | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Render (secret) | Service-role key, with full DB access. Never commit it. |
| `AUTH_SECRET` | Render (generated) | Signs login tokens. Changing it signs everyone out. |
| `ADMIN_USERNAMES` | `render.yaml` | Comma-separated admin usernames |
| `DEMO_SHOW_ANSWERS` | `render.yaml` | `0` in production. `1` sends answer hints to the browser. |
| `CORS_ORIGINS` | Render (optional) | Comma-separated allowed origins (default `*`) |
| `NEXT_QUESTION_DEBUG_LOGS` | `render.yaml` | Verbose question-search logging (off) |
| `VITE_API_BASE_URL` | Vercel | API base URL, read at build time |

For local development, also put an `AUTH_SECRET=<any long random string>` line in
`Backend/.env`. Without it the backend picks a random secret on each start, so every
restart, including each `--reload` after a code change, signs you out.
