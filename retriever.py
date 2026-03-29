# Hybrid Retriever: BM25 + Semantic + Cross-Encoder Reranker
# Implements the full RAG retrieval pipeline with metadata filtering

import os
import json
import pickle
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
import faiss

from config import (
    EMBEDDING_MODEL, CROSS_ENCODER_MODEL, TOP_K,
    RELEVANCE_THRESHOLD, BM25_WEIGHT, SEMANTIC_WEIGHT,
    VECTORSTORE_DIR
)
from chunker import PolicyChunk, load_all_policies


@dataclass
class RetrievedChunk:
    """A retrieved policy chunk with relevance metadata."""
    chunk_id: str
    doc_title: str
    section: str
    url: str
    excerpt: str
    relevance_score: float
    filters_applied: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "doc_title": self.doc_title,
            "section": self.section,
            "url": self.url,
            "excerpt": self.excerpt,
            "relevance_score": round(self.relevance_score, 4),
            "filters_applied": self.filters_applied,
        }


class HybridRetriever:
    """Hybrid BM25 + Semantic retriever with cross-encoder reranking."""

    def __init__(self, chunks: Optional[List[PolicyChunk]] = None):
        print("Initializing embedding model...")
        self.embed_model = SentenceTransformer(EMBEDDING_MODEL)
        print("Initializing cross-encoder reranker...")
        self.reranker = CrossEncoder(CROSS_ENCODER_MODEL)

        self.chunks: List[PolicyChunk] = []
        self.bm25: Optional[BM25Okapi] = None
        self.faiss_index: Optional[faiss.IndexFlatIP] = None
        self.embeddings: Optional[np.ndarray] = None

        if chunks:
            self.build_index(chunks)

    def build_index(self, chunks: List[PolicyChunk]):
        """Build BM25 and FAISS indices from policy chunks."""
        self.chunks = chunks
        print(f"Building index over {len(chunks)} chunks...")

        # ── BM25 index ──
        tokenized_docs = [chunk.text.lower().split() for chunk in chunks]
        self.bm25 = BM25Okapi(tokenized_docs)

        # ── FAISS semantic index ──
        texts = [chunk.text for chunk in chunks]
        print("  Computing embeddings...")
        self.embeddings = self.embed_model.encode(
            texts, show_progress_bar=True, batch_size=64,
            normalize_embeddings=True
        )

        dim = self.embeddings.shape[1]
        self.faiss_index = faiss.IndexFlatIP(dim)
        self.faiss_index.add(self.embeddings.astype(np.float32))

        print(f"  Index built: {len(chunks)} chunks, dim={dim}")

    def save_index(self, directory: str = VECTORSTORE_DIR):
        """Save the index to disk."""
        os.makedirs(directory, exist_ok=True)

        # Save chunks
        chunks_data = []
        for c in self.chunks:
            chunks_data.append({
                "chunk_id": c.chunk_id,
                "doc_title": c.doc_title,
                "doc_id": c.doc_id,
                "section": c.section,
                "url": c.url,
                "text": c.text,
                "token_count": c.token_count,
                "metadata": c.metadata,
            })
        with open(os.path.join(directory, "chunks.json"), "w") as f:
            json.dump(chunks_data, f, indent=2)

        # Save FAISS index
        faiss.write_index(self.faiss_index, os.path.join(directory, "faiss.index"))

        # Save embeddings
        np.save(os.path.join(directory, "embeddings.npy"), self.embeddings)

        # Save BM25 (pickle)
        with open(os.path.join(directory, "bm25.pkl"), "wb") as f:
            pickle.dump(self.bm25, f)

        print(f"Index saved to {directory}")

    def load_index(self, directory: str = VECTORSTORE_DIR):
        """Load the index from disk."""
        # Load chunks
        with open(os.path.join(directory, "chunks.json"), "r") as f:
            chunks_data = json.load(f)
        self.chunks = [
            PolicyChunk(**{k: v for k, v in cd.items()})
            for cd in chunks_data
        ]

        # Load FAISS index
        self.faiss_index = faiss.read_index(os.path.join(directory, "faiss.index"))

        # Load embeddings
        self.embeddings = np.load(os.path.join(directory, "embeddings.npy"))

        # Load BM25
        with open(os.path.join(directory, "bm25.pkl"), "rb") as f:
            self.bm25 = pickle.load(f)

        print(f"Index loaded: {len(self.chunks)} chunks")

    def _apply_metadata_filters(
        self,
        chunks_with_indices: List[tuple],
        fulfillment_type: Optional[str] = None,
        item_category: Optional[str] = None,
        shipping_region: Optional[str] = None,
        policy_sections: Optional[List[str]] = None,
    ) -> List[tuple]:
        """Filter chunks based on metadata. Returns (chunk, original_index) tuples."""
        filtered = []
        for chunk, idx in chunks_with_indices:
            meta = chunk.metadata

            # Filter by fulfillment type
            if fulfillment_type:
                chunk_ft = meta.get("fulfillment_type", [])
                if chunk_ft and fulfillment_type not in chunk_ft:
                    continue

            # Filter by item category
            if item_category:
                chunk_cat = meta.get("item_category", [])
                if chunk_cat and item_category not in chunk_cat:
                    continue

            # Filter by shipping region
            if shipping_region:
                chunk_reg = meta.get("shipping_region", [])
                if chunk_reg and shipping_region not in chunk_reg:
                    continue

            # Filter by policy sections
            if policy_sections:
                chunk_sec = meta.get("policy_section", [])
                if chunk_sec and not any(s in chunk_sec for s in policy_sections):
                    continue

            filtered.append((chunk, idx))

        return filtered

    def _bm25_search(self, query: str, top_n: int = 20) -> Dict[int, float]:
        """BM25 keyword search, returns {chunk_index: score}."""
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)

        top_indices = np.argsort(scores)[-top_n:][::-1]
        result = {}
        for idx in top_indices:
            if scores[idx] > 0:
                result[int(idx)] = float(scores[idx])
        return result

    def _semantic_search(self, query: str, top_n: int = 20) -> Dict[int, float]:
        """Semantic similarity search via FAISS, returns {chunk_index: score}."""
        query_embedding = self.embed_model.encode(
            [query], normalize_embeddings=True
        ).astype(np.float32)

        scores, indices = self.faiss_index.search(query_embedding, top_n)
        result = {}
        for idx, score in zip(indices[0], scores[0]):
            if idx >= 0:
                result[int(idx)] = float(score)
        return result

    def _reciprocal_rank_fusion(
        self,
        bm25_results: Dict[int, float],
        semantic_results: Dict[int, float],
        k: int = 60,
    ) -> Dict[int, float]:
        """Merge BM25 and semantic results using Reciprocal Rank Fusion."""
        # Convert scores to ranks
        bm25_ranked = sorted(bm25_results.keys(), key=lambda x: bm25_results[x], reverse=True)
        semantic_ranked = sorted(semantic_results.keys(), key=lambda x: semantic_results[x], reverse=True)

        fused_scores = {}
        for rank, idx in enumerate(bm25_ranked):
            fused_scores[idx] = fused_scores.get(idx, 0) + BM25_WEIGHT / (k + rank + 1)
        for rank, idx in enumerate(semantic_ranked):
            fused_scores[idx] = fused_scores.get(idx, 0) + SEMANTIC_WEIGHT / (k + rank + 1)

        return fused_scores

    def _rerank(self, query: str, candidate_indices: List[int], top_n: int = TOP_K) -> List[tuple]:
        """Rerank candidates using cross-encoder. Returns [(index, score), ...]."""
        if not candidate_indices:
            return []

        pairs = [(query, self.chunks[idx].text) for idx in candidate_indices]
        scores = self.reranker.predict(pairs)

        # Normalize scores to [0, 1] range using sigmoid
        scores_normalized = 1 / (1 + np.exp(-np.array(scores)))

        indexed_scores = list(zip(candidate_indices, scores_normalized))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)

        return indexed_scores[:top_n]

    def retrieve(
        self,
        query: str,
        fulfillment_type: Optional[str] = None,
        item_category: Optional[str] = None,
        shipping_region: Optional[str] = None,
        issue_type: Optional[str] = None,
        top_k: int = TOP_K,
        threshold: float = RELEVANCE_THRESHOLD,
    ) -> Dict[str, Any]:
        """
        Full hybrid retrieval pipeline:
        1. Metadata filter → candidate pool
        2. BM25 + semantic search
        3. RRF merge
        4. Cross-encoder rerank top-20
        5. Threshold filter → top-k

        Returns structured JSON matching the Policy Retriever Agent's output format.
        """
        # Map issue type to policy sections
        issue_section_map = {
            "REFUND": ["returns_and_refunds", "exceptions", "final_sale", "marketplace_guarantee", "gift_cards"],
            "SHIPPING": ["shipping_delivery", "lost_package", "carrier_policy"],
            "PAYMENT": ["payment_disputes", "chargebacks", "gift_cards"],
            "PROMO": ["promotions", "coupon_terms", "discount_policy", "gift_cards"],
            "FRAUD": ["fraud_prevention", "dispute_resolution"],
            "DISPUTE": ["dispute_resolution", "damaged_items", "missing_items", "marketplace_guarantee"],
            "CANCELLATION": ["returns_and_refunds"],
            "OTHER": ["gift_cards", "marketplace_guarantee"],
        }
        policy_sections = issue_section_map.get(issue_type, []) if issue_type else None

        # Build filters applied list for output
        filters_applied = []
        if fulfillment_type:
            filters_applied.append(f"fulfillment_type:{fulfillment_type}")
        if item_category:
            filters_applied.append(f"item_category:{item_category}")
        if shipping_region:
            filters_applied.append(f"shipping_region:{shipping_region}")
        if policy_sections:
            filters_applied.append(f"issue_type:{issue_type}")

        # Step 1: Build candidate pool with metadata filtering
        all_with_indices = [(c, i) for i, c in enumerate(self.chunks)]

        # Try filtered first, fall back to unfiltered if too few results
        filtered = self._apply_metadata_filters(
            all_with_indices,
            fulfillment_type=fulfillment_type,
            item_category=item_category,
            shipping_region=shipping_region,
            policy_sections=policy_sections,
        )

        # If filters are too restrictive, relax them progressively
        if len(filtered) < 10:
            # Relax: remove item_category filter
            filtered = self._apply_metadata_filters(
                all_with_indices,
                fulfillment_type=fulfillment_type,
                shipping_region=shipping_region,
                policy_sections=policy_sections,
            )
        if len(filtered) < 5:
            # Relax further: use all chunks
            filtered = all_with_indices

        candidate_indices = set(idx for _, idx in filtered)

        # Step 2: BM25 + Semantic search (on full index, then intersect)
        bm25_results = self._bm25_search(query, top_n=30)
        semantic_results = self._semantic_search(query, top_n=30)

        # Intersect with metadata-filtered candidates
        bm25_filtered = {k: v for k, v in bm25_results.items() if k in candidate_indices}
        semantic_filtered = {k: v for k, v in semantic_results.items() if k in candidate_indices}

        # Also keep some unfiltered results in case filters are too aggressive
        bm25_combined = {**bm25_filtered}
        semantic_combined = {**semantic_filtered}

        # If filtered results are too sparse, include some unfiltered top results
        if len(bm25_combined) < 5:
            for k, v in list(bm25_results.items())[:10]:
                bm25_combined.setdefault(k, v)
        if len(semantic_combined) < 5:
            for k, v in list(semantic_results.items())[:10]:
                semantic_combined.setdefault(k, v)

        # Step 3: RRF merge
        fused = self._reciprocal_rank_fusion(bm25_combined, semantic_combined)

        # Select top-20 candidates for reranking
        top_20_indices = sorted(fused.keys(), key=lambda x: fused[x], reverse=True)[:20]

        if not top_20_indices:
            return {
                "retrieved_chunks": [],
                "retrieval_metadata": {
                    "k": top_k,
                    "filters_applied": filters_applied,
                    "chunks_below_threshold": 0,
                    "hybrid_search": True,
                },
                "insufficient_evidence": True,
            }

        # Step 4: Cross-encoder rerank
        reranked = self._rerank(query, top_20_indices, top_n=top_k * 2)

        # Step 5: Threshold filter
        chunks_below_threshold = 0
        retrieved = []
        for idx, score in reranked:
            if score >= threshold:
                chunk = self.chunks[idx]
                retrieved.append(RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    doc_title=chunk.doc_title,
                    section=chunk.section,
                    url=chunk.url,
                    excerpt=chunk.text,
                    relevance_score=float(score),
                    filters_applied=filters_applied,
                ))
            else:
                chunks_below_threshold += 1

        # Limit to top_k
        retrieved = retrieved[:top_k]
        insufficient = len(retrieved) == 0

        return {
            "retrieved_chunks": [r.to_dict() for r in retrieved],
            "retrieval_metadata": {
                "k": top_k,
                "filters_applied": filters_applied,
                "chunks_below_threshold": chunks_below_threshold,
                "hybrid_search": True,
            },
            "insufficient_evidence": insufficient,
        }


def build_and_save_index():
    """Build the full index from policy documents and save to disk."""
    chunks = load_all_policies()
    retriever = HybridRetriever()
    retriever.build_index(chunks)
    retriever.save_index()
    return retriever


if __name__ == "__main__":
    retriever = build_and_save_index()

    # Test retrieval
    result = retriever.retrieve(
        query="Customer received damaged laptop and wants a full refund",
        fulfillment_type="first-party",
        item_category="electronics",
        shipping_region="US",
        issue_type="REFUND",
    )

    print(f"\nRetrieved {len(result['retrieved_chunks'])} chunks")
    print(f"Insufficient evidence: {result['insufficient_evidence']}")
    for chunk in result["retrieved_chunks"]:
        print(f"\n  [{chunk['relevance_score']:.3f}] {chunk['chunk_id']}")
        print(f"    {chunk['doc_title']} — {chunk['section']}")
        print(f"    {chunk['excerpt'][:120]}...")
