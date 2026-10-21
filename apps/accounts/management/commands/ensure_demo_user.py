from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Create the local demo user if it does not exist. The password is hashed by "
        "Django. Use --reset-password to set it again. CHANGE THESE CREDENTIALS BEFORE DEPLOYING."
    )

    def add_arguments(self, parser):
        parser.add_argument("--reset-password", action="store_true")

    def handle(self, *args, **opts):
        User = get_user_model()
        username = settings.SMP_DEMO_USERNAME
        user, created = User.objects.get_or_create(
            username=username, defaults={"is_staff": True, "is_superuser": True, "first_name": "Manab"}
        )
        if created or opts["reset_password"]:
            if settings.SMP_DEMO_PASSWORD:
                user.set_password(settings.SMP_DEMO_PASSWORD)
            else:
                user.password = settings.SMP_DEMO_PASSWORD_HASH  # already hashed
            user.save()
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created demo user '{username}'."))
        elif opts["reset_password"]:
            self.stdout.write(self.style.SUCCESS(f"Password reset for '{username}'."))
        else:
            self.stdout.write(f"Demo user '{username}' already exists; left unchanged.")
        self.stdout.write(self.style.WARNING(
            "Demo credentials are for local use only. Change them before any deployment."
        ))
