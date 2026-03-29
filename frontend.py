"""
E-commerce Support Resolution Agent — Gradio Frontend
Purple Merit Technologies — AI/ML Engineer Intern Assessment 2
"""

import gradio as gr
import json
import time
import os
import sys

# Load real pipeline
from orchestrator import SupportPipeline, PipelineTrace
from retriever import HybridRetriever
from config import VECTORSTORE_DIR, MAX_REWRITE_CYCLES

print("Loading retriever index for Gradio frontend...")
retriever = HybridRetriever()
index_path = os.path.join(VECTORSTORE_DIR, "chunks.json")
if os.path.exists(index_path):
    retriever.load_index()
else:
    print("WARNING: Index not found! Please run `python main.py --build-index` first.")

pipeline = SupportPipeline(retriever)


# ---------------------------------------------------------------------------
# Main pipeline orchestrator
# ---------------------------------------------------------------------------

def run_pipeline(ticket_text: str, order_json: str):
    """
    Runs all 6 agents in sequence, yielding progress updates after each step.
    Each yield returns: (trace_log, citations_md, resolution_json, status_html)
    """
    if not ticket_text.strip():
        yield "Error: Ticket text is required.", "", "{}", status_badge("error", "Error")
        return

    # Parse order context
    try:
        order_context = json.loads(order_json) if order_json.strip() else {}
    except json.JSONDecodeError:
        order_context = {}

    trace_log = ""
    citations_md = "_Waiting for retriever..._"
    resolution_json = "{}"

    def agent_header(n, name, badge=""):
        color = {"Required": "#534AB7", "Bonus": "#0F6E56"}.get(badge, "#534AB7")
        return f"\n{'─'*52}\n[Agent {n}] {name}\n{'─'*52}\n"

    trace = PipelineTrace(ticket_text=ticket_text, order_context=order_context)

    # ── Agent 1: Triage ──────────────────────────────────────
    trace_log += agent_header(1, "Triage Agent", "Required")
    trace_log += "Running classification...\n"
    yield trace_log, citations_md, resolution_json, status_badge("running", "Triage agent")

    trace.triage_output = pipeline.triage.run(ticket_text, order_context)
    issue_type = trace.triage_output.get("issue_type", "OTHER")
    fraud_signal = trace.triage_output.get("fraud_signal", False)

    trace_log += f"  Issue type    : {issue_type} ({trace.triage_output.get('confidence', 'LOW')})\n"
    trace_log += f"  Fraud signal  : {fraud_signal}\n"
    trace_log += f"  Missing fields: {trace.triage_output.get('missing_fields', [])}\n"
    
    if trace.triage_output.get("clarifying_questions"):
        trace_log += f"  Questions     : {'; '.join(trace.triage_output.get('clarifying_questions', []))}\n"
        
    trace_log += "  Status: COMPLETE\n"
    yield trace_log, citations_md, resolution_json, status_badge("running", "Order context interpreter")

    if trace.triage_output.get("clarifying_questions") and not order_context:
        trace_log += "  Needs clarification. Stopping pipeline.\n"
        resolution_json = json.dumps(trace.to_dict(), indent=2, default=str)
        yield trace_log, citations_md, resolution_json, status_badge("done", "Needs clarification")
        return

    # ── Agent 2: Order Context Interpreter ──────────────────
    trace_log += agent_header(2, "Order Context Interpreter", "Bonus")
    trace_log += "Validating and enriching order context...\n"
    yield trace_log, citations_md, resolution_json, status_badge("running", "Order context interpreter")

    trace.order_context_output = pipeline.order_context.run(order_context, trace.triage_output)
    vc = trace.order_context_output.get("validated_context", order_context)
    ctx_flags = trace.order_context_output.get("flags", [])

    trace_log += f"  Exception cat : {vc.get('is_exception_category', False)}\n"
    trace_log += f"  Regional check: {vc.get('requires_regional_check', False)}\n"
    trace_log += f"  Days delivered: {vc.get('days_since_delivery', 'N/A')}\n"
    trace_log += f"  Flags         : {ctx_flags}\n"
    trace_log += "  Status: COMPLETE\n"
    yield trace_log, citations_md, resolution_json, status_badge("running", "Policy retriever")

    # ── Agent 3: Policy Retriever ────────────────────────────
    trace_log += agent_header(3, "Policy Retriever Agent", "Required")
    trace_log += "Running hybrid BM25 + semantic search...\n"
    yield trace_log, citations_md, resolution_json, status_badge("running", "Policy retriever")

    normalized_summary = trace.triage_output.get("normalized_summary", ticket_text)
    trace.retriever_output = pipeline.policy_retriever.run(
        normalized_summary=normalized_summary,
        validated_context=vc,
        issue_type=issue_type
    )
    chunks = trace.retriever_output.get("retrieved_chunks", [])
    
    trace_log += f"  Chunks found  : {len(chunks)}\n"
    trace_log += f"  Insufficient  : {trace.retriever_output.get('insufficient_evidence', False)}\n"
    for c in chunks:
        trace_log += f"  [{c.get('relevance_score', 0):.2f}] {c.get('doc_title', '')} — {c.get('section', '')}\n"
    trace_log += "  Status: COMPLETE\n"

    citations_md = build_citations_md(chunks)
    yield trace_log, citations_md, resolution_json, status_badge("running", "Resolution writer")

    # ── Agent 4 & 5: Resolution Writer & Compliance ───────────────────────────
    rewrite_instructions = None
    
    for cycle in range(MAX_REWRITE_CYCLES + 1):
        # Stage 4: Resolution Writer
        trace_log += agent_header(4, f"Resolution Writer Agent (Cycle {cycle+1})", "Required")
        trace_log += "Drafting evidence-only resolution...\n"
        yield trace_log, citations_md, resolution_json, status_badge("running", f"Writing (C{cycle+1})")

        trace.resolution_output = pipeline.resolution_writer.run(
            normalized_summary=normalized_summary,
            validated_context=vc,
            retrieved_chunks=trace.retriever_output,
            triage_output=trace.triage_output,
            rewrite_instructions=rewrite_instructions
        )
        decision = trace.resolution_output.get("decision", "abstain").upper()
        
        trace_log += f"  Decision      : {decision}\n"
        trace_log += f"  Unsupported   : {trace.resolution_output.get('unsupported_claims', [])}\n"
        trace_log += "  Status: COMPLETE\n"
        
        if decision.lower() in ("abstain", "escalate"):
            trace.compliance_output = {"verdict": "pass" if decision.lower() == "abstain" else "escalate", "failures": [], "flags": []}
            break

        # Stage 5: Compliance Agent
        trace_log += agent_header(5, f"Compliance / Safety Agent (Cycle {cycle+1})", "Required")
        trace_log += "Auditing citations, PII, decision integrity...\n"
        yield trace_log, citations_md, resolution_json, status_badge("running", f"Compliance (C{cycle+1})")

        trace.compliance_output = pipeline.compliance.run(
            resolution_output=trace.resolution_output,
            retrieved_chunks=trace.retriever_output,
            validated_context=vc,
            triage_output=trace.triage_output,
            context_flags=ctx_flags
        )
        verdict = trace.compliance_output.get("verdict", "pass").lower()
        
        trace_log += f"  Verdict       : {verdict.upper()}\n"
        trace_log += f"  Failures      : {trace.compliance_output.get('failures', [])}\n"
        
        if verdict == "pass":
            trace_log += "  Status: COMPLETE\n"
            break
        elif verdict == "escalate":
            trace_log += "  Status: COMPLETE (Escalated)\n"
            break
        elif verdict == "rewrite" and cycle < MAX_REWRITE_CYCLES:
            rewrite_instructions = trace.compliance_output.get("rewrite_instructions", "Address all failures.")
            trace_log += f"  Sending back to Resolution Writer...\n  Instruction: {rewrite_instructions}\n"
        else:
            trace_log += "  Max rewrite cycles exceeded → auto-escalate\n"
            trace.compliance_output["verdict"] = "escalate"
            trace.compliance_output["escalation_reason"] = "Max rewrite cycles exceeded"
            break

    # ── Agent 6: Escalation (if needed) ──────────────────────
    compliance_verdict = trace.compliance_output.get("verdict", "pass").lower()
    writer_decision = trace.resolution_output.get("decision", "abstain").lower()

    if compliance_verdict == "escalate" or writer_decision == "escalate":
        trace_log += agent_header(6, "Escalation Agent", "Bonus")
        trace_log += "Packaging for human handoff...\n"
        yield trace_log, citations_md, resolution_json, status_badge("running", "Escalating")
        
        trace.escalation_output = pipeline.escalation.run(
            ticket_text=ticket_text,
            triage_output=trace.triage_output,
            validated_context=vc,
            retrieved_chunks=trace.retriever_output,
            resolution_output=trace.resolution_output,
            compliance_output=trace.compliance_output
        )
        brief = trace.escalation_output.get("escalation_brief", {})
        trace_log += f"  Priority      : {brief.get('priority', 'N/A')}\n"
        trace_log += f"  Team          : {brief.get('recommended_team', 'N/A')}\n"
        trace_log += f"  Reason        : {', '.join(brief.get('why_escalated', []))}\n"
        trace_log += "  Status: COMPLETE\n"
        final_decision = "escalate"
    else:
        final_decision = writer_decision

    trace_log += f"\n{'═'*52}\n  PIPELINE COMPLETE\n{'═'*52}\n"

    approved_output = trace.compliance_output.get("approved_output")
    if approved_output:
        trace.resolution_output = approved_output
        
    trace.final_decision = final_decision
    
    resolution_json = json.dumps(trace.to_dict(), indent=2, default=str)
    
    yield trace_log, citations_md, resolution_json, status_badge("done", final_decision)


