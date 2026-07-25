from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.shortcuts import render, redirect, get_object_or_404
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
