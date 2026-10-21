import decimal

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models



class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
                ("slug", models.SlugField(max_length=140, unique=True)),
                ("icon", models.CharField(default="box", help_text="Icon name from static/img/icons.svg", max_length=40)),
            ],
            options={"verbose_name_plural": "categories", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="DataSource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160, unique=True)),
                ("kind", models.CharField(choices=[("sample", "Sample / illustrative data"), ("manual", "Manual research"), ("adapter", "Automated adapter")], default="sample", max_length=10)),
                ("description", models.TextField(blank=True)),
                ("url", models.URLField(blank=True)),
                ("is_verified", models.BooleanField(default=False, help_text="True only if values from this source were checked.")),
                ("last_updated", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("description", models.TextField(blank=True)),
                ("image", models.ImageField(blank=True, upload_to="products/")),
                ("supplier_country", models.CharField(default="China", max_length=60)),
                ("supplier_price_cny", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0"))], verbose_name="Supplier unit price (CNY)")),
                ("fx_rate_cny_npr", models.DecimalField(blank=True, decimal_places=4, help_text="Leave blank to use the site-wide illustrative rate.", max_digits=8, null=True, verbose_name="CNY to NPR rate override")),
                ("moq", models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)], verbose_name="Minimum order quantity")),
                ("shipping_npr", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0"))], verbose_name="Estimated shipping for the MOQ (NPR)")),
                ("handling_npr", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0"))], verbose_name="Insurance and handling (NPR)")),
                ("duty_rate_pct", models.DecimalField(decimal_places=2, default=0, help_text="An ESTIMATE applied to purchase + shipping + insurance. Not a verified customs rate for this product.", max_digits=6, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0"))], verbose_name="Estimated duty and tax rate (%)")),
                ("other_import_npr", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0"))], verbose_name="Other import expenses (NPR)")),
                ("selling_price_npr", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0"))], verbose_name="Estimated selling price in Nepal (NPR)")),
                ("trend_score", models.PositiveSmallIntegerField(default=50, validators=[django.core.validators.MaxValueValidator(100)], verbose_name="Demand / trend score")),
                ("competition", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], default="medium", max_length=6)),
                ("import_complexity", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], default="medium", max_length=6)),
                ("confidence", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], default="low", max_length=6)),
                ("why_research", models.TextField(blank=True, verbose_name="Why research this?")),
                ("estimate_basis", models.TextField(blank=True, verbose_name="Source / basis of estimates")),
                ("is_verified", models.BooleanField(default=False, help_text="Tick only when the numbers were verified against real quotes.")),
                ("is_sample", models.BooleanField(default=True, help_text="Illustrative sample data, not live market data.")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("unit_price_npr", models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=12)),
                ("purchase_cost_npr", models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=14)),
                ("duties_taxes_npr", models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=14)),
                ("landed_total_npr", models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=14)),
                ("landed_per_unit_npr", models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=12)),
                ("profit_per_unit_npr", models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=12)),
                ("profit_per_order_npr", models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=14)),
                ("margin_pct", models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=7)),
                ("viability_score", models.PositiveSmallIntegerField(default=0, editable=False)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="products", to="catalog.category")),
                ("data_source", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="products", to="catalog.datasource")),
            ],
            options={"ordering": ["-viability_score", "name"]},
        ),
    ]
