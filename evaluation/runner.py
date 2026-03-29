# Evaluation Runner
# Runs all 25 tickets through the pipeline and computes metrics

import json
import os
import sys
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.test_set import EVALUATION_TICKETS, get_ticket_by_id
from orchestrator import SupportPipeline, PipelineTrace
from retriever import HybridRetriever
from config import VECTORSTORE_DIR


class EvaluationMetrics:
    """Computes and stores evaluation metrics across all tickets."""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def add_result(self, ticket: dict, trace: PipelineTrace):
        """Add a single ticket result."""
        expected = ticket["expected_decision"]
        actual = trace.final_decision

        # Citation coverage: count claims with citation backing
        resolution = trace.resolution_output
        # unwrap nested resolution_output if present
        if "resolution_output" in resolution:
            resolution = resolution["resolution_output"]
        citations = resolution.get("citations", [])
        unsupported = resolution.get("unsupported_claims", [])

        n_citations = len(citations)
        n_unsupported = len(unsupported)
        total_claims = n_citations + n_unsupported if n_citations + n_unsupported > 0 else 1

        citation_coverage = n_citations / total_claims if total_claims > 0 else 1.0
        unsupported_rate = n_unsupported / total_claims if total_claims > 0 else 0.0

        self.results.append({
            "ticket_id": ticket["id"],
            "category": ticket["category"],
            "expected_decision": expected,
            "actual_decision": actual,
            "decision_correct": self._decisions_match(expected, actual),
            "citation_coverage": citation_coverage,
            "unsupported_claim_rate": unsupported_rate,
            "n_citations": n_citations,
            "n_unsupported": n_unsupported,
            "rewrite_cycles": trace.rewrite_cycles,
            "execution_time": trace.execution_time_seconds,
            "pipeline_status": trace.pipeline_status,
            "key_challenge": ticket["key_challenge"],
        })

    def _decisions_match(self, expected: str, actual: str) -> bool:
        """Check if the actual decision matches expected, with some flexibility."""
        if expected == actual:
            return True
        # 'clarify' maps to 'needs_clarification' or 'abstain'
        if expected == "clarify" and actual in ("clarify", "abstain", "needs_clarification"):
            return True
        # 'escalate' should always be escalate
        if expected == "escalate" and actual == "escalate":
            return True
        return False

    def compute_summary(self) -> Dict[str, Any]:
        """Compute aggregate metrics."""
        if not self.results:
            return {"error": "No results to compute"}

        n = len(self.results)
        correct = sum(1 for r in self.results if r["decision_correct"])

        # Citation coverage
        coverage_values = [r["citation_coverage"] for r in self.results
                          if r["actual_decision"] not in ("abstain", "clarify")]
        avg_citation_coverage = (
            sum(coverage_values) / len(coverage_values)
            if coverage_values else 0.0
        )

        # Unsupported claim rate
        unsupported_values = [r["unsupported_claim_rate"] for r in self.results
                            if r["actual_decision"] not in ("abstain", "clarify")]
        avg_unsupported_rate = (
            sum(unsupported_values) / len(unsupported_values)
            if unsupported_values else 0.0
        )

        # Escalation accuracy for conflict and not-in-policy cases
        escalation_cases = [r for r in self.results
                           if r["expected_decision"] in ("escalate", "abstain")]
        escalation_correct = sum(
            1 for r in escalation_cases if r["decision_correct"]
        )
        escalation_rate = (
            escalation_correct / len(escalation_cases)
            if escalation_cases else 0.0
        )

        # Per-category accuracy
        categories = set(r["category"] for r in self.results)
        category_accuracy = {}
        for cat in categories:
            cat_results = [r for r in self.results if r["category"] == cat]
            cat_correct = sum(1 for r in cat_results if r["decision_correct"])
            category_accuracy[cat] = {
                "total": len(cat_results),
                "correct": cat_correct,
                "accuracy": cat_correct / len(cat_results) if cat_results else 0.0,
            }

        avg_time = sum(r["execution_time"] for r in self.results) / n

        return {
            "total_tickets": n,
            "overall_accuracy": correct / n,
            "correct_decisions": correct,
            "citation_coverage_rate": avg_citation_coverage,
            "unsupported_claim_rate": avg_unsupported_rate,
            "escalation_accuracy": escalation_rate,
            "category_accuracy": category_accuracy,
            "avg_execution_time_seconds": avg_time,
            "avg_rewrite_cycles": sum(r["rewrite_cycles"] for r in self.results) / n,
            "targets": {
                "citation_coverage_target": ">90%",
                "unsupported_claim_target": "<5%",
                "escalation_accuracy_target": "100%",
            },
        }

    def format_report(self) -> str:
        """Generate a formatted evaluation report."""
        summary = self.compute_summary()
        lines = [
            "=" * 80,
            "MULTI-AGENT RAG SUPPORT RESOLUTION — EVALUATION REPORT",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 80,
            "",
            "─── AGGREGATE METRICS ───",
            f"  Total tickets evaluated:      {summary['total_tickets']}",
            f"  Overall decision accuracy:    {summary['overall_accuracy']:.1%} ({summary['correct_decisions']}/{summary['total_tickets']})",
            f"  Citation coverage rate:       {summary['citation_coverage_rate']:.1%} (target >90%)",
            f"  Unsupported claim rate:       {summary['unsupported_claim_rate']:.1%} (target <5%)",
            f"  Escalation accuracy:          {summary['escalation_accuracy']:.1%} (target 100%)",
            f"  Avg execution time:           {summary['avg_execution_time_seconds']:.1f}s",
            f"  Avg rewrite cycles:           {summary['avg_rewrite_cycles']:.2f}",
            "",
            "─── PER-CATEGORY ACCURACY ───",
        ]

        for cat, stats in sorted(summary["category_accuracy"].items()):
            lines.append(
                f"  {cat:20s}  {stats['correct']}/{stats['total']} "
                f"({stats['accuracy']:.0%})"
            )

        lines.extend([
            "",
            "─── PER-TICKET RESULTS ───",
            f"  {'ID':>3s}  {'Cat':12s}  {'Expected':10s}  {'Actual':10s}  {'Match':5s}  {'Cites':5s}  {'Time':6s}  Challenge",
            "  " + "─" * 90,
        ])

        for r in self.results:
            match_str = "✓" if r["decision_correct"] else "✗"
            lines.append(
                f"  {r['ticket_id']:3d}  "
                f"{r['category']:12s}  "
                f"{r['expected_decision']:10s}  "
                f"{r['actual_decision']:10s}  "
                f"  {match_str}    "
                f"{r['n_citations']:3d}   "
                f"{r['execution_time']:5.1f}s  "
                f"{r['key_challenge']}"
            )

        lines.extend([
            "",
            "=" * 80,
        ])

        return "\n".join(lines)


