# Multi-Agent RAG Support Resolution System
# E-commerce customer support ticket resolution using policy documents

import os
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

# RAG config
CHUNK_SIZE = 400          # tokens
CHUNK_OVERLAP = 80        # tokens
TOP_K = 7
RELEVANCE_THRESHOLD = 0.55
BM25_WEIGHT = 0.4
SEMANTIC_WEIGHT = 0.6

# Agent config
MAX_REWRITE_CYCLES = 2
CURRENT_DATE = "2026-03-27"

# Paths
POLICIES_DIR = os.path.join(os.path.dirname(__file__), "policies")
VECTORSTORE_DIR = os.path.join(os.path.dirname(__file__), "data", "vectorstore")
