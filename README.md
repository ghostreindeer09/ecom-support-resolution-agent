# Multi-Agent RAG Support Resolution System

A policy-grounded, citation-backed, multi-agent system for resolving e-commerce customer support tickets using RAG (Retrieval-Augmented Generation) over policy documents.

## Architecture

![ecommerce_support_agent_architecture](https://github.com/user-attachments/assets/8b39b499-71a0-496f-b858-c7025a7a622a)







### 6 Agents

| # | Agent | Type | Responsibility |
|---|-------|------|---------------|
| 1 | **Triage Agent** | Required | Classifies ticket, identifies missing fields, generates clarifying questions |
| 2 | **Order Context Interpreter** | Bonus | Validates, normalises, enriches order context (dates, categories, regions) |
| 3 | **Policy Retriever** | Required | Hybrid BM25 + semantic search with cross-encoder reranking |
| 4 | **Resolution Writer** | Required | Evidence-only generation — every claim maps to a chunk_id |
| 5 | **Compliance/Safety** | Required | Citation integrity, PII scan, decision integrity, tone check |
| 6 | **Escalation Agent** | Bonus | Human handoff briefs for unresolvable cases |

### RAG Pipeline

- **Vector Store**: FAISS (flat inner product index)
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim)
- **Chunking**: ~400 token chunks with ~80 token overlap
- **Retriever**: Hybrid BM25 + semantic, merged via Reciprocal Rank Fusion (RRF)
- **Reranker**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Top-k**: 5 (configurable), threshold: 0.72

### Policy Corpus

- **28 documents**, **25,353+ words**
- Covers: returns & refunds, shipping, cancellations, promotions, payments, disputes, fraud, perishables, hygiene, marketplace, regional compliance, gift cards, warranties, final sale, damaged items, communication standards, escalation procedures, carrier logistics, account management, digital products, and more

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Build the vector store index
python main.py --build-index

# 4. Run a single test ticket
python main.py --test-ticket 1

# 5. Run the full 25-ticket evaluation
python main.py --evaluate

# 6. Run the 3 example traces (tickets 9, 15, 18)
python main.py --examples
```

## Evaluation Test Set (25 Tickets)

| Category | Count | Tickets |
|----------|-------|---------|
| Standard | 8 | #1–8, #21 |
| Exception-Heavy | 6 | #9–14, #22 |
| Conflict | 3 | #15–17, #23 |
| Not-in-Policy | 3 | #18–20, #24 |
| Bonus | 5 | #21–25 |

### Key Evaluation Tickets

- **Ticket 9**: Perishable + damaged + "refund AND keep" → `partial`
- **Ticket 10**: Opened hygiene item → `deny`
- **Ticket 13**: EU customer at 45 days → `escalate`
- **Ticket 15**: Marketplace seller vs platform guarantee → `escalate`
- **Ticket 17**: Delivered per carrier but customer denies receipt → `escalate`
- **Ticket 18**: Price-match request → `abstain`

### Evaluation Metrics

| Metric | Target |
|--------|--------|
| Citation coverage rate | >90% |
| Unsupported claim rate | <5% |
| Correct escalation rate | 100% |

## Project Structure

```
support_resolution/
├── main.py                 # Entry point (CLI)
├── config.py               # Configuration constants
├── chunker.py              # Policy document chunker
├── retriever.py            # Hybrid BM25 + FAISS retriever
├── orchestrator.py         # 6-agent pipeline orchestrator
├── requirements.txt
├── .env.example
├── agents/
│   ├── __init__.py
│   ├── core.py             # All 6 agent classes
│   └── prompts.py          # System prompts
├── evaluation/
│   ├── __init__.py
│   ├── test_set.py         # 25 test tickets
│   └── runner.py           # Evaluation runner + metrics
├── policies/               # 28 policy documents (25K+ words)
│   ├── 01_returns_and_refunds.md
│   ├── 02_shipping_and_delivery.md
│   └── ... (28 total)
└── data/
    └── vectorstore/        # Built index (FAISS + BM25 + chunks)
```

## Design Decisions

1. **Evidence-only generation**: The Resolution Writer can only cite retrieved chunks — no hallucinated policy claims
2. **Progressive filter relaxation**: Metadata filters relax if too aggressive, preventing empty retrievals
3. **Max 2 rewrite cycles**: Prevents infinite compliance loops — auto-escalates after 2 failures
4. **Strict JSON output**: All agents output raw JSON — no markdown, no preamble
5. **Fraud signal hardcoded to escalate**: Cannot be overridden by any agent
6. **Regional law → always escalate**: Agents never interpret law
