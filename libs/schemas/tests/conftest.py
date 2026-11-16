from typing import Any

import pytest


@pytest.fixture
def raw_payload() -> dict[str, Any]:
    """A valid conversations.raw event, as it would appear in JSON on the wire."""
    return {
        "schema_version": 1,
        "event_id": "7b1c2a10-5d3e-4f60-9a1b-2c3d4e5f6a01",
        "conversation_id": "c3f0a1b2-6e4f-4a70-8b2c-3d4e5f6a7b02",
        "message_id": "a91e3c4d-7f50-4b81-9c3d-4e5f6a7b8c03",
        "sequence": 3,
        "sent_at": "2026-11-09T10:15:42Z",
        "channel": "chat",
        "author": "customer",
        "text": "My 4G has been down for three days, I can't work.",
        "customer": {
            "customer_id": "CUST-004211",
            "segment": "postpaid",
            "tenure_months": 38,
            "monthly_revenue_eur": "29.99",
        },
    }


@pytest.fixture
def enriched_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    """A valid conversations.enriched event for a customer message, as JSON on the wire."""
    return {
        **raw_payload,
        "enrichment": {
            "language": "en",
            "language_confidence": 0.98,
            "sentiment": {"label": "negative", "score": -0.82},
            "topic": {"label": "network", "confidence": 0.91},
            "churn_risk": 0.74,
            "model_versions": {
                "language": "lingua-1.0.0",
                "sentiment": "tfidf-lr-0.1.0",
                "topic": "tfidf-lr-0.1.0",
                "churn": "rules-0.1.0",
            },
            "enriched_at": "2026-11-09T10:15:42.350000Z",
        },
    }


@pytest.fixture
def agent_enriched_payload(enriched_payload: dict[str, Any]) -> dict[str, Any]:
    """A valid enriched event for an agent message: only the language is predicted."""
    enriched_payload["author"] = "agent"
    enriched_payload["text"] = "I'm sorry to hear that, let me check the network in your area."
    enriched_payload["enrichment"].update(sentiment=None, topic=None, churn_risk=None)
    return enriched_payload