def build_citations_md(chunks: list) -> str:
    if not chunks:
        return "_No policy chunks retrieved._"
    lines = []
    for i, c in enumerate(chunks, 1):
        score = c.get("relevance_score", 0)
        lines.append(
            f"### {i}. {c.get('doc_title', 'Doc')}\n"
            f"**Section:** {c.get('section', 'Sec')}  \n"
            f"**Relevance:** `{score:.2f}`  \n"
            f"**Chunk ID:** `{c.get('chunk_id', 'id')}`  \n"
            f"**Source:** [{c.get('url', '#')}]({c.get('url', '#')})\n\n"
            f"> {c.get('excerpt', '')}\n"
        )
    return "\n---\n".join(lines)


def status_badge(state: str, label: str) -> str:
    colors = {"running": "#BA7517", "done": "#3B6D11", "error": "#A32D2D"}
    icons  = {"running": "●", "done": "✓", "error": "✗"}
    color  = colors.get(state, "#888")
    icon   = icons.get(state, "●")
    return (
        f'<div style="display:inline-flex;align-items:center;gap:8px;'
        f'padding:6px 14px;border-radius:20px;background:{color}18;'
        f'border:1px solid {color}44;font-size:13px;font-family:monospace;">'
        f'<span style="color:{color};font-size:16px">{icon}</span>'
        f'<span style="color:{color}">{label.upper()}</span></div>'
    )


