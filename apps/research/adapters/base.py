"""Source-adapter architecture.

An adapter turns an external (or local) data source into ``Observation``
records: "for product X, field Y has value Z, according to source S, retrieved
at T, and it is (or is not) verified". The core app never depends on any
particular adapter, so everything keeps working when no adapter is configured
or when the network is unavailable.

To add a source:
    1. Subclass ``SourceAdapter`` and implement ``fetch()``.
    2. Decorate it with ``@register``.
    3. Run ``python manage.py sync_sources --adapter <key>``.

Terms of service: only write adapters for sources you are permitted to use
(official APIs, licensed feeds, data you collected yourself). Do not scrape
sites that forbid it or bypass access controls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

# Product fields an adapter is allowed to update.
UPDATABLE_FIELDS = {
    "supplier_price_cny": "decimal",
    "moq": "int",
    "shipping_npr": "decimal",
    "handling_npr": "decimal",
    "duty_rate_pct": "decimal",
    "other_import_npr": "decimal",
    "selling_price_npr": "decimal",
    "trend_score": "int",
    "competition": "level",
    "import_complexity": "level",
    "confidence": "level",
}


@dataclass
class Observation:
    product_name: str
    field: str
    value: str
    source: str
    verified: bool = False
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SourceAdapter:
    key = "base"
    label = "Base adapter"
    description = ""
    implemented = False
    needs_network = False

    def fetch(self, **options):  # pragma: no cover - interface
        raise NotImplementedError

    def is_available(self):
        return self.implemented


_REGISTRY: dict[str, type[SourceAdapter]] = {}


def register(cls):
    _REGISTRY[cls.key] = cls
    return cls


def get_adapter(key):
    return _REGISTRY[key]()


def available_adapters():
    return [cls() for cls in _REGISTRY.values()]
