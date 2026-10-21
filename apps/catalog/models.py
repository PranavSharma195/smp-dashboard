from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.finance.calculations import compute_import_costs
from apps.research.scoring import score_band, score_product


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    icon = models.CharField(
        max_length=40, default="box", help_text="Icon name from static/img/icons.svg"
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class DataSource(models.Model):
    KIND_SAMPLE = "sample"
    KIND_MANUAL = "manual"
    KIND_ADAPTER = "adapter"
    KIND_CHOICES = [
        (KIND_SAMPLE, "Sample / illustrative data"),
        (KIND_MANUAL, "Manual research"),
        (KIND_ADAPTER, "Automated adapter"),
    ]

    name = models.CharField(max_length=160, unique=True)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=KIND_SAMPLE)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)
    is_verified = models.BooleanField(
        default=False, help_text="True only if values from this source were checked."
    )
    last_updated = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class FxRate(models.Model):
    """A CNY -> NPR exchange rate fetched from an external service."""

    rate = models.DecimalField(max_digits=12, decimal_places=6)
    source = models.CharField(max_length=160)
    fetched_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-fetched_at"]

    def __str__(self):
        return f"1 CNY = {self.rate} NPR ({self.fetched_at:%Y-%m-%d %H:%M})"


LEVEL_CHOICES = [("low", "Low"), ("medium", "Medium"), ("high", "High")]


class Product(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    image = models.ImageField(upload_to="products/", blank=True)

    supplier_country = models.CharField(max_length=60, default="China")
    supplier_price_cny = models.DecimalField(
        "Supplier unit price (CNY)", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    fx_rate_cny_npr = models.DecimalField(
        "CNY to NPR rate override", max_digits=8, decimal_places=4,
        null=True, blank=True,
        help_text="Leave blank to use the site-wide illustrative rate.",
    )
    moq = models.PositiveIntegerField(
        "Minimum order quantity", default=1, validators=[MinValueValidator(1)]
    )
    shipping_npr = models.DecimalField(
        "Estimated shipping for the MOQ (NPR)", max_digits=12, decimal_places=2,
        default=0, validators=[MinValueValidator(Decimal("0"))],
    )
    handling_npr = models.DecimalField(
        "Insurance and handling (NPR)", max_digits=12, decimal_places=2,
        default=0, validators=[MinValueValidator(Decimal("0"))],
    )
    duty_rate_pct = models.DecimalField(
        "Estimated duty and tax rate (%)", max_digits=6, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="An ESTIMATE applied to purchase + shipping + insurance. "
        "Not a verified customs rate for this product.",
    )
    other_import_npr = models.DecimalField(
        "Other import expenses (NPR)", max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal("0"))],
    )
    selling_price_npr = models.DecimalField(
        "Estimated selling price in Nepal (NPR)", max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )

    trend_score = models.PositiveSmallIntegerField(
        "Demand / trend score", default=50, validators=[MaxValueValidator(100)]
    )
    competition = models.CharField(max_length=6, choices=LEVEL_CHOICES, default="medium")
    import_complexity = models.CharField(max_length=6, choices=LEVEL_CHOICES, default="medium")
    confidence = models.CharField(max_length=6, choices=LEVEL_CHOICES, default="low")

    why_research = models.TextField("Why research this?", blank=True)
    estimate_basis = models.TextField("Source / basis of estimates", blank=True)
    data_source = models.ForeignKey(
        DataSource, null=True, blank=True, on_delete=models.SET_NULL, related_name="products"
    )
    is_verified = models.BooleanField(
        default=False, help_text="Tick only when the numbers were verified against real quotes."
    )
    is_sample = models.BooleanField(
        default=True, help_text="Illustrative sample data, not live market data."
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Calculated on save (see recalculate). Stored so lists can filter and sort in SQL.
    unit_price_npr = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    purchase_cost_npr = models.DecimalField(max_digits=14, decimal_places=2, default=0, editable=False)
    duties_taxes_npr = models.DecimalField(max_digits=14, decimal_places=2, default=0, editable=False)
    landed_total_npr = models.DecimalField(max_digits=14, decimal_places=2, default=0, editable=False)
    landed_per_unit_npr = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    profit_per_unit_npr = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    profit_per_order_npr = models.DecimalField(max_digits=14, decimal_places=2, default=0, editable=False)
    margin_pct = models.DecimalField(max_digits=7, decimal_places=2, default=0, editable=False)
    viability_score = models.PositiveSmallIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["-viability_score", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("catalog:detail", args=[self.slug])

    # -- calculation helpers -------------------------------------------------
    @property
    def fx_rate(self):
        if self.fx_rate_cny_npr:
            return self.fx_rate_cny_npr
        from .fx import current_rate

        return current_rate()[0]

    def cost_breakdown(self):
        return compute_import_costs(
            unit_price_cny=self.supplier_price_cny,
            fx_rate=self.fx_rate,
            quantity=self.moq,
            shipping_npr=self.shipping_npr,
            insurance_handling_npr=self.handling_npr,
            duty_rate_pct=self.duty_rate_pct,
            other_expenses_npr=self.other_import_npr,
            selling_price_npr=self.selling_price_npr,
        )

    def score_breakdown(self):
        return score_product(
            trend_score=self.trend_score,
            margin_pct=self.margin_pct,
            landed_total=self.landed_total_npr,
            moq=self.moq,
            competition=self.competition,
            complexity=self.import_complexity,
            confidence=self.confidence,
            weights=getattr(settings, "SMP_SCORE_WEIGHTS", None),
        )

    @property
    def score_label(self):
        return score_band(self.viability_score)

    def recalculate(self):
        result = self.cost_breakdown()
        zero = Decimal("0")
        if result.valid:
            self.unit_price_npr = result.unit_price_npr
            self.purchase_cost_npr = result.purchase_cost
            self.duties_taxes_npr = result.duties_taxes
            self.landed_total_npr = result.landed_total
            self.landed_per_unit_npr = result.landed_per_unit
            self.profit_per_unit_npr = result.profit_per_unit if result.profit_per_unit is not None else zero
            self.profit_per_order_npr = result.profit_per_order if result.profit_per_order is not None else zero
            self.margin_pct = result.margin_pct if result.margin_pct is not None else zero
        else:
            self.unit_price_npr = self.purchase_cost_npr = self.duties_taxes_npr = zero
            self.landed_total_npr = self.landed_per_unit_npr = zero
            self.profit_per_unit_npr = self.profit_per_order_npr = self.margin_pct = zero
        self.viability_score = self.score_breakdown().total

    @property
    def tone(self):
        return (self.pk or 0) % 6

    @property
    def import_expenses_npr(self):
        return self.landed_total_npr - self.purchase_cost_npr

    @property
    def evidence_label(self):
        return "Verified" if self.is_verified else "Estimated"

    def _unique_slug(self):
        base = slugify(self.name)[:150] or "product"
        slug, n = base, 2
        while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        self.recalculate()
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {
                "unit_price_npr", "purchase_cost_npr", "duties_taxes_npr",
                "landed_total_npr", "landed_per_unit_npr", "profit_per_unit_npr",
                "profit_per_order_npr", "margin_pct", "viability_score", "updated_at",
            }
        super().save(*args, **kwargs)
