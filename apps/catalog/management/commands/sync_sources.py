from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import DataSource, Product
from apps.research.adapters import UPDATABLE_FIELDS, available_adapters, get_adapter


def _convert(kind, raw):
    if kind == "decimal":
        return Decimal(raw)
    if kind == "int":
        return int(Decimal(raw))
    if kind == "level":
        value = raw.lower()
        if value not in {"low", "medium", "high"}:
            raise ValueError("must be low, medium or high")
        return value
    raise ValueError("unsupported field type")


class Command(BaseCommand):
    help = "Apply observations from a source adapter to products (records source and verified flag)."

    def add_arguments(self, parser):
        parser.add_argument("--adapter", help="Adapter key (see --list)")
        parser.add_argument("--file", help="Path for file-based adapters (csv)")
        parser.add_argument("--list", action="store_true", help="List adapters and exit")

    def handle(self, *args, **opts):
        if opts["list"] or not opts["adapter"]:
            for a in available_adapters():
                state = "ready" if a.implemented else "not implemented"
                self.stdout.write(f"{a.key:18} {state:16} {a.label}")
            return
        try:
            adapter = get_adapter(opts["adapter"])
        except KeyError as exc:
            raise CommandError(f"Unknown adapter '{opts['adapter']}'. Use --list.") from exc
        try:
            observations = list(adapter.fetch(path=opts["file"]))
        except (NotImplementedError, ValueError, FileNotFoundError) as exc:
            raise CommandError(str(exc)) from exc

        applied = skipped = 0
        with transaction.atomic():
            sources = {}
            touched = {}
            for ob in observations:
                kind = UPDATABLE_FIELDS.get(ob.field)
                product = touched.get(ob.product_name) or Product.objects.filter(name=ob.product_name).first()
                if kind is None or product is None:
                    skipped += 1
                    self.stderr.write(f"Skipped: {ob.product_name!r} / {ob.field!r}")
                    continue
                try:
                    value = _convert(kind, ob.value)
                except (InvalidOperation, ValueError) as exc:
                    skipped += 1
                    self.stderr.write(f"Skipped invalid value for {ob.product_name!r}.{ob.field}: {exc}")
                    continue
                setattr(product, ob.field, value)
                src = sources.get(ob.source)
                if src is None:
                    src, _ = DataSource.objects.get_or_create(
                        name=ob.source,
                        defaults={"kind": DataSource.KIND_ADAPTER, "is_verified": ob.verified},
                    )
                    sources[ob.source] = src
                product.data_source = src
                product.is_verified = ob.verified
                product.is_sample = False
                touched[ob.product_name] = product
                applied += 1
            for product in touched.values():
                product.save()
            for src in sources.values():
                src.last_updated = timezone.now()
                src.save()
        self.stdout.write(self.style.SUCCESS(f"Applied {applied} observation(s); skipped {skipped}."))
