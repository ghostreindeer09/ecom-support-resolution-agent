# Evaluation Test Set — 25 Support Tickets
# Structured test cases with expected decisions and evaluation criteria

EVALUATION_TICKETS = [
    # ═══════════════════════════════════════════════════════════════════════════
    # STANDARD CASES (1–8)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": 1,
        "category": "standard",
        "ticket_text": "Hi, I received my laptop yesterday and the screen is completely cracked. The packaging was also damaged. I'd like a full refund please.",
        "order_context": {
            "order_date": "2026-03-20",
            "delivery_date": "2026-03-26",
            "item_category": "electronics",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "delivered",
        },
        "expected_decision": "approve",
        "key_challenge": "Straightforward damaged-item claim",
    },
    {
        "id": 2,
        "category": "standard",
        "ticket_text": "My package has been showing 'in transit' for 10 days now with no updates. I ordered a jacket and it seems like it's lost. Can you help?",
        "order_context": {
            "order_date": "2026-03-10",
            "delivery_date": None,
            "item_category": "apparel",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "shipped",
        },
        "expected_decision": "approve",
        "key_challenge": "Lost package — standard SLA threshold",
    },
    {
        "id": 3,
        "category": "standard",
        "ticket_text": "I just placed an order about 20 minutes ago but I changed my mind. Can I cancel it? It's for a dress.",
        "order_context": {
            "order_date": "2026-03-27",
            "delivery_date": None,
            "item_category": "apparel",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "placed",
        },
        "expected_decision": "approve",
        "key_challenge": "Pre-fulfillment cancellation window",
    },
    {
        "id": 4,
        "category": "standard",
        "ticket_text": "I forgot to apply my coupon code SAVE20 at checkout. The order was placed 2 hours ago. Can you apply the discount retroactively?",
        "order_context": {
            "order_date": "2026-03-27",
            "delivery_date": None,
            "item_category": "electronics",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "placed",
        },
        "expected_decision": "deny",
        "key_challenge": "Retroactive coupon application",
    },
    {
        "id": 5,
        "category": "standard",
        "ticket_text": "I ordered a blue wool sweater but received a red cotton one. This is clearly the wrong item. I need the correct one sent to me ASAP.",
        "order_context": {
            "order_date": "2026-03-15",
            "delivery_date": "2026-03-22",
            "item_category": "apparel",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "delivered",
        },
        "expected_decision": "approve",
        "key_challenge": "Wrong item → replacement path",
    },
    {
        "id": 6,
        "category": "standard",
        "ticket_text": "My monitor was shipped yesterday and I just realized I put the wrong delivery address. Can you change it to my office address instead?",
        "order_context": {
            "order_date": "2026-03-25",
            "delivery_date": None,
            "item_category": "electronics",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "shipped",
        },
        "expected_decision": "deny",
        "key_challenge": "Address change after shipment",
    },
    {
        "id": 7,
        "category": "standard",
        "ticket_text": "The dress I got from one of your marketplace sellers is not the same color shown in the photos. It was listed as burgundy but it's clearly pink. I want a full refund.",
        "order_context": {
            "order_date": "2026-03-10",
            "delivery_date": "2026-03-18",
            "item_category": "apparel",
            "fulfillment_type": "marketplace",
            "shipping_region": "US",
            "order_status": "delivered",
        },
        "expected_decision": "partial",
        "key_challenge": "Marketplace seller — different policy applies",
    },
    {
        "id": 8,
        "category": "standard",
        "ticket_text": "I was charged twice for my headphones order — I can see two identical charges of $149.99 on my credit card statement. Please refund the duplicate charge.",
        "order_context": {
            "order_date": "2026-03-20",
            "delivery_date": "2026-03-25",
            "item_category": "electronics",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "delivered",
        },
        "expected_decision": "approve",
        "key_challenge": "Payment dispute — billing error",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # EXCEPTION-HEAVY CASES (9–14)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": 9,
        "category": "exception",
        "ticket_text": "My gourmet chocolate box arrived completely melted — it was left in the sun for hours. I want a full refund and I obviously can't return melted chocolate, so I'd like to keep it (or what's left of it). Also, the non-perishable gift box it came in was damaged too, and I want a refund for that as well without sending it back.",
        "order_context": {
            "order_date": "2026-03-20",
            "delivery_date": "2026-03-25",
            "item_category": "perishable",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "delivered",
        },
        "expected_decision": "partial",
        "key_challenge": "Perishable exception + keep-item request for non-perishables",
    },
    {
        "id": 10,
        "category": "exception",
        "ticket_text": "I bought an electric toothbrush and I've been using it for a week. The bristles fell out after 3 uses. It's clearly defective. I want a full refund.",
        "order_context": {
            "order_date": "2026-03-15",
            "delivery_date": "2026-03-18",
            "item_category": "hygiene",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "delivered",
        },
        "expected_decision": "deny",
        "key_challenge": "Hygiene items — final sale exception for opened items",
    },
    {
        "id": 11,
        "category": "exception",
        "ticket_text": "I bought a dress during your clearance sale 5 days ago. I changed my mind and want to return it. It still has the tags on.",
        "order_context": {
            "order_date": "2026-03-18",
            "delivery_date": "2026-03-22",
            "item_category": "apparel",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "delivered",
            "final_sale": True,
        },
        "expected_decision": "deny",
        "key_challenge": "Final sale — no returns permitted",
    },
    {
        "id": 12,
        "category": "exception",
        "ticket_text": "I bought a software package (Adobe Creative Suite, boxed version). I opened the box and installed it but it crashes every time I try to open Photoshop. The seal is broken because I had to open it to install. I want a refund.",
        "order_context": {
            "order_date": "2026-03-10",
            "delivery_date": "2026-03-14",
            "item_category": "software",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "delivered",
        },
        "expected_decision": "escalate",
        "key_challenge": "Opened software + defect claim conflict",
    },
    {
        "id": 13,
        "category": "exception",
        "ticket_text": "I'm a customer based in Germany. I received a jacket 45 days ago and I want to return it. I know your policy says 30 days, but EU consumer protection law gives me additional rights. Please process my return.",
        "order_context": {
            "order_date": "2026-02-01",
            "delivery_date": "2026-02-10",
            "item_category": "apparel",
            "fulfillment_type": "first-party",
            "shipping_region": "EU",
            "order_status": "delivered",
        },
        "expected_decision": "escalate",
        "key_challenge": "Regional law vs store policy conflict",
    },
    {
        "id": 14,
        "category": "exception",
        "ticket_text": "I received an email last week with a VIP offer for 40% off my next purchase. But when I enter the code at checkout, it says 'invalid code'. I don't have the email anymore, I deleted it. Can you still honor the discount?",
        "order_context": {
            "order_date": None,
            "delivery_date": None,
            "item_category": "apparel",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "placed",
        },
        "expected_decision": "clarify",
        "key_challenge": "Unverifiable promotional claim",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFLICT CASES (15–17)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": 15,
        "category": "conflict",
        "ticket_text": "I bought a designer handbag from a marketplace seller on your platform. The seller says 'no returns' but your website says '30-day free returns' for all items. The bag has a defect — the zipper is broken. Who do I believe? I want my money back.",
        "order_context": {
            "order_date": "2026-03-05",
            "delivery_date": "2026-03-12",
            "item_category": "apparel",
            "fulfillment_type": "marketplace",
            "shipping_region": "US",
            "order_status": "delivered",
        },
        "expected_decision": "escalate",
        "key_challenge": "Seller policy vs platform policy conflict",
    },
    {
        "id": 16,
        "category": "conflict",
        "ticket_text": "I'm in California and I purchased a final-sale TV that turned out to be defective. Your policy says final sale = no returns, but California consumer protection law says I have rights for defective goods regardless. I want a refund.",
        "order_context": {
            "order_date": "2026-03-01",
            "delivery_date": "2026-03-08",
            "item_category": "electronics",
            "fulfillment_type": "first-party",
            "shipping_region": "US-CA",
            "order_status": "delivered",
        },
        "expected_decision": "escalate",
        "key_challenge": "State law vs final-sale policy",
    },
    {
        "id": 17,
        "category": "conflict",
        "ticket_text": "My expensive camera was marked as delivered and it says someone signed for it, but I was at work all day and nobody was home. I did NOT receive this package and I did not sign for anything. I need a full refund immediately.",
        "order_context": {
            "order_date": "2026-03-10",
            "delivery_date": "2026-03-15",
            "item_category": "electronics",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "delivered",
        },
        "expected_decision": "escalate",
        "key_challenge": "Carrier record vs customer claim — fraud signal",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # NOT-IN-POLICY CASES (18–20)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": 18,
        "category": "not-in-policy",
        "ticket_text": "I found the same laptop on a competitor's website for $200 less. Do you offer price matching? I'd like you to match their price.",
        "order_context": {
            "order_date": "2026-03-20",
            "delivery_date": None,
            "item_category": "electronics",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "placed",
        },
        "expected_decision": "deny",
        "key_challenge": "Price matching — explicitly prohibited by policy",
    },
    {
        "id": 19,
        "category": "not-in-policy",
        "ticket_text": "I have a $50 gift card that I'd like to exchange for cash instead. Is that possible? I don't really shop here anymore.",
        "order_context": {
            "order_date": None,
            "delivery_date": None,
            "item_category": "gift-card",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": None,
        },
        "expected_decision": "deny",
        "key_challenge": "Gift card cash redemption — explicitly prohibited by policy",
    },
    {
        "id": 20,
        "category": "not-in-policy",
        "ticket_text": "Are you guys having any sales next month? I'm looking to buy a new winter coat but want to wait for a deal.",
        "order_context": {
            "order_date": None,
            "delivery_date": None,
            "item_category": "apparel",
            "fulfillment_type": None,
            "shipping_region": "US",
            "order_status": None,
        },
        "expected_decision": "abstain",
        "key_challenge": "Future sale availability — outside policy scope",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # BONUS CASES (21–25)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": 21,
        "category": "standard",
        "ticket_text": "I want to return a shirt I bought 90 days ago. It's been sitting in my closet unworn with tags still on. I just never got around to wearing it.",
        "order_context": {
            "order_date": "2025-12-27",
            "delivery_date": "2026-01-03",
            "item_category": "apparel",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "delivered",
        },
        "expected_decision": "deny",
        "key_challenge": "Expired 30-day refund window",
    },
    {
        "id": 22,
        "category": "exception",
        "ticket_text": "My wireless earbuds stopped working after just 3 uses. The right earbud makes a buzzing sound and won't charge. This seems like a manufacturing defect. I bought them 6 weeks ago.",
        "order_context": {
            "order_date": "2026-02-10",
            "delivery_date": "2026-02-15",
            "item_category": "electronics",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "delivered",
        },
        "expected_decision": "partial",
        "key_challenge": "Store vs manufacturer warranty boundary (past 30 days)",
    },
    {
        "id": 23,
        "category": "conflict",
        "ticket_text": "I returned a TV and was charged a $75 restocking fee. Nobody told me about a restocking fee when I bought it. I don't see it anywhere on the product page or my order confirmation. I want the fee refunded.",
        "order_context": {
            "order_date": "2026-03-01",
            "delivery_date": "2026-03-05",
            "item_category": "electronics",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "returned",
        },
        "expected_decision": "escalate",
        "key_challenge": "Undisclosed fee conflict — potential policy violation",
    },
    {
        "id": 24,
        "category": "not-in-policy",
        "ticket_text": "Can I speak to Sarah Johnson in your customer service department? She helped me last time and was very knowledgeable.",
        "order_context": {
            "order_date": None,
            "delivery_date": None,
            "item_category": None,
            "fulfillment_type": None,
            "shipping_region": "US",
            "order_status": None,
        },
        "expected_decision": "abstain",
        "key_challenge": "Personnel routing — entirely outside policy",
    },
    {
        "id": 25,
        "category": "standard",
        "ticket_text": "This is the THIRD month in a row that my subscription box had the wrong items. January was wrong, February was wrong, and now March is wrong too. I want a full refund for all three months, not just this one.",
        "order_context": {
            "order_date": "2026-01-01",
            "delivery_date": "2026-03-20",
            "item_category": "subscription",
            "fulfillment_type": "first-party",
            "shipping_region": "US",
            "order_status": "delivered",
        },
        "expected_decision": "escalate",
        "key_challenge": "Repeated incorrect fulfillment — multi-order escalation",
    },
]


def get_ticket_by_id(ticket_id: int) -> dict:
    """Get a specific ticket by its ID."""
    for ticket in EVALUATION_TICKETS:
        if ticket["id"] == ticket_id:
            return ticket
    raise ValueError(f"Ticket ID {ticket_id} not found")


def get_tickets_by_category(category: str) -> list:
    """Get all tickets in a category."""
    return [t for t in EVALUATION_TICKETS if t["category"] == category]
