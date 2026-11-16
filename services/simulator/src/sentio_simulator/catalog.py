"""The fictional operator and its offers.

Quillnet Mobile is an invented European telecom operator. Its name, plans and prices are made up
for the demo and do not describe any real company.
"""

from dataclasses import dataclass
from decimal import Decimal

from sentio_schemas import CustomerSegment

OPERATOR_NAME = "Quillnet Mobile"


@dataclass(frozen=True, slots=True)
class Plan:
    name: str
    monthly_price_eur: Decimal


PLANS: dict[CustomerSegment, tuple[Plan, ...]] = {
    CustomerSegment.PREPAID: (
        Plan("Quill Start", Decimal("9.99")),
        Plan("Quill Flex 30", Decimal("14.99")),
    ),
    CustomerSegment.POSTPAID: (
        Plan("Quill 50 Go", Decimal("19.99")),
        Plan("Quill 150 Go 5G", Decimal("29.99")),
        Plan("Quill Unlimited 5G", Decimal("39.99")),
    ),
    CustomerSegment.BUSINESS: (
        Plan("Quill Business Pro", Decimal("49.00")),
        Plan("Quill Business Unlimited", Decimal("79.00")),
    ),
}

CITIES = ("Lyon", "Lille", "Porto", "Ghent", "Turin", "Seville", "Bordeaux", "Utrecht")
"""Places mentioned in network complaints."""

ROAMING_COUNTRIES_EN = (
    "in Spain",
    "in Italy",
    "in Morocco",
    "in Switzerland",
    "in the United Kingdom",
    "in Canada",
)
ROAMING_COUNTRIES_FR = (
    "en Espagne",
    "en Italie",
    "au Maroc",
    "en Suisse",
    "au Royaume-Uni",
    "au Canada",
)
"""Same countries in both languages, index by index, with the preposition each language needs."""