def run_full_evaluation(
    pipeline: SupportPipeline,
    ticket_ids: Optional[List[int]] = None,
    save_traces: bool = True,
) -> EvaluationMetrics:
    """Run evaluation on all (or selected) tickets."""
    metrics = EvaluationMetrics()

    tickets = EVALUATION_TICKETS
    if ticket_ids:
        tickets = [get_ticket_by_id(tid) for tid in ticket_ids]

    traces = []
    for i, ticket in enumerate(tickets):
        print(f"\n{'━'*70}")
        print(f"Ticket {ticket['id']}/{len(tickets)}: {ticket['ticket_text'][:60]}...")
        print(f"Expected: {ticket['expected_decision']} | Category: {ticket['category']}")
        print(f"{'━'*70}")

        trace = pipeline.run(
            ticket_text=ticket["ticket_text"],
            order_context=ticket.get("order_context"),
        )

        metrics.add_result(ticket, trace)
        traces.append({
            "ticket_id": ticket["id"],
            "trace": trace.to_dict(),
        })

        print(f"  → Decision: {trace.final_decision} "
              f"(expected: {ticket['expected_decision']})")
        time.sleep(4)
    # Print report
    report = metrics.format_report()
    print(report)

    # Save traces and report
    if save_traces:
        os.makedirs("evaluation/results", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        with open(f"evaluation/results/traces_{timestamp}.json", "w") as f:
            json.dump(traces, f, indent=2, default=str)

        with open(f"evaluation/results/report_{timestamp}.txt", "w") as f:
            f.write(report)

        summary = metrics.compute_summary()
        with open(f"evaluation/results/metrics_{timestamp}.json", "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\nResults saved to evaluation/results/")

    return metrics


def run_example_traces(pipeline: SupportPipeline) -> List[PipelineTrace]:
    """Run 3 highlighted example traces: exception, conflict, abstention."""
    example_ids = [9, 15, 18]  # Exception, Conflict, Not-in-policy
    traces = []

    for tid in example_ids:
        ticket = get_ticket_by_id(tid)
        print(f"\n{'═'*70}")
        print(f"EXAMPLE TRACE — Ticket {tid}: {ticket['key_challenge']}")
        print(f"{'═'*70}")

        trace = pipeline.run(
            ticket_text=ticket["ticket_text"],
            order_context=ticket.get("order_context"),
        )
        traces.append(trace)

        print(f"\n  Final decision: {trace.final_decision}")
        print(f"  Pipeline status: {trace.pipeline_status}")
        print(f"  Rewrite cycles: {trace.rewrite_cycles}")

        # Print key outputs
        if trace.resolution_output:
            print(f"\n  Resolution rationale: {trace.resolution_output.get('rationale', 'N/A')[:200]}")
            print(f"  Customer draft: {trace.resolution_output.get('customer_response_draft', 'N/A')[:200]}")

        if trace.escalation_output:
            brief = trace.escalation_output.get("escalation_brief", {})
            print(f"\n  Escalation summary: {brief.get('one_line_summary', 'N/A')}")
            print(f"  Recommended team: {brief.get('recommended_team', 'N/A')}")
            print(f"  Priority: {brief.get('priority', 'N/A')}")

    return traces


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run evaluation")
    parser.add_argument("--tickets", nargs="*", type=int,
                        help="Specific ticket IDs to run (default: all)")
    parser.add_argument("--examples-only", action="store_true",
                        help="Run only the 3 example traces")
    args = parser.parse_args()

    # Initialize retriever and pipeline
    print("Loading retriever index...")
    retriever = HybridRetriever()
    if os.path.exists(os.path.join(VECTORSTORE_DIR, "chunks.json")):
        retriever.load_index()
    else:
        print("Index not found. Building from policy documents...")
        from chunker import load_all_policies
        chunks = load_all_policies()
        retriever.build_index(chunks)
        retriever.save_index()

    pipeline = SupportPipeline(retriever)

    if args.examples_only:
        run_example_traces(pipeline)
    else:
        run_full_evaluation(pipeline, ticket_ids=args.tickets)
