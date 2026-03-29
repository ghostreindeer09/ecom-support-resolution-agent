# Escalation Procedures and Guidelines

**Document ID:** POL-ESC-017
**Effective Date:** January 1, 2026
**Last Updated:** March 15, 2026
**Applies To:** All customer support escalation scenarios

---

## Section 1: Escalation Triggers

A case must be escalated from frontline support to the appropriate specialist team when any of the following conditions are met:

### 1.1 Automatic Escalation (Required — No Agent Discretion)
1. **Fraud signal detected**: Any case where fraud indicators are present must be escalated to the fraud investigation team immediately
2. **Regional law cited**: Any case where the customer references a specific consumer protection law, regardless of whether the agent believes it applies
3. **Policy conflict detected**: Any case where two or more internal policies provide contradictory guidance for the same situation
4. **Order value exceeds $500**: Refund or dispute decisions for orders above $500 require supervisor approval
5. **Customer threatens legal action**: Any case where the customer explicitly states they will pursue legal action
6. **Undisclosed fee dispute**: Any case where the customer claims a fee was not disclosed at the point of purchase
7. **Repeat failures**: If the automated resolution system attempts to resolve a case twice and fails (e.g., compliance review fails twice), the case must be escalated automatically

### 1.2 Discretionary Escalation (Agent Judgment)
1. **Complex multi-order situations**: Cases spanning multiple orders or subscription periods that exceed normal complexity
2. **High-value customer requests**: Requests from customers with long account histories or high lifetime value that may warrant exceptions outside standard policy
3. **Unusual circumstances**: Cases with unusual facts that don't fit neatly into any policy category
4. **Customer dissatisfaction**: If the customer has expressed significant dissatisfaction with a policy-compliant resolution and the agent believes a supervisor review is warranted

---

## Section 2: Escalation Teams

Cases are escalated to the following specialist teams based on the nature of the issue:

### Senior Support
- Handles: Complex customer situations, policy edge cases, customer retention cases
- Response time: Within 4 hours during business hours
- Authority: Can approve exceptions up to 150% of the standard policy allowance
- Contact: Internal escalation queue — "senior_support"

### Legal Compliance
- Handles: Regional law conflicts, consumer protection claims, undisclosed fee disputes
- Response time: Within 1 business day
- Authority: Can override any platform policy when required by law
- Contact: Internal escalation queue — "legal"

### Fraud Investigation
- Handles: Suspected fraudulent claims, account abuse patterns, delivery disputes with fraud signals
- Response time: Within 1–2 business days
- Authority: Can deny claims, restrict accounts, refer to law enforcement
- Contact: Internal escalation queue — "fraud"

### Billing and Payments
- Handles: Double charges, chargeback management, payment processing errors
- Response time: Within 4 hours during business hours
- Authority: Can issue refunds, reverse charges, coordinate with payment processors
- Contact: Internal escalation queue — "billing"

### Account Management
- Handles: Subscription issues, repeat fulfillment errors, high-value customer relationships
- Response time: Within 1 business day
- Authority: Can adjust subscription terms, issue extended credits, coordinate with fulfillment operations
- Contact: Internal escalation queue — "account_management"

---

## Section 3: Escalation Package Requirements

When escalating a case, the following information must be included in the escalation package:

**Required fields:**
1. **One-line summary**: A single sentence (max 20 words) describing the situation
2. **Reason for escalation**: The specific trigger(s) that caused the escalation
3. **Customer request**: What the customer is asking for
4. **Actions taken so far**: What resolution was attempted and why it was insufficient
5. **Relevant policy references**: The policy sections that apply (or conflict)
6. **Priority level**: URGENT, HIGH, or NORMAL (see Section 4)

**Optional but helpful:**
7. Policy chunks with citations that were retrieved during the resolution attempt
8. Customer communication history (recent messages)
9. Account flags or notes from previous interactions

---

## Section 4: Priority Levels

### URGENT
- Assigned when: fraud signal present, regional law conflict, customer safety issue, data breach
- Response expectation: Within 2 hours during business hours, next business day for after-hours
- Customer communication: Holding message with acknowledgment of urgency — "We're treating your case as a priority"

### HIGH
- Assigned when: compliance check failed twice, conflicting policies detected, order value exceeds $1,000, customer has threatened to escalate externally
- Response expectation: Within 4 hours during business hours
- Customer communication: Holding message with specific timeline — "You'll hear back within 1 business day"

### NORMAL
- Assigned when: standard policy edge case, discretionary escalation, customer preference
- Response expectation: Within 1 business day
- Customer communication: Standard holding message — "You'll hear back within 1–2 business days"

---

## Section 5: Escalation Holding Messages

Standard holding messages for customers during escalation:

**Template 1 — General:**
"Thank you for getting in touch. I've referred your case to our specialist team to make sure we handle it correctly. You'll receive a response within [timeline]. We appreciate your patience."

**Template 2 — Complex case:**
"I want to make sure we get this right for you. I've asked our specialist team to review your case. They'll reach out to you directly within [timeline] with a resolution. In the meantime, if you have any additional information to share, please reply to this message."

**Template 3 — Fraud-flagged (neutral):**
"Thank you for your patience. Your case requires a bit of additional review by our team. You'll hear back within 1–2 business days. We appreciate you bearing with us."

**Critical rule**: Holding messages must never:
- Imply a specific outcome ("We'll get you your refund soon")
- Reveal the reason for escalation to the specialist team
- Contain any PII (order numbers, email addresses, etc.)
- Promise specific compensation or resolution
