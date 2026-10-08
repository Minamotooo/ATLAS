<div align="center">

# ATLAS

### Learn smarter, not harder.

Adaptive tutoring for HSC Physics, Chemistry and Higher Mathematics,<br>
built on Bayesian Knowledge Tracing over a prerequisite skill graph.

<br>

<a href="https://atlas-indol-one.vercel.app/"><img src="https://img.shields.io/badge/Live_demo-atlas--indol--one.vercel.app-4f46e5?style=for-the-badge&logo=vercel&logoColor=white" alt="Live demo" height="44"></a>

<br><br>

![React](https://img.shields.io/badge/React_18-20232a?style=flat-square&logo=react)
![Vite](https://img.shields.io/badge/Vite-20232a?style=flat-square&logo=vite)
![FastAPI](https://img.shields.io/badge/FastAPI-20232a?style=flat-square&logo=fastapi)
![Supabase](https://img.shields.io/badge/Supabase-20232a?style=flat-square&logo=supabase)
![KaTeX](https://img.shields.io/badge/KaTeX-20232a?style=flat-square&logo=latex)

<br>

| **1,688** | **1,683** | **51** | **~12,000** |
|:---:|:---:|:---:|:---:|
| skills | prerequisite links | sections | questions |

</div>

<br>

## How it works

**1 · Diagnose.** A short adaptive diagnostic sets a starting mastery for every skill
in a section.

**2 · Track.** Each answer updates that skill's mastery. A correct answer also lifts
the skills it depends on.

**3 · Step back.** If three of the last five wrong answers point to the same missing
prerequisite, ATLAS asks two questions on that skill, then returns to the topic.

**4 · See it.** The mastery map shows every skill, coloured by how well you know it,
with the links between them.

Questions are in Bangla with LaTeX math. They were generated from six textbooks by a
retrieval-grounded Gemini pipeline, and each one was re-solved independently before
it was kept.

## Run locally

Create `Backend/.env` with `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` and `AUTH_SECRET`, then:

```bash
# API, http://localhost:8000
cd Backend && pip install -r requirements.txt && uvicorn server:app --reload
```

```bash
# App, http://localhost:5173
cd Frontend && npm install && npm run dev
```

```bash
# Engine test, no database needed
python Backend/smoke_test_engine.py
```

## Repository

| Path | Contents |
|---|---|
| `Backend/` | FastAPI API, BKT engine, auth |
| `Frontend/` | React + Vite app |
| `data-gen/` | Question generation pipeline |
| `Ontology/` | Skill ontology built from the textbooks |

<br>

<div align="center">
<sub><a href="ARCHITECTURE.md">Architecture</a> · <a href="BKT-DAG%20Policy%20For%20Skill%20Mastery.txt">Mastery rules</a></sub>
</div>
