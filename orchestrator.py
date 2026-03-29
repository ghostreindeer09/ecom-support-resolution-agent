# Pipeline Orchestrator
# Wires all 6 agents together with rewrite loops and escalation handling

import json
import time
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict

from config import MAX_REWRITE_CYCLES
from agents.core import (
    TriageAgent,
    OrderContextAgent,
    PolicyRetrieverAgent,
    ResolutionWriterAgent,
    ComplianceAgent,
    EscalationAgent,
)
from retriever import HybridRetriever


@dataclass
class PipelineTrace:
    """Complete trace of a ticket through the pipeline."""
    ticket_text: str
    order_context: dict
    triage_output: dict = field(default_factory=dict)
    order_context_output: dict = field(default_factory=dict)
    retriever_output: dict = field(default_factory=dict)
    resolution_output: dict = field(default_factory=dict)
    compliance_output: dict = field(default_factory=dict)
    escalation_output: dict = field(default_factory=dict)
    final_decision: str = ""
    rewrite_cycles: int = 0
    pipeline_status: str = ""  # completed | escalated | abstained | needs_clarification
    execution_time_seconds: float = 0.0
    agent_log: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


class SupportPipeline:
    """
    Orchestrates the 6-agent pipeline:
    Triage → Order Context → Policy Retriever → Resolution Writer → Compliance → (Escalation)
    With rewrite loop (max 2 cycles) between Resolution Writer and Compliance.
    """

    def __init__(self, retriever: HybridRetriever):
        print("Initializing support pipeline agents...")
        self.triage = TriageAgent()
        self.order_context = OrderContextAgent()
        self.policy_retriever = PolicyRetrieverAgent(retriever)
        self.resolution_writer = ResolutionWriterAgent()
        self.compliance = ComplianceAgent()
        self.escalation = EscalationAgent()
        print("All agents initialized.")

    def _log(self, trace: PipelineTrace, agent: str, message: str):
        """Add a log entry to the pipeline trace."""
        entry = {"agent": agent, "message": message, "timestamp": time.time()}
        trace.agent_log.append(entry)
        print(f"  [{agent}] {message}")

    def run(self, ticket_text: str, order_context: Optional[dict] = None) -> PipelineTrace:
        """
        Run a support ticket through the full pipeline.

        Returns a PipelineTrace with all intermediate outputs and the final decision.
        """
        start_time = time.time()
        trace = PipelineTrace(
            ticket_text=ticket_text,
            order_context=order_context or {},
        )

        print(f"\n{'='*70}")
        print(f"Processing ticket: {ticket_text[:80]}...")
        print(f"{'='*70}")

        # ── Stage 1: Triage ──
        self._log(trace, "Triage", "Classifying ticket...")
        trace.triage_output = self.triage.run(ticket_text, order_context)
        issue_type = trace.triage_output.get("issue_type", "OTHER")
        fraud_signal = trace.triage_output.get("fraud_signal", False)
        self._log(trace, "Triage", f"Classification: {issue_type}, Fraud: {fraud_signal}")

        # Check for clarifying questions
        clarifying_qs = trace.triage_output.get("clarifying_questions", [])
        if clarifying_qs and not order_context:
            self._log(trace, "Triage", f"Needs clarification: {len(clarifying_qs)} questions")
            trace.pipeline_status = "needs_clarification"
            trace.final_decision = "clarify"
            trace.execution_time_seconds = time.time() - start_time
            return trace

        # ── Stage 2: Order Context Interpreter ──
        self._log(trace, "OrderContext", "Validating and enriching order context...")
        trace.order_context_output = self.order_context.run(
            order_context or {},
            trace.triage_output,
        )
        validated_ctx = trace.order_context_output.get("validated_context", order_context or {})
        ctx_flags = trace.order_context_output.get("flags", [])
        self._log(trace, "OrderContext", f"Flags: {ctx_flags}")

        # ── Stage 3: Policy Retriever ──
        normalized_summary = trace.triage_output.get("normalized_summary", ticket_text)
        self._log(trace, "PolicyRetriever", f"Retrieving policies for: {issue_type}...")
        trace.retriever_output = self.policy_retriever.run(
            normalized_summary=normalized_summary,
            validated_context=validated_ctx,
            issue_type=issue_type,
        )
        n_chunks = len(trace.retriever_output.get("retrieved_chunks", []))
        insufficient = trace.retriever_output.get("insufficient_evidence", False)
        self._log(trace, "PolicyRetriever",
                  f"Retrieved {n_chunks} chunks, insufficient_evidence={insufficient}")

        # ── Stage 4 & 5: Resolution Writer + Compliance Loop ──
        rewrite_instructions = None

        for cycle in range(MAX_REWRITE_CYCLES + 1):
            # Stage 4: Resolution Writer
            self._log(trace, "ResolutionWriter",
                      f"Generating resolution (cycle {cycle + 1})...")
            trace.resolution_output = self.resolution_writer.run(
                normalized_summary=normalized_summary,
                validated_context=validated_ctx,
                retrieved_chunks=trace.retriever_output,
                triage_output=trace.triage_output,
                rewrite_instructions=rewrite_instructions,
            )
            decision = trace.resolution_output.get("decision", "abstain")
            self._log(trace, "ResolutionWriter", f"Decision: {decision}")

            # If decision is abstain or escalate from the writer, skip compliance
            if decision in ("abstain", "escalate"):
                trace.compliance_output = {
                    "verdict": "pass" if decision == "abstain" else "escalate",
                    "failures": [],
                    "flags": [],
                }
                break

            # Stage 5: Compliance Check
            self._log(trace, "Compliance", f"Auditing resolution (cycle {cycle + 1})...")
            trace.compliance_output = self.compliance.run(
                resolution_output=trace.resolution_output,
                retrieved_chunks=trace.retriever_output,
                validated_context=validated_ctx,
                triage_output=trace.triage_output,
                context_flags=ctx_flags,
            )
            verdict = trace.compliance_output.get("verdict", "pass")
            failures = trace.compliance_output.get("failures", [])
            self._log(trace, "Compliance",
                      f"Verdict: {verdict}, Failures: {failures}")

            if verdict == "pass":
                trace.rewrite_cycles = cycle
                break
            elif verdict == "escalate":
                trace.rewrite_cycles = cycle
                break
            elif verdict == "rewrite" and cycle < MAX_REWRITE_CYCLES:
                rewrite_instructions = trace.compliance_output.get(
                    "rewrite_instructions", "Address all failures."
                )
                self._log(trace, "Compliance",
                          f"Requesting rewrite: {rewrite_instructions[:100]}...")
                trace.rewrite_cycles = cycle + 1
            else:
                # Max rewrites exceeded → auto-escalate
                self._log(trace, "Compliance",
                          "Max rewrite cycles exceeded → auto-escalate")
                trace.compliance_output["verdict"] = "escalate"
                trace.compliance_output["escalation_reason"] = (
                    "Max rewrite cycles exceeded"
                )
                trace.rewrite_cycles = cycle + 1
                break

        # ── Stage 6: Escalation (if needed) ──
        compliance_verdict = trace.compliance_output.get("verdict", "pass")
        writer_decision = trace.resolution_output.get("decision", "abstain")

        if compliance_verdict == "escalate" or writer_decision == "escalate":
            self._log(trace, "Escalation", "Generating escalation package...")
            trace.escalation_output = self.escalation.run(
                ticket_text=ticket_text,
                triage_output=trace.triage_output,
                validated_context=validated_ctx,
                retrieved_chunks=trace.retriever_output,
                resolution_output=trace.resolution_output,
                compliance_output=trace.compliance_output,
            )
            trace.final_decision = "escalate"
            trace.pipeline_status = "escalated"
        elif writer_decision == "abstain":
            trace.final_decision = "abstain"
            trace.pipeline_status = "abstained"
        else:
            trace.final_decision = writer_decision
            trace.pipeline_status = "completed"
            # Use compliance-approved output if available
            approved = trace.compliance_output.get("approved_output")
            if approved:
                trace.resolution_output = approved

        trace.execution_time_seconds = time.time() - start_time
        self._log(trace, "Pipeline",
                  f"Finished: {trace.pipeline_status} → {trace.final_decision} "
                  f"({trace.execution_time_seconds:.1f}s)")

        return trace
