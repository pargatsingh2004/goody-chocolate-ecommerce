from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from products.models import (
    Product, Category, Order, OrderItem, Contact, EmailLog,
    Customer, NewsletterSubscriber,
)
from products import emails
from django.contrib.auth.models import User

from .decorators import staff_required
from .forms import (
    ProductForm, CategoryForm, ContactReplyForm, OrderStatusForm,
    NewsletterForm,
)


# ---------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------

def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        remember = request.POST.get("remember")

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_staff:
            auth_login(request, user)
            if remember:
                request.session.set_expiry(60 * 60 * 24 * 30)
            else:
                request.session.set_expiry(0)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect('admin_dashboard')

        messages.error(request, "Invalid credentials or you do not have admin access.")

    return render(request, "admin_panel/login.html")


def admin_logout(request):
    auth_logout(request)
    messages.success(request, "You have been logged out of the admin panel.")
    return redirect('admin_login')


# ---------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------

@staff_required
def dashboard(request):
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    total_customers = Customer.objects.count()
    total_revenue = Order.objects.filter(payment_status='paid').aggregate(
        total=Sum('total_price')
    )['total'] or 0

    # Notifications
    new_orders_count = Order.objects.filter(order_status='pending').count()
    new_messages_count = Contact.objects.filter(status='new').count()
    pending_replies_count = Contact.objects.exclude(status='replied').count()
    low_stock_count = Product.objects.filter(stock__lte=Product.LOW_STOCK_THRESHOLD).count()

    recent_orders = Order.objects.select_related('customer').prefetch_related('items')[:8]

    # Monthly sales / orders for the last 6 months
    today = timezone.now()
    months, monthly_sales, monthly_orders = [], [], []
    for i in range(5, -1, -1):
        target = today.replace(day=1)
        # step back i months
        year = target.year
        month = target.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_orders = Order.objects.filter(created_at__year=year, created_at__month=month)
        months.append(f"{year}-{month:02d}")
        monthly_sales.append(float(month_orders.filter(payment_status='paid').aggregate(
            total=Sum('total_price'))['total'] or 0))
        monthly_orders.append(month_orders.count())

    category_distribution = list(
        Category.objects.annotate(count=Count('products')).values('name', 'count')
    )

    context = {
        "total_products": total_products,
        "total_orders": total_orders,
        "total_customers": total_customers,
        "total_revenue": total_revenue,
        "new_orders_count": new_orders_count,
        "new_messages_count": new_messages_count,
        "pending_replies_count": pending_replies_count,
        "low_stock_count": low_stock_count,
        "recent_orders": recent_orders,
        "months_json": months,
        "monthly_sales_json": monthly_sales,
        "monthly_orders_json": monthly_orders,
        "category_labels_json": [c['name'] for c in category_distribution],
        "category_counts_json": [c['count'] for c in category_distribution],
    }
    return render(request, "admin_panel/dashboard.html", context)


# ---------------------------------------------------------------------
# Product Management
# ---------------------------------------------------------------------

@staff_required
def product_list(request):
    products = Product.objects.select_related('category').all()

    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    status = request.GET.get('status', '')

    if q:
        products = products.filter(name__icontains=q)
    if category_id:
        products = products.filter(category_id=category_id)
    if status:
        products = products.filter(status=status)

    paginator = Paginator(products, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        "page_obj": page_obj,
        "categories": Category.objects.all(),
        "q": q,
        "selected_category": category_id,
        "selected_status": status,
    }
    return render(request, "admin_panel/products.html", context)


@staff_required
def product_add(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Product added successfully.")
            return redirect('admin_products')
    else:
        form = ProductForm()
    return render(request, "admin_panel/product_form.html", {"form": form, "is_edit": False})


@staff_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully.")
            return redirect('admin_products')
    else:
        form = ProductForm(instance=product)
    return render(request, "admin_panel/product_form.html", {"form": form, "is_edit": True, "product": product})


@staff_required
def product_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, "admin_panel/product_detail.html", {"product": product})


@staff_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, "Product deleted.")
    return redirect('admin_products')


# ---------------------------------------------------------------------
# Category Management
# ---------------------------------------------------------------------

@staff_required
def category_list(request):
    categories = Category.objects.annotate(num_products=Count('products'))
    q = request.GET.get('q', '').strip()
    if q:
        categories = categories.filter(name__icontains=q)
    paginator = Paginator(categories, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, "admin_panel/categories.html", {"page_obj": page_obj, "q": q})


@staff_required
def category_add(request):
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Category added successfully.")
            return redirect('admin_categories')
    else:
        form = CategoryForm()
    return render(request, "admin_panel/category_form.html", {"form": form, "is_edit": False})


@staff_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully.")
            return redirect('admin_categories')
    else:
        form = CategoryForm(instance=category)
    return render(request, "admin_panel/category_form.html", {"form": form, "is_edit": True, "category": category})


