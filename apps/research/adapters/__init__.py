import csv
from pathlib import Path

from .base import (  # noqa: F401
    UPDATABLE_FIELDS, Observation, SourceAdapter, available_adapters, get_adapter, register,
)


@register
class CsvFileAdapter(SourceAdapter):
    """Reads researched values from a local CSV you maintain.

    Columns: product_name, field, value, source, verified (yes/no)
    Works offline. Example row:
        Braided USB-C Charging Cable 1m,supplier_price_cny,4.2,Supplier quote 2026-10-01,yes
    """

    key = "csv"
    label = "Local CSV file"
    description = "Import researched supplier/market values from a CSV you control. Works offline."
    implemented = True

    def fetch(self, path=None, **options):
        if not path:
            raise ValueError("Provide --file path/to/observations.csv")
        file = Path(path)
        if not file.exists():
            raise FileNotFoundError(f"CSV not found: {file}")
        with file.open(newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                yield Observation(
                    product_name=(row.get("product_name") or "").strip(),
                    field=(row.get("field") or "").strip(),
                    value=(row.get("value") or "").strip(),
                    source=(row.get("source") or "CSV import").strip(),
                    verified=(row.get("verified") or "").strip().lower() in {"yes", "true", "1", "y"},
                )


class _PlannedAdapter(SourceAdapter):
    implemented = False
    needs_network = True

    def fetch(self, **options):
        raise NotImplementedError(
            f"'{self.label}' is not implemented. Add a permitted API or licensed feed here."
        )


@register
class SupplierListingsAdapter(_PlannedAdapter):
    key = "supplier_listings"
    label = "Chinese supplier listings and MOQs"
    description = "Planned: supplier prices and MOQs from an official API or licensed feed."


@register
class NepalEcommercePricesAdapter(_PlannedAdapter):
    key = "nepal_prices"
    label = "Nepalese ecommerce prices"
    description = "Planned: local selling prices from a permitted data source."


@register
class SearchInterestAdapter(_PlannedAdapter):
    key = "search_interest"
    label = "Search interest / public trend indicators"
    description = "Planned: demand signals from a public trends API within its terms."
