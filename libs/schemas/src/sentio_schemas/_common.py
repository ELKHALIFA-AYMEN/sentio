"""Building blocks shared by every event contract."""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field


class Contract(BaseModel):
    """Base for event models: immutable, strict about unknown fields and about types."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


def _to_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


UtcDatetime = Annotated[AwareDatetime, AfterValidator(_to_utc)]
"""A timestamp that must carry a timezone; it is normalised to UTC."""

Probability = Annotated[float, Field(ge=0.0, le=1.0)]
"""A number between 0 and 1 (confidence, risk score)."""
