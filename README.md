<div align="center">

# ATLAS

Adaptive tutoring for HSC Physics, Chemistry and Higher Mathematics.

<a href="https://atlas-indol-one.vercel.app/"><img src="https://img.shields.io/badge/Live_demo-atlas--indol--one.vercel.app-4f46e5?style=for-the-badge&logo=vercel&logoColor=white" alt="Live demo" height="44"></a>

![React](https://img.shields.io/badge/React-18-20232a?logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?logo=fastapi&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-Postgres-3ecf8e?logo=supabase&logoColor=white)

</div>

ATLAS keeps a mastery estimate for each of 1,688 skills, updated after every answer
with Bayesian Knowledge Tracing. Skills are linked by 1,683 prerequisite edges.
When a learner keeps getting things wrong, ATLAS checks which prerequisite the wrong
answers point to and gives a couple of questions on that before going back to the
topic.

The question bank holds about 12,000 Bangla multiple-choice questions with LaTeX
math. They were generated from six textbooks with a retrieval-grounded Gemini
pipeline, and each one was re-solved independently before it was kept.

## Run locally

Create `Backend/.env` with `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` and `AUTH_SECRET`.

```bash
cd Backend && pip install -r requirements.txt && uvicorn server:app --reload
cd Frontend && npm install && npm run dev
```

Run the two commands in separate terminals.

To test the engine without a database:

```bash
python Backend/smoke_test_engine.py
```

## Layout

| Path | Contents |
|---|---|
| `Backend/` | FastAPI API, BKT engine, auth |
| `Frontend/` | React + Vite app |
| `data-gen/` | Question generation pipeline |
| `Ontology/` | Skill ontology built from the textbooks |

More detail is in [ARCHITECTURE.md](ARCHITECTURE.md). The exact mastery rules are in
[`BKT-DAG Policy For Skill Mastery.txt`](BKT-DAG%20Policy%20For%20Skill%20Mastery.txt).
