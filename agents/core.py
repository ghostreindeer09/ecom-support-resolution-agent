# Agent Implementations
# All 6 agents: Triage, Order Context, Policy Retriever, Resolution Writer,
# Compliance/Safety, and Escalation

import json
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, date

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config import LLM_MODEL, MAX_REWRITE_CYCLES, CURRENT_DATE, GROQ_API_KEY
from agents.prompts import (
    TRIAGE_AGENT_PROMPT,
    ORDER_CONTEXT_PROMPT,
    RESOLUTION_WRITER_PROMPT,
    COMPLIANCE_AGENT_PROMPT,
    ESCALATION_AGENT_PROMPT,
)


def _get_llm(temperature: float = 0.0) -> ChatGroq:
    """Get a configured LLM instance using Groq."""
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=temperature,
        api_key=GROQ_API_KEY,
        max_tokens=10000,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


def _parse_json_output(text: str) -> dict:
    """Robustly parse JSON from LLM output, handling markdown fences."""
    text = text.strip()
    # Remove markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from mixed output
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {"error": "Failed to parse JSON output", "raw_output": text[:500]}


# ═══════════════════════════════════════════════════════════════════════════════
# Agent 1: Triage Agent
# ═══════════════════════════════════════════════════════════════════════════════

class TriageAgent:
    """Classifies ticket, identifies missing fields, generates clarifying questions."""

    def __init__(self):
        self.llm = _get_llm(temperature=0.0)

    def run(self, ticket_text: str, order_context: Optional[dict] = None) -> dict:
        """Run triage on a support ticket."""
        user_msg = json.dumps({
            "ticket_text": ticket_text,
            "order_context": order_context or {},
        }, indent=2)

        response = self.llm.invoke([
            SystemMessage(content=TRIAGE_AGENT_PROMPT),
            HumanMessage(content=user_msg),
        ])

        return _parse_json_output(response.content)


# ═══════════════════════════════════════════════════════════════════════════════
# Agent 2: Order Context Interpreter (Bonus)
# ═══════════════════════════════════════════════════════════════════════════════

class OrderContextAgent:
    """Validates, normalises, and enriches order context."""

    def __init__(self):
        self.llm = _get_llm(temperature=0.0)

    def run(self, order_context: dict, triage_output: dict) -> dict:
        """Validate and enrich order context."""
        prompt = ORDER_CONTEXT_PROMPT.format(current_date=CURRENT_DATE)

        user_msg = json.dumps({
            "order_context": order_context,
            "triage_output": triage_output,
        }, indent=2)

        response = self.llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=user_msg),
        ])

        return _parse_json_output(response.content)


# ═══════════════════════════════════════════════════════════════════════════════
# Agent 3: Policy Retriever Agent
# ═══════════════════════════════════════════════════════════════════════════════

class PolicyRetrieverAgent:
    """Queries the vector store and returns cited policy excerpts."""

    def __init__(self, retriever):
        """
        Args:
            retriever: HybridRetriever instance with loaded index
        """
        self.retriever = retriever

    def run(
        self,
        normalized_summary: str,
        validated_context: dict,
        issue_type: str,
    ) -> dict:
        """Retrieve relevant policy chunks."""
        fulfillment_type = validated_context.get("fulfillment_type")
        item_category = validated_context.get("item_category")
        shipping_region = validated_context.get("shipping_region")

        result = self.retriever.retrieve(
            query=normalized_summary,
            fulfillment_type=fulfillment_type,
            item_category=item_category,
            shipping_region=shipping_region,
            issue_type=issue_type,
        )

        return result


# ═══════════════════════════════════════════════════════════════════════════════
# Agent 4: Resolution Writer Agent
# ═══════════════════════════════════════════════════════════════════════════════

class ResolutionWriterAgent:
    """Drafts evidence-only resolution using retrieved policy chunks."""

    def __init__(self):
        self.llm = _get_llm(temperature=0.1)

    def run(
        self,
        normalized_summary: str,
        validated_context: dict,
        retrieved_chunks: dict,
        triage_output: dict,
        rewrite_instructions: Optional[str] = None,
    ) -> dict:
        """Generate a resolution based on policy evidence."""
        user_payload = {
            "normalized_summary": normalized_summary,
            "validated_context": validated_context,
            "retrieved_chunks": retrieved_chunks.get("retrieved_chunks", []),
            "insufficient_evidence": retrieved_chunks.get("insufficient_evidence", False),
            "issue_type": triage_output.get("issue_type", "OTHER"),
            "confidence": triage_output.get("confidence", "LOW"),
            "fraud_signal": triage_output.get("fraud_signal", False),
        }

        if rewrite_instructions:
            user_payload["rewrite_instructions"] = rewrite_instructions
            user_payload["note"] = (
                "The Compliance Agent has requested a rewrite. "
                "Address ALL failure points listed in rewrite_instructions. "
                "Ensure every claim maps to a chunk_id."
            )

        user_msg = json.dumps(user_payload, indent=2)

        response = self.llm.invoke([
            SystemMessage(content=RESOLUTION_WRITER_PROMPT),
            HumanMessage(content=user_msg),
        ])

        return _parse_json_output(response.content)


# ═══════════════════════════════════════════════════════════════════════════════
# Agent 5: Compliance / Safety Agent
# ═══════════════════════════════════════════════════════════════════════════════

class ComplianceAgent:
    """Audits resolution for citation integrity, PII, and decision correctness."""

    def __init__(self):
        self.llm = _get_llm(temperature=0.0)

    def run(
        self,
        resolution_output: dict,
        retrieved_chunks: dict,
        validated_context: dict,
        triage_output: dict,
        context_flags: List[str] = None,
    ) -> dict:
        """Run compliance checks on a resolution."""
        user_payload = {
            "resolution_output": resolution_output,
            "retrieved_chunks": retrieved_chunks.get("retrieved_chunks", []),
            "insufficient_evidence": retrieved_chunks.get("insufficient_evidence", False),
            "validated_context": validated_context,
            "fraud_signal": triage_output.get("fraud_signal", False),
            "context_flags": context_flags or [],
        }

        user_msg = json.dumps(user_payload, indent=2)

        response = self.llm.invoke([
            SystemMessage(content=COMPLIANCE_AGENT_PROMPT),
            HumanMessage(content=user_msg),
        ])

        return _parse_json_output(response.content)


# ═══════════════════════════════════════════════════════════════════════════════
# Agent 6: Escalation Agent (Bonus)
# ═══════════════════════════════════════════════════════════════════════════════

class EscalationAgent:
    """Packages unresolvable tickets for human handoff."""

    def __init__(self):
        self.llm = _get_llm(temperature=0.1)

    def run(
        self,
        ticket_text: str,
        triage_output: dict,
        validated_context: dict,
        retrieved_chunks: dict,
        resolution_output: Optional[dict],
        compliance_output: dict,
    ) -> dict:
        """Generate escalation package for human review."""
        user_payload = {
            "ticket_text": ticket_text,
            "triage_output": triage_output,
            "validated_context": validated_context,
            "retrieved_chunks": retrieved_chunks.get("retrieved_chunks", []),
            "resolution_output": resolution_output,
            "compliance_output": compliance_output,
        }

        user_msg = json.dumps(user_payload, indent=2)

        response = self.llm.invoke([
            SystemMessage(content=ESCALATION_AGENT_PROMPT),
            HumanMessage(content=user_msg),
        ])

        return _parse_json_output(response.content)
