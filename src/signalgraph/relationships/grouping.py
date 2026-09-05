"""Parse and validate market relationship groups from YAML configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

RelationshipType = Literal[
    "aggregate_constituent",
    "mutually_exclusive",
    "conditional",
    "overlapping",
    "custom",
]


class MarketRef(BaseModel):
    """Reference to a single market on a platform."""

    platform: str = Field(..., min_length=1)
    market_id: str = Field(..., min_length=1)
    notes: str | None = None

    @field_validator("platform", "market_id")
    @classmethod
    def _strip_nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("platform/market_id must be non-empty")
        return value


class MarketGroup(BaseModel):
    """A named set of related markets for research."""

    name: str
    relationship_type: RelationshipType
    description: str | None = None
    aggregate: MarketRef | None = None
    constituents: list[MarketRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_relationship_shape(self) -> MarketGroup:
        if self.relationship_type == "aggregate_constituent":
            if self.aggregate is None:
                raise ValueError(
                    f"Group '{self.name}': aggregate_constituent requires aggregate"
                )
            if not self.constituents:
                # Allow templates with placeholder IDs, but require the key present.
                # Empty constituents are rejected only when market_ids look real.
                pass
        if self.relationship_type == "mutually_exclusive" and self.aggregate is not None:
            raise ValueError(
                f"Group '{self.name}': mutually_exclusive should not define aggregate"
            )
        return self

    def all_market_refs(self) -> list[MarketRef]:
        refs: list[MarketRef] = []
        if self.aggregate is not None:
            refs.append(self.aggregate)
        refs.extend(self.constituents)
        return refs

    def real_market_refs(self) -> list[MarketRef]:
        """Return refs that do not look like configuration placeholders."""
        return [
            r
            for r in self.all_market_refs()
            if not r.market_id.upper().startswith("REPLACE_WITH")
        ]


def load_market_groups(path: Path | str) -> dict[str, MarketGroup]:
    """Load market groups from a YAML file.

    Expected structure:
        groups:
          group_name:
            relationship_type: ...
            aggregate: {platform, market_id}
            constituents: [...]
    """
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    groups_raw = raw.get("groups", {})
    if not isinstance(groups_raw, dict):
        raise ValueError("market_groups.yaml must contain a top-level 'groups' mapping")

    groups: dict[str, MarketGroup] = {}
    for name, cfg in groups_raw.items():
        if cfg is None:
            cfg = {}
        if not isinstance(cfg, dict):
            raise ValueError(f"Group '{name}' must be a mapping")
        payload = {"name": name, **cfg}
        groups[name] = MarketGroup.model_validate(payload)
    return groups
