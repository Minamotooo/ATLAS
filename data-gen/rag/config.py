"""Paths and hyperparameters for the naive RAG pipeline."""

from pathlib import Path

# data-gen/
DATA_GEN_DIR = Path(__file__).resolve().parent.parent
# bktback/
BKTBACK_DIR = DATA_GEN_DIR.parent

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
OLLAMA_TIMEOUT_SEC = 300
OLLAMA_TEMPERATURE = 0.7

# Generation loop defaults (mirrors generate_question.py)
N_QUESTIONS = 3
OUTPUT_PATH = DATA_GEN_DIR / "output_questions.json"
RAW_OUTPUT_DIR = DATA_GEN_DIR / "raw_responses_rag"
TUPLES_PATH = DATA_GEN_DIR / "tuples.json"
PREREQS_PATH = DATA_GEN_DIR / "prereqs.json"
START_TUPLE_INDEX = 1  # 1-based; set higher to resume
MAX_JSON_RETRIES = 2