@staff_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    messages.success(request, "Category deleted.")
    return redirect('admin_categories')


# ---------------------------------------------------------------------
# Order Management
# ---------------------------------------------------------------------

@staff_required
def order_list(request):
    orders = Order.objects.select_related('customer').prefetch_related('items')

    q = request.GET.get('q', '').strip()
    order_status = request.GET.get('order_status', '')
    payment_status = request.GET.get('payment_status', '')

    if q:
        orders = orders.filter(
            Q(full_name__icontains=q) | Q(email__icontains=q) | Q(id__icontains=q)
        )
    if order_status:
        orders = orders.filter(order_status=order_status)
    if payment_status:
        orders = orders.filter(payment_status=payment_status)

    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        "page_obj": page_obj,
        "q": q,
        "selected_order_status": order_status,
        "selected_payment_status": payment_status,
        "order_status_choices": Order.ORDER_STATUS_CHOICES,
        "payment_status_choices": Order.PAYMENT_STATUS_CHOICES,
    }
    return render(request, "admin_panel/orders.html", context)


@staff_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related('items'), pk=pk)
    if request.method == "POST":
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            old_status = order.order_status
            updated_order = form.save()
            if updated_order.order_status != old_status:
                emails.send_order_status_update_email(updated_order)
            messages.success(request, "Order updated successfully.")
            return redirect('admin_order_detail', pk=pk)
    else:
        form = OrderStatusForm(instance=order)
    return render(request, "admin_panel/order_detail.html", {"order": order, "form": form})


# ---------------------------------------------------------------------
# Customer Management
# ---------------------------------------------------------------------

@staff_required
def customer_list(request):
    customers = Customer.objects.select_related('user')

    q = request.GET.get('q', '').strip()
    if q:
        customers = customers.filter(
            Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) |
            Q(user__username__icontains=q) | Q(user__email__icontains=q)
        )

    paginator = Paginator(customers, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, "admin_panel/customers.html", {"page_obj": page_obj, "q": q})


@staff_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    orders = customer.user.orders.all()
    if request.method == "POST":
        customer.user.first_name = request.POST.get('first_name', customer.user.first_name)
        customer.user.last_name = request.POST.get('last_name', customer.user.last_name)
        customer.user.email = request.POST.get('email', customer.user.email)
        customer.phone = request.POST.get('phone', customer.phone)
        customer.address = request.POST.get('address', customer.address)
        customer.user.save()
        customer.save()
        messages.success(request, "Customer updated successfully.")
        return redirect('admin_customer_detail', pk=pk)
    return render(request, "admin_panel/customer_detail.html", {"customer": customer, "orders": orders})


@staff_required
@require_POST
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer.user.delete()  # cascades to Customer via OneToOne
    messages.success(request, "Customer deleted.")
    return redirect('admin_customers')


# ---------------------------------------------------------------------
# Contact Management
# ---------------------------------------------------------------------

@staff_required
def contact_list(request):
    contacts = Contact.objects.all()

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    if q:
        contacts = contacts.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(subject__icontains=q)
        )
    if status:
        contacts = contacts.filter(status=status)

    paginator = Paginator(contacts, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        "page_obj": page_obj,
        "q": q,
        "selected_status": status,
        "status_choices": Contact.STATUS_CHOICES,
    }
    return render(request, "admin_panel/contacts.html", context)


@staff_required
def contact_detail(request, pk):
    contact = get_object_or_404(Contact, pk=pk)

    if contact.status == 'new':
        contact.status = 'read'
        contact.save(update_fields=['status'])

    if request.method == "POST":
        form = ContactReplyForm(request.POST)
        if form.is_valid():
            contact.reply = form.cleaned_data['reply']
            contact.status = 'replied'
            contact.replied_at = timezone.now()
            contact.save()
            emails.send_admin_reply_email(contact, admin_username=request.user.username)
            messages.success(request, "Reply sent to the customer.")
            return redirect('admin_contact_detail', pk=pk)
    else:
        form = ContactReplyForm(initial={'reply': contact.reply})

    return render(request, "admin_panel/contact_detail.html", {"contact": contact, "form": form})


