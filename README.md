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


Clone the repository and navigate into the project directory:

```bash
git clone https://github.com/ghostreindeer09/ecom-support-resolution-agent.git
cd ecom-support-resolution-agent
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Set up environment variables by copying the example file and adding your API key:

```bash
cp .env.example .env
```

Then edit `.env` and add:

```env
OPENAI_API_KEY=your_api_key_here
```

Build the retrieval index (BM25 + FAISS) from policy documents:

```bash
python main.py --build-index
```

Run the system on a single test ticket:

```bash
python main.py --test-ticket 1
```

Run the full evaluation on all 25 test tickets:

```bash
python main.py --evaluate
```

Run example traces to inspect agent workflows (tickets 9, 15, 18):

```bash
python main.py --examples
```

Tip:  Rebuild the index whenever policy documents change, and use example traces to debug agent reasoning and improve performance.


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

<img width="1187" height="308" alt="Screenshot 2026-03-29 at 19 20 43" src="https://github.com/user-attachments/assets/8df69c2d-14ab-488c-b049-fdd68a4978af" />


## Design Decisions

1. **Evidence-only generation**: The Resolution Writer can only cite retrieved chunks — no hallucinated policy claims
2. **Progressive filter relaxation**: Metadata filters relax if too aggressive, preventing empty retrievals
3. **Max 2 rewrite cycles**: Prevents infinite compliance loops — auto-escalates after 2 failures
4. **Strict JSON output**: All agents output raw JSON — no markdown, no preamble
5. **Fraud signal hardcoded to escalate**: Cannot be overridden by any agent
6. **Regional law → always escalate**: Agents never interpret law
