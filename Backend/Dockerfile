# Build from the repository root (render.yaml sets dockerContext: .):
#   docker build -f Backend/Dockerfile -t atlas-api .
# admin_ontology.py loads Ontology/full_corpus_rebuild/ at import time, so those
# two files ship next to Backend/ or the server will not start.
FROM python:3.13-slim

WORKDIR /app/Backend

COPY Backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY Backend/ .
COPY Ontology/full_corpus_rebuild/tuples.json Ontology/full_corpus_rebuild/prereqs.json /app/Ontology/full_corpus_rebuild/

# Hosts like Render inject PORT. Their proxy sets X-Forwarded-For, which the
# login throttle needs in order to see the real client IP.
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
