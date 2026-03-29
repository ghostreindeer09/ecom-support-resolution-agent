# Policy Document Chunker
# Chunks policy markdown documents into overlapping segments with metadata

import os
import re
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional
import tiktoken

from config import CHUNK_SIZE, CHUNK_OVERLAP, POLICIES_DIR


@dataclass
class PolicyChunk:
    """A single chunk of a policy document with metadata."""
    chunk_id: str
    doc_title: str
    doc_id: str
    section: str
    url: str
    text: str
    token_count: int
    metadata: dict = field(default_factory=dict)


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Count tokens using tiktoken."""
    enc = tiktoken.get_encoding(model)
    return len(enc.encode(text))


def extract_metadata_from_doc(content: str, filename: str) -> dict:
    """Extract document-level metadata from the markdown frontmatter-style headers."""
    meta = {
        "doc_title": "",
        "doc_id": "",
        "effective_date": "",
        "applies_to": "",
        "filename": filename,
    }

    # Extract title from first H1
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        meta["doc_title"] = title_match.group(1).strip()

    # Extract document ID
    doc_id_match = re.search(r'\*\*Document ID:\*\*\s*(.+)', content)
    if doc_id_match:
        meta["doc_id"] = doc_id_match.group(1).strip()

    # Extract applies to
    applies_match = re.search(r'\*\*Applies To:\*\*\s*(.+)', content)
    if applies_match:
        meta["applies_to"] = applies_match.group(1).strip()

    return meta


def infer_chunk_metadata(doc_title: str, section: str, text_lower: str) -> dict:
    """Infer metadata fields useful for filtering from chunk content."""
    metadata = {
        "fulfillment_type": [],
        "item_category": [],
        "shipping_region": [],
        "policy_section": [],
    }

    # Fulfillment type detection
    if "first-party" in text_lower or "first party" in text_lower:
        metadata["fulfillment_type"].append("first-party")
    if "marketplace" in text_lower or "third-party" in text_lower or "third party" in text_lower:
        metadata["fulfillment_type"].append("marketplace")

    # Item category detection
    category_keywords = {
        "electronics": ["electronics", "laptop", "computer", "phone", "camera", "tv", "audio"],
        "apparel": ["apparel", "clothing", "footwear", "shoes", "garment", "swimwear"],
        "perishable": ["perishable", "food", "fresh", "frozen", "dairy", "meat", "baked"],
        "hygiene": ["hygiene", "toothbrush", "razor", "personal care", "intimates", "earbuds"],
        "software": ["software", "digital download", "license key", "game code"],
        "subscription": ["subscription", "subscription box"],
        "gift-card": ["gift card", "gift-card", "store credit"],
        "furniture": ["furniture", "large item", "mattress", "appliance"],
    }
    for category, keywords in category_keywords.items():
        if any(kw in text_lower for kw in keywords):
            metadata["item_category"].append(category)

    # Region detection
    region_keywords = {
        "US": ["united states", "us ", "domestic", "california", "new york"],
        "EU": ["european union", "eu ", "eu consumer", "eu customer"],
        "UK": ["united kingdom", "uk ", "consumer rights act"],
        "CA": ["canada", "canadian", "province"],
    }
    for region, keywords in region_keywords.items():
        if any(kw in text_lower for kw in keywords):
            metadata["shipping_region"].append(region)

    # Policy section detection
    section_keywords = {
        "returns_and_refunds": ["return", "refund", "rma", "return window"],
        "exceptions": ["exception", "non-returnable", "final sale", "hygiene", "perishable"],
        "final_sale": ["final sale", "clearance", "non-refundable"],
        "shipping_delivery": ["shipping", "delivery", "carrier", "tracking"],
        "lost_package": ["lost package", "not delivered", "missing package"],
        "carrier_policy": ["carrier", "usps", "ups", "fedex", "dhl"],
        "payment_disputes": ["payment", "billing", "charge", "transaction"],
        "chargebacks": ["chargeback", "dispute charge", "bank dispute"],
        "promotions": ["promo", "coupon", "discount", "sale event"],
        "coupon_terms": ["coupon", "promo code", "promotional"],
        "discount_policy": ["discount", "price reduction"],
        "fraud_prevention": ["fraud", "suspicious", "account abuse"],
        "dispute_resolution": ["dispute", "mediation", "investigation"],
        "damaged_items": ["damaged", "broken", "defective", "cosmetic damage"],
        "missing_items": ["missing item", "incomplete order", "wrong item"],
        "warranty": ["warranty", "manufacturer", "extended warranty"],
        "escalation": ["escalation", "escalate", "supervisor", "specialist team"],
        "regional_compliance": ["regional", "eu law", "california", "consumer protection"],
        "marketplace_guarantee": ["marketplace guarantee", "seller policy", "platform guarantee", "marketplace"],
        "gift_cards": ["gift card", "store credit", "cash redemption"],
        "communication": ["communication", "pii", "tone", "customer response"],
    }
    for section_name, keywords in section_keywords.items():
        if any(kw in text_lower for kw in keywords):
            metadata["policy_section"].append(section_name)

    return metadata


def split_into_sections(content: str) -> List[tuple]:
    """Split markdown content into sections based on ## headers."""
    sections = []
    current_section = "Overview"
    current_text = []

    for line in content.split("\n"):
        if line.startswith("## "):
            if current_text:
                sections.append((current_section, "\n".join(current_text).strip()))
            current_section = line.lstrip("# ").strip()
            current_text = []
        elif line.startswith("### "):
            # Include subsections in the current section
            current_text.append(line)
        else:
            current_text.append(line)

    if current_text:
        sections.append((current_section, "\n".join(current_text).strip()))

    return sections


