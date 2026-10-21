import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("catalog", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="FxRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rate", models.DecimalField(decimal_places=6, max_digits=12)),
                ("source", models.CharField(max_length=160)),
                ("fetched_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={"ordering": ["-fetched_at"]},
        ),
    ]
