from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify


# ---------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------

class Category(models.Model):
    """
    Product category, manageable from the custom admin panel.
    Replaces the old hard-coded CATEGORY_CHOICES on Product.
    """
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def product_count(self):
        return self.products.count()


# ---------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------

class Product(models.Model):

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='products'
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Discount percentage (0-100)."
    )
    image = models.ImageField(upload_to='products/')
    stock = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    LOW_STOCK_THRESHOLD = 5

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def category_name(self):
        return self.category.name if self.category else "Uncategorized"

    @property
    def discounted_price(self):
        if self.discount:
            return round(self.price - (self.price * self.discount / 100), 2)
        return self.price

    @property
    def is_low_stock(self):
        return self.stock <= self.LOW_STOCK_THRESHOLD


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class PaymentSettings(models.Model):
    upi_id = models.CharField(max_length=100, blank=True)
    qr_code = models.ImageField(upload_to='payment/', blank=True, null=True)
    bank_name = models.CharField(max_length=150, blank=True)
    account_holder_name = models.CharField(max_length=150, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    bank_branch = models.CharField(max_length=150, blank=True)
    instructions = models.TextField(blank=True)

    class Meta:
        verbose_name = "Payment Setting"
        verbose_name_plural = "Payment Settings"

    def __str__(self):
        return "Payment Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


# ---------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------

class Customer(models.Model):
    """
    Extra profile info for a registered site user. Created automatically
    the moment a User registers (see signals.py).
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def email(self):
        return self.user.email

    @property
    def total_orders(self):
        return self.user.orders.count()

    @property
    def total_spent(self):
        total = self.user.orders.filter(
            payment_status='paid'
        ).aggregate(models.Sum('total_price'))['total_price__sum']
        return total or 0


# ---------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------

class Order(models.Model):

    PAYMENT_METHOD_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('upi', 'UPI / QR Payment'),
        ('bank', 'Bank Transfer'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='orders')
    full_name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)

    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='cod')
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')
    order_status = models.CharField(max_length=15, choices=ORDER_STATUS_CHOICES, default='pending')

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id}"

    @property
    def customer_name(self):
        if self.full_name:
            return self.full_name
        return self.customer.get_full_name() if self.customer else "Guest"

    @property
    def item_count(self):
        return sum(i.quantity for i in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"


# ---------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------

class Contact(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('read', 'Read'),
        ('replied', 'Replied'),
    ]

    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    reply = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.subject}"


# ---------------------------------------------------------------------
# Newsletter
# ---------------------------------------------------------------------

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.email


# ---------------------------------------------------------------------
# Email log
# ---------------------------------------------------------------------

class EmailLog(models.Model):
    EMAIL_TYPE_CHOICES = [
        ('welcome', 'Welcome Email'),
        ('contact_confirmation', 'Contact Confirmation'),
        ('admin_reply', 'Admin Reply'),
        ('order_confirmation', 'Order Confirmation'),
        ('order_status_update', 'Order Status Update'),
        ('password_reset', 'Password Reset'),
        ('newsletter', 'Newsletter'),
    ]
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    email_type = models.CharField(max_length=30, choices=EMAIL_TYPE_CHOICES)
    sent_by = models.CharField(max_length=150, blank=True, help_text="System, or admin username.")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email_type} -> {self.recipient} ({self.status})"
