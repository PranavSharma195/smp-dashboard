from django.contrib import admin, messages

from .models import Category, DataSource, FxRate, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "product_count")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Products")
    def product_count(self, obj):
        return obj.products.count()


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "is_verified", "last_updated")
    list_filter = ("kind", "is_verified")
    search_fields = ("name", "description")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "category", "supplier_price_cny", "moq", "selling_price_npr",
        "landed_total_npr", "margin_pct", "trend_score", "competition",
        "confidence", "viability_score", "is_verified", "is_active",
    )
    list_filter = ("category", "competition", "confidence", "import_complexity",
                   "is_verified", "is_sample", "is_active", "data_source")
    search_fields = ("name", "description", "why_research")
    ordering = ("-updated_at",)
    list_per_page = 40
    date_hierarchy = "updated_at"
    readonly_fields = (
        "unit_price_npr", "purchase_cost_npr", "duties_taxes_npr", "landed_total_npr",
        "landed_per_unit_npr", "profit_per_unit_npr", "profit_per_order_npr",
        "margin_pct", "viability_score", "updated_at",
    )
    prepopulated_fields = {"slug": ("name",)}
    actions = ["mark_verified", "mark_estimated", "recalculate_selected"]
    fieldsets = (
        ("Product", {"fields": ("name", "slug", "category", "image", "description", "is_active")}),
        ("Supplier and order", {"fields": ("supplier_country", "supplier_price_cny", "fx_rate_cny_npr", "moq")}),
        ("Import expense estimates", {"fields": ("shipping_npr", "handling_npr", "duty_rate_pct", "other_import_npr")}),
        ("Nepal market assumptions", {"fields": ("selling_price_npr", "trend_score", "competition", "import_complexity", "confidence")}),
        ("Research notes and data source", {"fields": ("why_research", "estimate_basis", "data_source", "is_verified", "is_sample")}),
        ("Calculated (read-only, refreshed on save)", {
            "classes": ("collapse",),
            "fields": ("unit_price_npr", "purchase_cost_npr", "duties_taxes_npr", "landed_total_npr",
                       "landed_per_unit_npr", "profit_per_unit_npr", "profit_per_order_npr",
                       "margin_pct", "viability_score", "created_at", "updated_at"),
        }),
    )

    @admin.action(description="Mark selected as verified")
    def mark_verified(self, request, queryset):
        for p in queryset:
            p.is_verified, p.is_sample = True, False
            p.save()
        self.message_user(request, f"{queryset.count()} product(s) marked verified.", messages.SUCCESS)

    @admin.action(description="Mark selected as estimated (unverified)")
    def mark_estimated(self, request, queryset):
        for p in queryset:
            p.is_verified = False
            p.save()
        self.message_user(request, f"{queryset.count()} product(s) marked estimated.", messages.SUCCESS)

    @admin.action(description="Recalculate costs and scores")
    def recalculate_selected(self, request, queryset):
        for p in queryset:
            p.save()
        self.message_user(request, f"Recalculated {queryset.count()} product(s).", messages.SUCCESS)


@admin.register(FxRate)
class FxRateAdmin(admin.ModelAdmin):
    list_display = ("rate", "source", "fetched_at")
    ordering = ("-fetched_at",)