@staff_required
@require_POST
def contact_mark_read(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    contact.status = 'read'
    contact.save(update_fields=['status'])
    messages.success(request, "Marked as read.")
    return redirect('admin_contacts')


@staff_required
@require_POST
def contact_delete(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    contact.delete()
    messages.success(request, "Message deleted.")
    return redirect('admin_contacts')


# ---------------------------------------------------------------------
# Newsletter
# ---------------------------------------------------------------------

@staff_required
def newsletter(request):
    customers = Customer.objects.select_related('user')
    sent_count = None

    if request.method == "POST":
        form = NewsletterForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message_html = form.cleaned_data['message']
            recipients_choice = form.cleaned_data['recipients']

            if recipients_choice == 'all':
                recipient_emails = list(
                    User.objects.exclude(email='').values_list('email', flat=True)
                )
            else:
                selected_ids = request.POST.getlist('selected_customers')
                recipient_emails = list(
                    Customer.objects.filter(id__in=selected_ids).exclude(user__email='')
                    .values_list('user__email', flat=True)
                )

            sent_count = 0
            for email in recipient_emails:
                ok = emails.send_newsletter_email(
                    subject, message_html, email, admin_username=request.user.username
                )
                if ok:
                    sent_count += 1

            messages.success(request, f"Newsletter sent to {sent_count} of {len(recipient_emails)} recipients.")
            return redirect('admin_newsletter')
    else:
        form = NewsletterForm(initial={'recipients': 'all'})

    recent_logs = EmailLog.objects.filter(email_type='newsletter')[:15]

    return render(request, "admin_panel/newsletter.html", {
        "form": form,
        "customers": customers,
        "recent_logs": recent_logs,
        "sent_count": sent_count,
    })


# ---------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------

@staff_required
def admin_settings(request):
    from products.models import PaymentSettings
    settings_obj = PaymentSettings.load()

    if request.method == "POST":
        settings_obj.upi_id = request.POST.get('upi_id', '')
        settings_obj.bank_name = request.POST.get('bank_name', '')
        settings_obj.account_holder_name = request.POST.get('account_holder_name', '')
        settings_obj.account_number = request.POST.get('account_number', '')
        settings_obj.ifsc_code = request.POST.get('ifsc_code', '')
        settings_obj.bank_branch = request.POST.get('bank_branch', '')
        settings_obj.instructions = request.POST.get('instructions', '')
        if request.FILES.get('qr_code'):
            settings_obj.qr_code = request.FILES['qr_code']
        settings_obj.save()
        messages.success(request, "Settings updated successfully.")
        return redirect('admin_settings')

    return render(request, "admin_panel/settings.html", {"settings_obj": settings_obj})


# ---------------------------------------------------------------------
# Business / Analytics Management
# ---------------------------------------------------------------------

@staff_required
def analytics(request):
    today = timezone.localdate()
    paid_orders = Order.objects.filter(payment_status='paid')
    revenue = paid_orders.aggregate(total=Sum('total_price'))['total'] or 0
    avg_order = paid_orders.aggregate(avg=Sum('total_price'))['avg'] or 0
    paid_count = paid_orders.count()
    avg_order_value = (revenue / paid_count) if paid_count else 0

    status_counts = dict(Order.objects.values_list('order_status').annotate(count=Count('id')))
    top_products = (OrderItem.objects.values('product_name')
                    .annotate(units=Sum('quantity'), revenue=Sum('price'))
                    .order_by('-units')[:10])
    low_stock = Product.objects.filter(stock__lte=Product.LOW_STOCK_THRESHOLD).order_by('stock', 'name')
    active_coupons = Coupon.objects.filter(active=True).count()
    pending_reviews = Review.objects.filter(approved=False).count()

    months, sales, orders = [], [], []
    anchor = timezone.now().replace(day=1)
    for i in range(11, -1, -1):
        year = anchor.year
        month = anchor.month - i
        while month <= 0:
            month += 12
            year -= 1
        qs = Order.objects.filter(created_at__year=year, created_at__month=month)
        months.append(f'{year}-{month:02d}')
        sales.append(float(qs.filter(payment_status='paid').aggregate(total=Sum('total_price'))['total'] or 0))
        orders.append(qs.count())

    return render(request, 'admin_panel/analytics.html', {
        'revenue': revenue, 'paid_count': paid_count, 'avg_order_value': avg_order_value,
        'status_counts': status_counts, 'top_products': top_products, 'low_stock': low_stock,
        'active_coupons': active_coupons, 'pending_reviews': pending_reviews,
        'months_json': months, 'sales_json': sales, 'orders_json': orders,
    })


@staff_required
def coupon_list(request):
    coupons = Coupon.objects.all()
    q = request.GET.get('q', '').strip()
    if q:
        coupons = coupons.filter(code__icontains=q)
    return render(request, 'admin_panel/coupons.html', {'coupons': coupons, 'q': q})


@staff_required
def coupon_create(request):
    if request.method == 'POST':
        try:
            code = request.POST.get('code', '').strip().upper()
            if not code:
                raise ValueError('Coupon code is required.')
            if Coupon.objects.filter(code=code).exists():
                raise ValueError('Coupon code already exists.')
            discount_type = request.POST.get('discount_type', 'percentage')
            value = request.POST.get('discount_value', '0')
            minimum = request.POST.get('minimum_order', '0') or '0'
            maximum = request.POST.get('maximum_discount', '') or None
            valid_from = request.POST.get('valid_from') or timezone.now().strftime('%Y-%m-%dT%H:%M')
            valid_until = request.POST.get('valid_until') or None
            Coupon.objects.create(
                code=code, discount_type=discount_type, discount_value=value,
                minimum_order=minimum, maximum_discount=maximum,
                valid_from=valid_from, valid_until=valid_until,
                usage_limit=request.POST.get('usage_limit') or None,
                active=bool(request.POST.get('active')),
            )
            messages.success(request, 'Coupon created successfully.')
            return redirect('admin_coupons')
        except Exception as exc:
            messages.error(request, str(exc))
    return render(request, 'admin_panel/coupon_form.html', {'coupon': None})


@staff_required
def coupon_edit(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == 'POST':
        try:
            coupon.code = request.POST.get('code', coupon.code).strip().upper()
            coupon.discount_type = request.POST.get('discount_type', coupon.discount_type)
            coupon.discount_value = request.POST.get('discount_value', coupon.discount_value)
            coupon.minimum_order = request.POST.get('minimum_order', coupon.minimum_order)
            coupon.maximum_discount = request.POST.get('maximum_discount') or None
            coupon.valid_from = request.POST.get('valid_from') or coupon.valid_from
            coupon.valid_until = request.POST.get('valid_until') or None
            coupon.usage_limit = request.POST.get('usage_limit') or None
            coupon.active = bool(request.POST.get('active'))
            coupon.save()
            messages.success(request, 'Coupon updated successfully.')
            return redirect('admin_coupons')
        except Exception as exc:
            messages.error(request, str(exc))
    return render(request, 'admin_panel/coupon_form.html', {'coupon': coupon})


@staff_required
@require_POST
def coupon_toggle(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon.active = not coupon.active
    coupon.save(update_fields=['active'])
    messages.success(request, f"Coupon {coupon.code} is now {'active' if coupon.active else 'inactive'}.")
    return redirect('admin_coupons')


@staff_required
@require_POST
def coupon_delete(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon.delete()
    messages.success(request, 'Coupon deleted.')
    return redirect('admin_coupons')


@staff_required
def review_list(request):
    reviews = Review.objects.select_related('product', 'user').all()
    status = request.GET.get('status', '')
    if status == 'pending':
        reviews = reviews.filter(approved=False)
    elif status == 'approved':
        reviews = reviews.filter(approved=True)
    return render(request, 'admin_panel/reviews.html', {'reviews': reviews, 'selected_status': status})


@staff_required
@require_POST
def review_toggle(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.approved = not review.approved
    review.save(update_fields=['approved'])
    messages.success(request, 'Review moderation status updated.')
    return redirect('admin_reviews')


@staff_required
@require_POST
def review_delete(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.delete()
    messages.success(request, 'Review deleted.')
    return redirect('admin_reviews')


@staff_required
def inventory(request):
    products = Product.objects.select_related('category').all().order_by('stock', 'name')
    status = request.GET.get('status', '')
    if status == 'low':
        products = products.filter(stock__lte=Product.LOW_STOCK_THRESHOLD)
    elif status == 'out':
        products = products.filter(stock=0)
    return render(request, 'admin_panel/inventory.html', {'products': products, 'selected_status': status})


@staff_required
@require_POST
def inventory_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        stock = max(0, int(request.POST.get('stock', product.stock)))
        product.stock = stock
        product.save(update_fields=['stock'])
        messages.success(request, f'{product.name} stock updated to {stock}.')
    except ValueError:
        messages.error(request, 'Stock must be a whole number.')
    return redirect('admin_inventory')


@staff_required
def payment_overview(request):
    paid = Order.objects.filter(payment_status='paid').aggregate(total=Sum('total_price'))['total'] or 0
    pending = Order.objects.filter(payment_status='pending').aggregate(total=Sum('total_price'))['total'] or 0
    failed = Order.objects.filter(payment_status='failed').aggregate(total=Sum('total_price'))['total'] or 0
    methods = list(Order.objects.values('payment_method').annotate(count=Count('id'), amount=Sum('total_price')).order_by('-count'))
    recent = Order.objects.select_related('customer').order_by('-updated_at')[:30]
    return render(request, 'admin_panel/payments.html', {
        'paid': paid, 'pending': pending, 'failed': failed, 'methods': methods, 'recent': recent,
    })


@staff_required
def export_orders_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="goody-orders.csv"'
    import csv
    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Customer', 'Email', 'Total', 'Payment Status', 'Order Status', 'Created'])
    for order in Order.objects.all().iterator():
        writer.writerow([order.id, order.customer_name, order.email, order.total_price,
                         order.payment_status, order.order_status, order.created_at.strftime('%Y-%m-%d %H:%M')])
    return response
