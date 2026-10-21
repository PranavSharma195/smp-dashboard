from django.core.management.base import BaseCommand, CommandError

from apps.catalog.fx import FxError, refresh_rate


class Command(BaseCommand):
    help = "Fetch the live CNY to NPR exchange rate and recalculate every product."

    def handle(self, *args, **opts):
        try:
            rate, count = refresh_rate()
        except FxError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"1 CNY = {rate} NPR. Recalculated {count} products."))
