from django.contrib import admin
from .models import (
    Product, PaymentSettings, Wishlist, Category, Customer,
    Order, OrderItem, Contact, EmailLog, NewsletterSubscriber,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_count', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'total_orders', 'total_spent', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'total_price', 'payment_status', 'order_status', 'created_at')
    list_filter = ('order_status', 'payment_status', 'payment_method')
    search_fields = ('full_name', 'email')
    inlines = [OrderItemInline]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'email', 'subject')


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'subject', 'email_type', 'status', 'created_at')
    list_filter = ('email_type', 'status')
    search_fields = ('recipient', 'subject')


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'subscribed_at')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'category',
        'price',
        'stock',
        'featured',
    )

    list_filter = (
        'category',
        'featured',
    )

    search_fields = (
        'name',
        'description',
    )

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    """
    Admin interface for managing user wishlists
    """
    list_display = (
        'user',
        'product',
        'added_at',
    )

    list_filter = (
        'added_at',
    )

    search_fields = (
        'user__username',
        'user__email',
        'product__name',
    )

    readonly_fields = ('added_at',)

@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    """
    Only one row ever exists. From here the admin uploads the UPI/QR
    code image and fills in the bank account details that customers
    see on the checkout page.
    """

    fieldsets = (
        ("UPI / QR Payment", {
            "fields": ("upi_id", "qr_code"),
        }),
        ("Bank Transfer Details", {
            "fields": ("bank_name", "account_holder_name", "account_number", "ifsc_code", "bank_branch"),
        }),
        ("Customer Instructions", {
            "fields": ("instructions",),
        }),
    )

    def has_add_permission(self, request):
        # Prevent creating a second row — this is a singleton settings table.
        return not PaymentSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False