"""Canonical evaluation corpus shared by Day 5 RAG and Day 6 evaluation."""

from embeddings import EmbeddingModel
from models import Chunk, ChunkMetadata


def build_corpus(embedder: EmbeddingModel) -> list[Chunk]:
    """Build the canonical corpus with stable chunk IDs."""

    records = [
        {
            "id": "refund-001",
            "text": "Refunds are allowed within 30 days of purchase.",
            "document_id": "doc_refunds",
            "source": "refund-policy.pdf",
            "page": 1,
            "section": "Returns",
        },
        {
            "id": "returns-001",
            "text": "Damaged products can be returned if reported within 48 hours.",
            "document_id": "doc_returns",
            "source": "returns.pdf",
            "page": 2,
            "section": "Damaged Goods",
        },
        {
            "id": "payment-001",
            "text": (
                "Error code ERR_PAYMENT_403 indicates a forbidden transaction."
            ),
            "document_id": "doc_errors",
            "source": "errors.pdf",
            "page": 2,
            "section": "Payment Errors",
        },
        {
            "id": "shipping-001",
            "text": (
                "Orders are processed after they are successfully placed "
                "and payment has been confirmed."
            ),
            "document_id": "doc_shipping",
            "source": "shipping_policy.md",
            "page": 1,
            "section": "Processing Orders",
        },
        {
            "id": "shipping-002",
            "text": "Processing time is separate from transit time.",
            "document_id": "doc_shipping",
            "source": "shipping_policy.md",
            "page": 1,
            "section": "Processing Orders",
        },
        {
            "id": "shipping-003",
            "text": (
                "Standard delivery typically takes 3–5 business days "
                "after an order has been processed."
            ),
            "document_id": "doc_shipping",
            "source": "shipping_policy.md",
            "page": 1,
            "section": "Delivery Time",
        },
        {
            "id": "shipping-004",
            "text": (
                "Actual delivery time may vary depending on destination, "
                "carrier conditions, weather, holidays, and other "
                "circumstances affecting transportation."
            ),
            "document_id": "doc_shipping",
            "source": "shipping_policy.md",
            "page": 1,
            "section": "Delivery Time",
        },
        {
            "id": "shipping-005",
            "text": (
                "Customers are responsible for providing a complete and "
                "accurate shipping address."
            ),
            "document_id": "doc_shipping",
            "source": "shipping_policy.md",
            "page": 1,
            "section": "Shipping Address",
        },
        {
            "id": "shipping-006",
            "text": (
                "An incorrect or incomplete address may cause a delivery "
                "delay or failed delivery."
            ),
            "document_id": "doc_shipping",
            "source": "shipping_policy.md",
            "page": 1,
            "section": "Shipping Address",
        },
        {
            "id": "shipping-007",
            "text": (
                "When tracking information is available, customers can use "
                "the tracking information associated with their order to "
                "monitor delivery progress."
            ),
            "document_id": "doc_shipping",
            "source": "shipping_policy.md",
            "page": 1,
            "section": "Tracking",
        },
        {
            "id": "shipping-008",
            "text": (
                "If an order has not arrived within the expected delivery "
                "window, the customer should first check the available "
                "tracking information."
            ),
            "document_id": "doc_shipping",
            "source": "shipping_policy.md",
            "page": 1,
            "section": "Delayed Deliveries",
        },
        {
            "id": "shipping-009",
            "text": (
                "If the shipment remains delayed, the customer should "
                "contact support with their order details."
            ),
            "document_id": "doc_shipping",
            "source": "shipping_policy.md",
            "page": 1,
            "section": "Delayed Deliveries",
        },
        {
            "id": "shipping-010",
            "text": (
                "If a package or product is damaged during delivery, "
                "the customer should contact support and provide order "
                "details, a description of the damage, and photos when available."
            ),
            "document_id": "doc_shipping",
            "source": "shipping_policy.md",
            "page": 1,
            "section": "Damaged Packages",
        },
        {
            "id": "shipping-011",
            "text": (
                "Delivery may take longer than the standard estimate because "
                "of severe weather, carrier disruptions, public holidays, "
                "or incorrect delivery information."
            ),
            "document_id": "doc_shipping",
            "source": "shipping_policy.md",
            "page": 1,
            "section": "Delivery Exceptions",
        },
        {
            "id": "account-001",
            "text": (
                "Customers can create an account by providing the required "
                "registration information through the account registration flow."
            ),
            "document_id": "doc_account",
            "source": "account_guide.md",
            "page": 1,
            "section": "Creating an Account",
        },
        {
            "id": "account-002",
            "text": "Required registration information includes name, email address, and password.",
            "document_id": "doc_account",
            "source": "account_guide.md",
            "page": 1,
            "section": "Creating an Account",
        },
        {
            "id": "account-003",
            "text": (
                "After registration, customers can sign in using their "
                "email address and password."
            ),
            "document_id": "doc_account",
            "source": "account_guide.md",
            "page": 1,
            "section": "Creating an Account",
        },
        {
            "id": "account-004",
            "text": (
                "To sign in, open the sign-in page, enter the email address "
                "associated with the account, enter the account password, "
                "and submit the sign-in form."
            ),
            "document_id": "doc_account",
            "source": "account_guide.md",
            "page": 1,
            "section": "Signing In",
        },
        {
            "id": "account-005",
            "text": (
                "To reset a forgotten password, open the password-reset flow, "
                "enter the account email address, follow the instructions "
                "sent to that email address, and create a new password."
            ),
            "document_id": "doc_account",
            "source": "account_guide.md",
            "page": 1,
            "section": "Password Reset",
        },
        {
            "id": "account-006",
            "text": (
                "Customers should keep their password private, use a strong "
                "unique password, avoid sharing account credentials, and "
                "contact support if they suspect unauthorized access."
            ),
            "document_id": "doc_account",
            "source": "account_guide.md",
            "page": 1,
            "section": "Account Security",
        },
    ]

    return [
        Chunk(
            id=record["id"],
            text=record["text"],
            metadata=ChunkMetadata(
                document_id=record["document_id"],
                source=record["source"],
                page=record["page"],
                section=record["section"],
                tenant_id="company_42",
                created_at="2026-09-01",
            ),
            embedding=embedder.get_embedding(record["text"]),
        )
        for record in records
    ]
