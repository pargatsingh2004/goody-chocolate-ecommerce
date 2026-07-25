from decimal import Decimal

from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse, JsonResponse

from .models import (
    Product, PaymentSettings, Wishlist, Category,
    Customer, Order, OrderItem, Contact, NewsletterSubscriber,
)
from . import emails

CART_SESSION_KEY = "cart"


# ---------------------------------------------------------------------
# Cart helpers
# ---------------------------------------------------------------------

def _get_cart(request):
    """Return the raw {product_id_str: quantity} dict stored in the session."""
    return request.session.get(CART_SESSION_KEY, {})


def _save_cart(request, cart):
    request.session[CART_SESSION_KEY] = cart
    request.session.modified = True


def _build_cart_context(request):
    """Turn the session cart into template-ready cart_items + totals."""
    cart = _get_cart(request)
    cart_items = []
    subtotal = Decimal("0")

    if cart:
        products = Product.objects.filter(id__in=cart.keys())
        products_by_id = {str(p.id): p for p in products}

        for product_id, quantity in cart.items():
            product = products_by_id.get(product_id)
            if not product:
                continue
            line_total = product.discounted_price * quantity
            subtotal += line_total
            cart_items.append({
                "product": product,
                "quantity": quantity,
                "total": line_total,
            })

    shipping = Decimal("99") if cart_items else Decimal("0")
    total = subtotal + shipping

    return {
        "cart_items": cart_items,
        "subtotal": subtotal,
        "shipping": shipping,
        "total": total,
    }


def cart_item_count(request):
    """Used by the context processor to show a badge in the navbar."""
    return sum(_get_cart(request).values())


# ---------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------

def wishlist(request):
    if request.user.is_authenticated:
        items = Wishlist.objects.filter(user=request.user)
    else:
        items = Wishlist.objects.none()
    return render(request, "products/wishlist.html", {"items": items})


@login_required(login_url='login')
def add_to_wishlist(request, id):
    product = get_object_or_404(Product, id=id)
    Wishlist.objects.get_or_create(user=request.user, product=product)
    messages.success(request, f"{product} added to wishlist.")
    return redirect("wishlist")


@login_required(login_url='login')
def remove_from_wishlist(request, id):
    Wishlist.objects.filter(id=id, user=request.user).delete()
    messages.success(request, "Item removed from wishlist.")
    return redirect("wishlist")


def home(request):
    featured_products = Product.objects.filter(featured=True, status='active')[:8]

    if not featured_products:
        featured_products = Product.objects.filter(status='active').order_by('-id')[:8]

    return render(request, "products/home.html", {"products": featured_products})


def shop(request):
    products = Product.objects.filter(status='active').order_by('-id')

    category_id = request.GET.get('category')
    selected_category = None
    if category_id:
        products = products.filter(category_id=category_id)
        selected_category = Category.objects.filter(id=category_id).first()

    context = {
        'products': products,
        'categories': Category.objects.all(),
        'selected_category': selected_category,
    }

    return render(request, 'products/shop.html', context)


def search(request):
    query = request.GET.get("q", "")

    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            status='active',
        )
    else:
        products = Product.objects.filter(status='active')

    return render(request, "products/search.html", {
        "products": products,
        "query": query,
    })


def about(request):
    return render(request, "products/about.html")


def contact(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        subject = request.POST.get("subject", "").strip()
        message = request.POST.get("message", "").strip()

        if not (name and email and subject and message):
            messages.error(request, "Please fill in all required fields.")
            return render(request, "products/contact.html", {
                "form_data": request.POST,
            })

        contact_obj = Contact.objects.create(
            name=name, email=email, phone=phone,
            subject=subject, message=message,
        )

        emails.send_contact_confirmation_email(contact_obj)

        messages.success(request, "Your message has been sent! We'll get back to you shortly.")
        return redirect("contact")

    return render(request, "products/contact.html")


def product_detail(request, id):
    product = get_object_or_404(Product, id=id)

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.info(request, "Please login to add items to your cart.")
            return redirect(f"{reverse('login')}?next={request.path}")

        quantity = int(request.POST.get("quantity", 1))
        cart = _get_cart(request)
        key = str(product.id)
        cart[key] = cart.get(key, 0) + max(quantity, 1)
        _save_cart(request, cart)
        messages.success(request, f"{product.name} added to your cart.")
        return redirect("cart")

    related_products = Product.objects.filter(
        category=product.category, status='active'
    ).exclude(id=id)[:4]

    context = {
        "product": product,
        "related_products": related_products,
    }

    return render(request, "products/product_detail.html", context)


@login_required(login_url='login')
def add_to_cart(request, id):
    product = get_object_or_404(Product, id=id)
    quantity = 1

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1) or 1)

    cart = _get_cart(request)
    key = str(product.id)
    cart[key] = cart.get(key, 0) + max(quantity, 1)
    _save_cart(request, cart)

    messages.success(request, f"{product.name} added to your cart.")
    return redirect(request.META.get("HTTP_REFERER") or "cart")