def chunk_text(text: str, max_tokens: int = CHUNK_SIZE, overlap_tokens: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping token-based chunks."""
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)

    if len(tokens) <= max_tokens:
        return [text]

    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens)
        chunks.append(chunk_text)

        if end >= len(tokens):
            break
        start += max_tokens - overlap_tokens

    return chunks


def generate_chunk_id(doc_id: str, section: str, chunk_idx: int) -> str:
    """Generate a deterministic, readable chunk ID."""
    doc_prefix = doc_id.lower().replace("-", "_").replace(" ", "_")[:20]
    section_slug = re.sub(r'[^a-z0-9]', '_', section.lower())[:20]
    return f"{doc_prefix}_{section_slug}_chunk_{chunk_idx:02d}"


def generate_url(doc_title: str, section: str) -> str:
    """Generate a pseudo-URL for the policy chunk."""
    doc_slug = re.sub(r'[^a-z0-9]', '-', doc_title.lower()).strip('-')
    section_slug = re.sub(r'[^a-z0-9]', '-', section.lower()).strip('-')
    return f"https://platform.example.com/policies/{doc_slug}#{section_slug}"


def process_policy_document(filepath: str) -> List[PolicyChunk]:
    """Process a single policy document into chunks with metadata."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    filename = os.path.basename(filepath)
    doc_meta = extract_metadata_from_doc(content, filename)
    sections = split_into_sections(content)
    chunks = []

    for section_name, section_text in sections:
        if not section_text.strip():
            continue

        text_chunks = chunk_text(section_text)

        for idx, chunk_content in enumerate(text_chunks):
            chunk_id = generate_chunk_id(
                doc_meta["doc_id"] or filename.replace(".md", ""),
                section_name,
                idx
            )
            url = generate_url(doc_meta["doc_title"], section_name)
            text_lower = chunk_content.lower()

            inferred_meta = infer_chunk_metadata(
                doc_meta["doc_title"], section_name, text_lower
            )

            chunk = PolicyChunk(
                chunk_id=chunk_id,
                doc_title=doc_meta["doc_title"],
                doc_id=doc_meta.get("doc_id", ""),
                section=section_name,
                url=url,
                text=chunk_content,
                token_count=count_tokens(chunk_content),
                metadata={
                    **inferred_meta,
                    "filename": filename,
                    "doc_id": doc_meta.get("doc_id", ""),
                }
            )
            chunks.append(chunk)

    return chunks


def load_all_policies(policies_dir: str = POLICIES_DIR) -> List[PolicyChunk]:
    """Load and chunk all policy documents from the policies directory."""
    all_chunks = []

    policy_files = sorted([
        f for f in os.listdir(policies_dir)
        if f.endswith(".md")
    ])

    for policy_file in policy_files:
        filepath = os.path.join(policies_dir, policy_file)
        chunks = process_policy_document(filepath)
        all_chunks.extend(chunks)

    print(f"Loaded {len(policy_files)} policy documents → {len(all_chunks)} chunks")
    return all_chunks


if __name__ == "__main__":
    chunks = load_all_policies()
    total_tokens = sum(c.token_count for c in chunks)
    print(f"Total tokens across all chunks: {total_tokens:,}")
    print(f"Average chunk size: {total_tokens / len(chunks):.0f} tokens")

    # Show sample metadata
    for chunk in chunks[:3]:
        print(f"\n--- {chunk.chunk_id} ---")
        print(f"  Doc: {chunk.doc_title}")
        print(f"  Section: {chunk.section}")
        print(f"  Tokens: {chunk.token_count}")
        print(f"  Categories: {chunk.metadata.get('item_category', [])}")
        print(f"  Regions: {chunk.metadata.get('shipping_region', [])}")
        print(f"  Policy sections: {chunk.metadata.get('policy_section', [])}")
