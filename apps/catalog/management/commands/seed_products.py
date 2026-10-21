from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Category, DataSource, Product
from apps.catalog.seed_data import CATEGORIES, get_products

SOURCE_NAME = "SMP research estimates"
SOURCE_DESC = "Estimated starting figures bundled with the app. Replace with quotes you have verified."
BASIS = (
    "Estimated figures: supplier price, MOQ, shipping, duty rate and Nepal selling price "
    "are estimates, not verified quotes. Exchange rate is configurable."
)


class Command(BaseCommand):
    help = "Seed sample categories and products. Safe to re-run (no duplicates)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh", action="store_true",
            help="Overwrite existing sample products with the bundled values.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        source, _ = DataSource.objects.get_or_create(
            name=SOURCE_NAME,
            defaults={"kind": DataSource.KIND_SAMPLE, "description": SOURCE_DESC, "is_verified": False},
        )
        cats = {}
        for name, slug, icon in CATEGORIES:
            cat, _ = Category.objects.get_or_create(slug=slug, defaults={"name": name, "icon": icon})
            cats[slug] = cat

        created = updated = skipped = 0
        now = timezone.now()
        for i, row in enumerate(get_products()):
            values = {
                "description": row["description"],
                "category": cats[row["category"]],
                "supplier_country": "China",
                "supplier_price_cny": Decimal(str(row["cny_price"])),
                "moq": row["moq"],
                "shipping_npr": Decimal(str(row["shipping_npr"])),
                "handling_npr": Decimal(str(row["handling_npr"])),
                "duty_rate_pct": Decimal(str(row["duty_pct"])),
                "other_import_npr": Decimal(str(row["other_npr"])),
                "selling_price_npr": Decimal(str(row["sell_npr"])),
                "trend_score": row["trend"],
                "competition": row["competition"],
                "import_complexity": row["complexity"],
                "confidence": row["confidence"],
                "why_research": row["why"],
                "estimate_basis": BASIS,
                "data_source": source,
                "is_verified": False,
                "is_sample": True,
            }
            existing = Product.objects.filter(name=row["name"]).first()
            if existing is None:
                Product.objects.create(
                    name=row["name"], created_at=now - timedelta(hours=(40 - i) * 3), **values
                )
                created += 1
            elif opts["refresh"]:
                for key, val in values.items():
                    setattr(existing, key, val)
                existing.save()
                updated += 1
            else:
                skipped += 1
        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {created} created, {updated} refreshed, {skipped} left unchanged."
        ))
