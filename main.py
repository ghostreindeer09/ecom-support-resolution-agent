#!/usr/bin/env python3
"""
Multi-Agent RAG Support Resolution System
==========================================
Entry point for building the index, running single tickets, or running the full evaluation suite.

Usage:
  # Build the vector store index from policy documents
  python main.py --build-index

  # Run a single ticket interactively
  python main.py --ticket "My laptop arrived damaged, I want a refund"

  # Run a specific test ticket by ID
  python main.py --test-ticket 9

  # Run the full 25-ticket evaluation
  python main.py --evaluate

  # Run only the 3 example traces
  python main.py --examples
"""

import argparse
import json
import os
import sys

from config import VECTORSTORE_DIR


def build_index():
    """Build the vector store index from policy documents."""
    from retriever import build_and_save_index
    print("Building vector store index...")
    retriever = build_and_save_index()
    print("Done. Index saved to:", VECTORSTORE_DIR)
    return retriever


def get_retriever():
    """Load or build the retriever."""
    from retriever import HybridRetriever

    retriever = HybridRetriever()
    index_path = os.path.join(VECTORSTORE_DIR, "chunks.json")

    if os.path.exists(index_path):
        retriever.load_index()
    else:
        print("Index not found. Building from policy documents...")
        from chunker import load_all_policies
        chunks = load_all_policies()
        retriever.build_index(chunks)
        retriever.save_index()

    return retriever


def run_single_ticket(ticket_text: str, order_context: dict = None):
    """Run a single ticket through the pipeline."""
    from orchestrator import SupportPipeline

    retriever = get_retriever()
    pipeline = SupportPipeline(retriever)

    trace = pipeline.run(ticket_text, order_context)

    print(f"\n{'='*60}")
    print("FINAL RESULT")
    print(f"{'='*60}")
    print(f"Decision: {trace.final_decision}")
    print(f"Status: {trace.pipeline_status}")
    print(f"Rewrite cycles: {trace.rewrite_cycles}")
    print(f"Time: {trace.execution_time_seconds:.1f}s")

    if trace.resolution_output:
        print(f"\nRationale: {trace.resolution_output.get('rationale', 'N/A')}")
        print(f"\nCustomer draft:\n{trace.resolution_output.get('customer_response_draft', 'N/A')}")

    if trace.escalation_output:
        brief = trace.escalation_output.get("escalation_brief", {})
        print(f"\nEscalation: {brief.get('one_line_summary', 'N/A')}")
        print(f"Team: {brief.get('recommended_team', 'N/A')}")
        print(f"Priority: {brief.get('priority', 'N/A')}")
        print(f"\nHolding message:\n{trace.escalation_output.get('customer_holding_message', 'N/A')}")

    return trace


def run_test_ticket(ticket_id: int):
    """Run a specific evaluation test ticket."""
    from evaluation.test_set import get_ticket_by_id
    from orchestrator import SupportPipeline

    ticket = get_ticket_by_id(ticket_id)
    retriever = get_retriever()
    pipeline = SupportPipeline(retriever)

    print(f"Running test ticket {ticket_id}: {ticket['ticket_text'][:60]}...")
    print(f"Expected decision: {ticket['expected_decision']}")
    print(f"Key challenge: {ticket['key_challenge']}")

    trace = pipeline.run(ticket["ticket_text"], ticket.get("order_context"))

    match = "✓ MATCH" if trace.final_decision == ticket["expected_decision"] else "✗ MISMATCH"
    print(f"\nResult: {trace.final_decision} (expected: {ticket['expected_decision']}) → {match}")

    return trace


def run_evaluation(ticket_ids=None):
    """Run the full evaluation suite."""
    from orchestrator import SupportPipeline
    from evaluation.runner import run_full_evaluation

    retriever = get_retriever()
    pipeline = SupportPipeline(retriever)
    run_full_evaluation(pipeline, ticket_ids=ticket_ids)


def run_examples():
    """Run the 3 example traces."""
    from orchestrator import SupportPipeline
    from evaluation.runner import run_example_traces

    retriever = get_retriever()
    pipeline = SupportPipeline(retriever)
    run_example_traces(pipeline)


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent RAG Support Resolution System"
    )
    parser.add_argument("--build-index", action="store_true",
                        help="Build the vector store index from policy documents")
    parser.add_argument("--ticket", type=str,
                        help="Run a single ticket (provide the ticket text)")
    parser.add_argument("--test-ticket", type=int,
                        help="Run a specific evaluation test ticket by ID (1-25)")
    parser.add_argument("--evaluate", action="store_true",
                        help="Run the full 25-ticket evaluation suite")
    parser.add_argument("--evaluate-tickets", nargs="*", type=int,
                        help="Evaluate specific ticket IDs only")
    parser.add_argument("--examples", action="store_true",
                        help="Run the 3 example traces (tickets 9, 15, 18)")

    args = parser.parse_args()

    if args.build_index:
        build_index()
    elif args.ticket:
        run_single_ticket(args.ticket)
    elif args.test_ticket:
        run_test_ticket(args.test_ticket)
    elif args.evaluate:
        run_evaluation()
    elif args.evaluate_tickets:
        run_evaluation(ticket_ids=args.evaluate_tickets)
    elif args.examples:
        run_examples()
    else:
        parser.print_help()
        print("\nQuick start:")
        print("  1. Create .env file with OPENAI_API_KEY=your_key")
        print("  2. python main.py --build-index")
        print("  3. python main.py --test-ticket 1")
        print("  4. python main.py --evaluate")


if __name__ == "__main__":
    main()
