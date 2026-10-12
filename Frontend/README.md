# ATLAS Frontend

React 18 + Vite single-page app for ATLAS: course and section browsing, the adaptive
diagnostic, topic practice, mastery maps (Cytoscape), and Bangla/LaTeX question
rendering (KaTeX). See the root [README](../README.md) for the project overview.

## Run

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # production build into dist/
```

The API base URL comes from `VITE_API_BASE_URL` (default `http://localhost:8000`).
It is read at build time. The deployed site on Vercel sets it to the Render API URL;
see [`../DEPLOY.md`](../DEPLOY.md). `vercel.json` rewrites every path to
`index.html` so deep links work.

## Layout

- `src/pages/`: one component per route (route table in [`../ARCHITECTURE.md`](../ARCHITECTURE.md) §6)
- `src/components/`: layout, navbar, `MathText` (LaTeX renderer), shared UI
- `src/context/`: `AuthContext` (token session, `authFetch`), `LanguageContext` (English/Bangla)
