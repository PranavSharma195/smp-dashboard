from django.conf import settings
from django.db import models


class UserPreference(models.Model):
    """Per-user saved preferences (currently: saved Explore filters)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="smp_preferences"
    )
    saved_filters = models.CharField(max_length=1000, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user}"
