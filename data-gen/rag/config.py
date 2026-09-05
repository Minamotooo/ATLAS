"""Paths and hyperparameters for the naive RAG pipeline."""

import os
from pathlib import Path

# data-gen/
DATA_GEN_DIR = Path(__file__).resolve().parent.parent
# repository root
BKTBACK_DIR = DATA_GEN_DIR.parent
# Canonical ontology lives with the Backend that serves it.
ONTOLOGY_SOURCE_DIR = BKTBACK_DIR / "Backend" / "tree_data" / "ontology_source"

DOCUMENTS_DIR = BKTBACK_DIR / "documents"
KB_DIR = Path(__file__).resolve().parent / "kb"
ITEMS_PATH = KB_DIR / "items.jsonl"
EMBEDDINGS_PATH = KB_DIR / "embeddings.npy"

# Multilingual embedding model (CPU) — Bangla + English + LaTeX-ish text.
# MiniLM is smaller/faster to download than e5-base; still multilingual.
# Override with env RAG_EMBED_MODEL. Force TF-IDF with RAG_FORCE_TFIDF=1.
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# Stronger (slower download): intfloat/multilingual-e5-base
# E5 models expect "passage: ..." / "query: ..." prefixes.
PASSAGE_PREFIX = "passage: "
QUERY_PREFIX = "query: "

# Retrieval
TOP_K = 5
# Soft boost when KB item subject matches the query's subject (Math/Physics/Chemistry).
SUBJECT_MATCH_BOOST = 0.08
# Soft boost for MCQ KB items (generator must always emit MCQs, not Written).
MCQ_MATCH_BOOST = 0.06

# Canonical subjects for BUET / university admission.
SUBJECT_ALIASES = {
    "math": "Mathematics",
    "mathematics": "Mathematics",
    "গণিত": "Mathematics",
    "পাটিগণিত": "Mathematics",
    "higher math": "Mathematics",
    "higher mathematics": "Mathematics",
    "physics": "Physics",
    "পদার্থবিজ্ঞান": "Physics",
    "পদার্থ": "Physics",
    "chemistry": "Chemistry",
    "রসায়ন": "Chemistry",
    "রসায়ন": "Chemistry",
}

# Local generator (Ollama)
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:7b-instruct-q4_K_M"
OLLAMA_FALLBACK_MODEL = "qwen2.5:3b-instruct"
# Generous because a single call is ~5-6k prompt tokens + ~3k generated tokens.
# On a GPU that is well under a minute; on CPU it can exceed 15 minutes, and the
# old 300s ceiling made every call time out and produce nothing.
OLLAMA_TIMEOUT_SEC = int(os.environ.get("OLLAMA_TIMEOUT_SEC", "1800"))
OLLAMA_TEMPERATURE = 0.7

# Ollama defaults num_ctx to 2048. Our prompt (system + 5 retrieved reference
# blocks) measures ~4-6k tokens, so leaving this unset SILENTLY TRUNCATES the
# retrieved material - questions still generate, but ungrounded and off-schema.
# Must comfortably exceed prompt + num_predict.
OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "8192"))
OLLAMA_NUM_PREDICT = int(os.environ.get("OLLAMA_NUM_PREDICT", "3072"))

# Generation loop defaults (mirrors generate_question.py)
N_QUESTIONS = 3
OUTPUT_PATH = DATA_GEN_DIR / "output_questions.json"
RAW_OUTPUT_DIR = DATA_GEN_DIR / "raw_responses_rag"
TUPLES_PATH = ONTOLOGY_SOURCE_DIR / "tuples.json"
PREREQS_PATH = ONTOLOGY_SOURCE_DIR / "prereqs.json"
START_TUPLE_INDEX = 1  # 1-based; set higher to resume
MAX_JSON_RETRIES = 2

# The ontology assigns ONE Bloom level per skill (mostly "Apply"). Both the
# diagnostic and topic practice ask for a question one Bloom level ABOVE the
# learner's current band, so a single-level bank forces the nearby-Bloom fallback
# on nearly every request. With expansion on, each skill is generated at every
# Bloom level, which is what the adaptive policy actually needs.
# Cost: 6x the generation runs. Override with env RAG_EXPAND_BLOOMS=0.
EXPAND_ALL_BLOOM_LEVELS = True
BLOOM_LEVELS = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