@login_required(login_url='login')
def update_cart_item(request, id):
    """Increase/decrease quantity. action=inc|dec passed as POST/GET param."""
    cart = _get_cart(request)
    key = str(id)

    if key in cart:
        action = request.POST.get("action") or request.GET.get("action")
        if action == "inc":
            cart[key] += 1
        elif action == "dec":
            cart[key] -= 1
            if cart[key] <= 0:
                del cart[key]

    _save_cart(request, cart)
    return redirect("cart")


@login_required(login_url='login')
def remove_from_cart(request, id):
    cart = _get_cart(request)
    key = str(id)

    if key in cart:
        del cart[key]
        _save_cart(request, cart)
        messages.success(request, "Item removed from cart.")

    return redirect("cart")


@login_required(login_url='login')
def cart(request):
    context = _build_cart_context(request)
    return render(request, "products/cart.html", context)


@login_required(login_url='login')
def checkout(request):
    context = _build_cart_context(request)
    context["payment_settings"] = PaymentSettings.load()

    if request.method == "POST":
        if not context["cart_items"]:
            messages.error(request, "Your cart is empty.")
            return redirect("shop")

        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        pincode = request.POST.get("pincode", "").strip()
        notes = request.POST.get("notes", "").strip()
        payment_method = request.POST.get("payment_method", "cod")

        order = Order.objects.create(
            customer=request.user,
            full_name=f"{first_name} {last_name}".strip(),
            email=email,
            phone=phone,
            address=address,
            city=city,
            state=state,
            pincode=pincode,
            notes=notes,
            payment_method=payment_method,
            subtotal=context["subtotal"],
            shipping_fee=context["shipping"],
            total_price=context["total"],
        )

        for item in context["cart_items"]:
            product = item["product"]
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                quantity=item["quantity"],
                price=product.discounted_price,
            )
            # reduce stock
            if product.stock >= item["quantity"]:
                product.stock -= item["quantity"]
                product.save(update_fields=["stock"])

        emails.send_order_confirmation_email(order)

        _save_cart(request, {})
        messages.success(request, "Your order has been placed! We'll be in touch shortly.")
        return redirect("home")

    return render(request, "products/checkout.html", context)


def newsletter_subscribe(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        if email:
            NewsletterSubscriber.objects.get_or_create(email=email)
            messages.success(request, "You're subscribed! Sweet offers are on the way.")
        else:
            messages.error(request, "Please enter a valid email address.")
    return redirect(request.META.get("HTTP_REFERER") or "home")


# ---------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------

def login(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        remember = request.POST.get("remember")
        next_url = request.POST.get("next") or request.GET.get("next")

        if not User.objects.filter(username=username).exists():
            error = "You are not registered. Please register first."
            messages.error(request, error)
            return render(request, "products/login.html", {
                "error": error,
                "username": username,
                "next": next_url,
            })

        user = authenticate(request, username=username, password=password)

        if user:
            auth_login(request, user)
            if remember:
                request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
            else:
                request.session.set_expiry(0)  # expires on browser close
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect(next_url or "home")

        error = "Incorrect password. Please try again."
        messages.error(request, error)
        return render(request, "products/login.html", {
            "error": error,
            "username": username,
            "next": next_url,
        })

    return render(request, "products/login.html", {"next": request.GET.get("next")})


def user_logout(request):
    auth_logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")


def register(request):

    if request.method == "POST":

        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("register")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name
        )

        user.save()
        # Customer profile is auto-created via the post_save signal.

        emails.send_welcome_email(user)

        messages.success(request, "Account created successfully! A welcome email is on its way.")

        return redirect("login")

    return render(request, "products/register.html")