# ---------------------------------------------------------------------------
# Sample tickets
# ---------------------------------------------------------------------------

EXAMPLES = [
    [
        "My laptop arrived with a cracked screen. I want a full refund immediately.",
        json.dumps({
            "order_date": "2026-03-01",
            "delivery_date": "2026-03-05",
            "item_category": "electronics",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "delivered"
        }, indent=2)
    ],
    [
        "My order shows delivered but I never received it. Tracking says it was signed for but that wasn't me. I want a full refund and I think someone stole it.",
        json.dumps({
            "order_date": "2026-03-10",
            "delivery_date": "2026-03-14",
            "item_category": "electronics",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "delivered"
        }, indent=2)
    ],
    [
        "I saw the same item cheaper at another store. Can you match the price?",
        json.dumps({
            "order_date": "2026-03-20",
            "delivery_date": None,
            "item_category": "apparel",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "placed"
        }, indent=2)
    ],
    [
        "The cookies I ordered arrived completely melted. I want a refund but I already ate them. Is that okay?",
        json.dumps({
            "order_date": "2026-03-18",
            "delivery_date": "2026-03-22",
            "item_category": "perishable",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "delivered"
        }, indent=2)
    ],
]

ORDER_CONTEXT_PLACEHOLDER = json.dumps({
    "order_date": "2026-03-01",
    "delivery_date": "2026-03-05",
    "item_category": "electronics",
    "fulfillment_type": "first-party",
    "shipping_region": "US",
    "order_status": "delivered",
    "payment_method": "credit_card"
}, indent=2)


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
.gradio-container { max-width: 1200px !important; }
.agent-trace textarea { font-family: 'Courier New', monospace !important; font-size: 12px !important; }
.resolution-json textarea { font-family: 'Courier New', monospace !important; font-size: 12px !important; }
footer { display: none !important; }
"""

with gr.Blocks(
    title="E-commerce Support Resolution Agent"
) as demo:

    gr.Markdown(
        """
        # E-commerce Support Resolution Agent
        **Purple Merit Technologies — AI/ML Engineer Intern Assessment 2**

        Multi-agent RAG system with 6 agents: Triage → Order Interpreter → Policy Retriever → Resolution Writer → Compliance → Escalation
        *(Note: Using local Ollama inference. Please be patient while the model responds.)*
        """
    )

    with gr.Row():
        # ── Left column: inputs ──────────────────────────────
        with gr.Column(scale=1):
            gr.Markdown("### Ticket input")
            ticket_input = gr.Textbox(
                label="Customer ticket text",
                placeholder="Describe the customer's issue in free-form text...",
                lines=5,
                max_lines=10
            )
            order_input = gr.Code(
                label="Order context (JSON)",
                language="json",
                value=ORDER_CONTEXT_PLACEHOLDER,
                lines=12
            )
            with gr.Row():
                clear_btn = gr.Button("Clear", variant="secondary", size="sm")
                run_btn   = gr.Button("Run pipeline", variant="primary", size="lg")

            status_display = gr.HTML(
                value=status_badge("done", "Ready"),
                label="Pipeline status"
            )

            gr.Markdown("### Try an example")
            with gr.Column():
                ex_btns = [
                    gr.Button(f"Ticket {i+1}: {['Damaged laptop','Fraud — delivery dispute','Price match request','Melted perishable'][i]}", size="sm")
                    for i in range(4)
                ]

        # ── Right column: outputs ────────────────────────────
        with gr.Column(scale=2):
            with gr.Tabs():
                with gr.TabItem("Agent trace"):
                    trace_output = gr.Textbox(
                        label="Live agent pipeline log",
                        lines=28,
                        max_lines=40,
                        interactive=False,
                        elem_classes=["agent-trace"],
                        placeholder="Agent trace will appear here as the pipeline runs..."
                    )

                with gr.TabItem("Citations"):
                    citations_output = gr.Markdown(
                        value="_Run a ticket to see retrieved policy citations._",
                        label="Retrieved policy chunks"
                    )

                with gr.TabItem("Resolution output (JSON Trace)"):
                    resolution_output = gr.Code(
                        label="Structured pipeline resolution (JSON)",
                        language="json",
                        lines=28,
                        interactive=False,
                        elem_classes=["resolution-json"]
                    )

    # ── Wire up events ────────────────────────────────────────

    def clear_all():
        return "", ORDER_CONTEXT_PLACEHOLDER, "", "_Run a ticket to see retrieved policy citations._", "{}", status_badge("done", "Ready")

    clear_btn.click(
        fn=clear_all,
        outputs=[ticket_input, order_input, trace_output, citations_output, resolution_output, status_display]
    )

    run_btn.click(
        fn=run_pipeline,
        inputs=[ticket_input, order_input],
        outputs=[trace_output, citations_output, resolution_output, status_display]
    )

    # Example button wiring
    for i, btn in enumerate(ex_btns):
        def load_example(idx=i):
            ex = EXAMPLES[idx]
            return ex[0], ex[1]
        btn.click(fn=load_example, outputs=[ticket_input, order_input])

if __name__ == "__main__":
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
