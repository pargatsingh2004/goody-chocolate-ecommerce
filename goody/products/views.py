from datetime import timedelta
import random
import time
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login as auth_login,
    logout as auth_logout,
    get_user_model,
)
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Avg
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import json

import razorpay

from . import emails
from .models import (
    Category,
    Contact,
    Customer,
    NewsletterSubscriber,
    Order,
    OrderItem,
    PaymentSettings,
    Product,
    Wishlist,
    EmailOTP,
    Address,
    Coupon,
    CouponUsage,
    Review,
    OrderStatusHistory,
)


CART_SESSION_KEY = "cart"


# =====================================================================
# EMAIL HELPER
# =====================================================================

def _get_email_sender():
    """
    Return the configured sender email.

    DEFAULT_FROM_EMAIL is preferred. If it is empty, EMAIL_HOST_USER
    is used as a fallback.

    Raises ValueError when no valid sender is configured.
    """

    sender = (
        getattr(settings, "DEFAULT_FROM_EMAIL", "")
        or getattr(settings, "EMAIL_HOST_USER", "")
        or ""
    ).strip()

    if not sender:
        raise ValueError(
            "Email sender is not configured. "
            "Set EMAIL_HOST_USER and DEFAULT_FROM_EMAIL in your .env file."
        )

    if "@" not in sender:
        raise ValueError(
            "Invalid email sender configuration. "
            "Check DEFAULT_FROM_EMAIL in your .env file."
        )

    return sender


def _send_app_email(subject, message, recipient):
    """
    Send an application email using the configured sender.

    All application OTP emails should use this helper instead of
    passing an empty from_email value.
    """

    recipient = (recipient or "").strip()

    if not recipient or "@" not in recipient:
        raise ValueError("Invalid recipient email address.")

    sender = _get_email_sender()

    return send_mail(
        subject=subject,
        message=message,
        from_email=sender,
        recipient_list=[recipient],
        fail_silently=False,
    )


# =====================================================================
# CART HELPERS
# =====================================================================

def _get_cart(request):
    """
    Return the cart stored in the user's session.

    Format:
    {
        "1": 2,
        "5": 1,
    }
    """
    return request.session.get(CART_SESSION_KEY, {})


def _save_cart(request, cart):
    """Save the cart back into the user's session."""
    request.session[CART_SESSION_KEY] = cart
    request.session.modified = True


def _get_coupon(request):
    code = request.session.get("coupon_code")

    if not code:
        return None

    return Coupon.objects.filter(
        code=code.upper()
    ).first()


def _build_cart_context(request):
    cart = _get_cart(request)

    cart_items = []
    subtotal = Decimal("0.00")

    if cart:

        products = Product.objects.filter(
            id__in=cart.keys(),
            status="active",
        )

        products_by_id = {
            str(product.id): product
            for product in products
        }

        cleaned_cart = {}

        for product_id, raw_quantity in cart.items():

            product = products_by_id.get(
                str(product_id)
            )

            if not product or product.stock <= 0:
                continue

            try:
                quantity = max(
                    int(raw_quantity),
                    1,
                )
            except (TypeError, ValueError):
                quantity = 1

            quantity = min(
                quantity,
                product.stock,
            )

            cleaned_cart[str(product.id)] = quantity

            line_total = (
                product.discounted_price
                * quantity
            )

            subtotal += line_total

            cart_items.append(
                {
                    "product": product,
                    "quantity": quantity,
                    "total": line_total,
                }
            )

        if cleaned_cart != cart:
            _save_cart(
                request,
                cleaned_cart,
            )

    shipping = (
        Decimal("99.00")
        if cart_items
        and subtotal < Decimal("999.00")
        else Decimal("0.00")
    )

    coupon = _get_coupon(request)

    discount = (
        coupon.calculate_discount(subtotal)
        if coupon
        else Decimal("0.00")
    )

    if coupon and discount <= 0:

        request.session.pop(
            "coupon_code",
            None,
        )

        coupon = None

    total = max(
        Decimal("0.00"),
        subtotal + shipping - discount,
    )

    return {
        "cart_items": cart_items,
        "subtotal": subtotal,
        "shipping": shipping,
        "coupon": coupon,
        "discount_amount": discount,
        "total": total,
    }


def cart_item_count(request):
    """Return total quantity of products in cart."""

    total = 0

    for quantity in _get_cart(request).values():

        try:
            total += int(quantity)

        except (TypeError, ValueError):
            continue

    return total


# =====================================================================
# WISHLIST
# =====================================================================

@login_required(login_url="login")
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(
        user=request.user
    ).select_related("product")

    return render(
        request,
        "products/wishlist.html",
        {
            "wishlist_items": wishlist_items,
        },
    )


@login_required(login_url="login")
def add_to_wishlist(request, id):
    if request.method != "POST":
        return redirect("product_detail", id=id)

    product = get_object_or_404(
        Product,
        id=id,
        status="active",
    )

    Wishlist.objects.get_or_create(
        user=request.user,
        product=product,
    )

    messages.success(
        request,
        f"{product.name} added to wishlist."
    )

    return redirect("wishlist")


@login_required(login_url="login")
def remove_from_wishlist(request, id):

    if request.method != "POST":
        return redirect("wishlist")

    Wishlist.objects.filter(
        id=id,
        user=request.user,
    ).delete()

    messages.success(
        request,
        "Item removed from wishlist."
    )

    return redirect("wishlist")

# =====================================================================
# HOME
# =====================================================================

def home(request):

    featured_products = Product.objects.filter(
        featured=True,
        status="active",
    )[:8]

    if not featured_products:

        featured_products = Product.objects.filter(
            status="active"
        ).order_by("-id")[:8]

    return render(
        request,
        "products/home.html",
        {
            "products": featured_products,
        },
    )


# =====================================================================
# SHOP
# =====================================================================

def shop(request):

    products = Product.objects.filter(
        status="active"
    ).order_by("-id")

    category_id = request.GET.get(
        "category"
    )

    selected_category = None

    if category_id:

        products = products.filter(
            category_id=category_id
        )

        selected_category = (
            Category.objects.filter(
                id=category_id
            ).first()
        )

    context = {
        "products": products,
        "categories": Category.objects.all(),
        "selected_category": selected_category,
    }

    return render(
        request,
        "products/shop.html",
        context,
    )


# =====================================================================
# SEARCH
# =====================================================================

def search(request):

    query = request.GET.get(
        "q",
        "",
    ).strip()

    if query:

        products = Product.objects.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query),
            status="active",
        ).order_by("-id")

    else:

        products = Product.objects.filter(
            status="active"
        ).order_by("-id")

    return render(
        request,
        "products/search.html",
        {
            "products": products,
            "query": query,
        },
    )


# =====================================================================
# ABOUT
# =====================================================================

def about(request):

    return render(
        request,
        "products/about.html",
    )


# =====================================================================
# CONTACT
# =====================================================================

def contact(request):

    if request.method == "POST":

        name = request.POST.get(
            "name",
            "",
        ).strip()

        email = request.POST.get(
            "email",
            "",
        ).strip().lower()

        phone = request.POST.get(
            "phone",
            "",
        ).strip()

        subject = request.POST.get(
            "subject",
            "",
        ).strip()

        message = request.POST.get(
            "message",
            "",
        ).strip()

        if not name or not email or not subject or not message:

            messages.error(
                request,
                "Please fill in all required fields.",
            )

            return render(
                request,
                "products/contact.html",
                {
                    "form_data": request.POST,
                },
            )

        contact_obj = Contact.objects.create(
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message,
        )

        try:

            emails.send_contact_confirmation_email(
                contact_obj
            )

        except Exception:
            # Keep contact request even when email fails.
            pass

        messages.success(
            request,
            "Your message has been sent! We'll get back to you shortly.",
        )

        return redirect("contact")

    return render(
        request,
        "products/contact.html",
    )


# =====================================================================
# PRODUCT DETAIL
# =====================================================================

def product_detail(request, id):

    product = get_object_or_404(
        Product,
        id=id,
        status="active",
    )

    if request.method == "POST":

        if not request.user.is_authenticated:

            messages.info(
                request,
                "Please login to add items to your cart.",
            )

            return redirect(
                f"{reverse('login')}?next={request.path}"
            )

        try:

            quantity = int(
                request.POST.get(
                    "quantity",
                    1,
                )
            )

        except (TypeError, ValueError):

            quantity = 1

        quantity = max(
            quantity,
            1,
        )

        if product.stock <= 0:

            messages.error(
                request,
                "This product is currently out of stock.",
            )

            return redirect(
                "product_detail",
                id=product.id,
            )

        cart = _get_cart(request)

        key = str(product.id)

        try:
            current_quantity = int(
                cart.get(key, 0)
            )
        except (TypeError, ValueError):
            current_quantity = 0

        new_quantity = (
            current_quantity
            + quantity
        )

        if new_quantity > product.stock:

            messages.warning(
                request,
                f"Only {product.stock} item(s) are available.",
            )

            return redirect(
                "product_detail",
                id=product.id,
            )

        cart[key] = new_quantity

        _save_cart(
            request,
            cart,
        )

        messages.success(
            request,
            f"{product.name} added to your cart.",
        )

        return redirect("cart")

    related_products = Product.objects.filter(
        category=product.category,
        status="active",
    ).exclude(
        id=id
    )[:4]

    reviews = (
        product.reviews
        .filter(approved=True)
        .select_related("user")
    )

    average_rating = (
        reviews.aggregate(
            avg=Avg("rating")
        )["avg"]
        if reviews.exists()
        else 0
    )

    context = {
        "product": product,
        "related_products": related_products,
        "reviews": reviews,
        "average_rating": average_rating,
        "review_count": reviews.count(),
    }

    return render(
        request,
        "products/product_detail.html",
        context,
    )


# =====================================================================
# ADD TO CART
# =====================================================================

@login_required(login_url="login")
def add_to_cart(request, id):

    if request.method != "POST":

        return redirect(
            request.META.get(
                "HTTP_REFERER"
            ) or "cart"
        )

    product = get_object_or_404(
        Product,
        id=id,
        status="active",
    )

    try:

        quantity = int(
            request.POST.get(
                "quantity",
                1,
            )
        )

    except (TypeError, ValueError):

        quantity = 1

    quantity = max(
        quantity,
        1,
    )

    if product.stock <= 0:

        messages.error(
            request,
            "This product is currently out of stock.",
        )

        return redirect(
            request.META.get(
                "HTTP_REFERER"
            ) or "shop"
        )

    cart = _get_cart(request)

    key = str(product.id)

    try:

        current_quantity = int(
            cart.get(key, 0)
        )

    except (TypeError, ValueError):

        current_quantity = 0

    new_quantity = (
        current_quantity
        + quantity
    )

    if new_quantity > product.stock:

        messages.warning(
            request,
            f"Only {product.stock} item(s) are available.",
        )

        return redirect(
            request.META.get(
                "HTTP_REFERER"
            ) or "cart"
        )

    cart[key] = new_quantity

    _save_cart(
        request,
        cart,
    )

    messages.success(
        request,
        f"{product.name} added to your cart.",
    )

    return redirect(
        request.META.get(
            "HTTP_REFERER"
        ) or "cart"
    )


# =====================================================================
# UPDATE CART
# =====================================================================

@login_required(login_url="login")
def update_cart_item(request, id):

    if request.method != "POST":
        return redirect("cart")

    cart = _get_cart(request)

    key = str(id)

    if key not in cart:
        return redirect("cart")

    action = request.POST.get(
        "action"
    )

    try:

        current_quantity = int(
            cart[key]
        )

    except (TypeError, ValueError):

        current_quantity = 1

    product = Product.objects.filter(
        id=id,
        status="active",
    ).first()

    if not product:

        del cart[key]

        _save_cart(
            request,
            cart,
        )

        return redirect("cart")

    if action == "inc":

        if current_quantity < product.stock:

            cart[key] = (
                current_quantity + 1
            )

        else:

            messages.warning(
                request,
                f"Only {product.stock} item(s) are available.",
            )

    elif action == "dec":

        current_quantity -= 1

        if current_quantity <= 0:

            del cart[key]

        else:

            cart[key] = current_quantity

    _save_cart(
        request,
        cart,
    )

    return redirect("cart")


# =====================================================================
# REMOVE FROM CART
# =====================================================================

@login_required(login_url="login")
def remove_from_cart(request, id):

    if request.method != "POST":
        return redirect("cart")

    cart = _get_cart(request)

    key = str(id)

    if key in cart:

        del cart[key]

        _save_cart(
            request,
            cart,
        )

        messages.success(
            request,
            "Item removed from cart.",
        )

    return redirect("cart")


# =====================================================================
# CART
# =====================================================================

@login_required(login_url="login")
def cart(request):

    context = _build_cart_context(
        request
    )

    return render(
        request,
        "products/cart.html",
        context,
    )


# =====================================================================
# COUPONS
# =====================================================================

def apply_coupon(request):

    if request.method != "POST":
        return redirect("cart")

    code = request.POST.get(
        "coupon_code",
        "",
    ).strip().upper()

    if not code:

        messages.error(
            request,
            "Please enter a coupon code.",
        )

        return redirect("cart")

    coupon = Coupon.objects.filter(
        code=code
    ).first()

    if not coupon:

        messages.error(
            request,
            "Invalid coupon code.",
        )

        return redirect("cart")

    context = _build_cart_context(
        request
    )

    if not context["cart_items"]:

        messages.error(
            request,
            "Add products to your cart before applying a coupon.",
        )

        return redirect("cart")

    if not coupon.is_valid(
        context["subtotal"]
    ):

        messages.error(
            request,
            "This coupon is expired, inactive, already used up, or does not meet the minimum order value.",
        )

        return redirect("cart")

    if CouponUsage.objects.filter(
        coupon=coupon,
        user=request.user,
    ).exists():

        messages.error(
            request,
            "You have already used this coupon.",
        )

        return redirect("cart")

    request.session["coupon_code"] = (
        coupon.code
    )

    request.session.modified = True

    messages.success(
        request,
        f"Coupon {coupon.code} applied successfully.",
    )

    return redirect("cart")


def remove_coupon(request):

    if request.method == "POST":

        request.session.pop(
            "coupon_code",
            None,
        )

        messages.success(
            request,
            "Coupon removed.",
        )

    return redirect("cart")


# =====================================================================
# CHECKOUT
# =====================================================================

@login_required(login_url="login")
def checkout(request):

    context = _build_cart_context(
        request
    )

    context["payment_settings"] = (
        PaymentSettings.load()
    )

    context["addresses"] = (
        request.user.addresses.all()
    )

    context["default_address"] = (
        request.user.addresses
        .filter(is_default=True)
        .first()
    )

    if not context["cart_items"]:

        messages.info(
            request,
            "Your cart is empty.",
        )

        return redirect("shop")

    if request.method == "POST":

        payment_method = (
            request.POST.get(
                "payment_method",
                "cod",
            )
            .strip()
            .lower()
        )

        allowed_payment_methods = {
            choice[0]
            for choice in Order.PAYMENT_METHOD_CHOICES
        }

        if payment_method not in allowed_payment_methods:

            messages.error(
                request,
                "Please select a valid payment method.",
            )

            return render(
                request,
                "products/checkout.html",
                context,
            )

        if payment_method == "razorpay":

            messages.info(
                request,
                "Please use the Online Payment button to continue.",
            )

            return render(
                request,
                "products/checkout.html",
                context,
            )

        address_obj = None

        selected_address_id = (
            request.POST.get(
                "address_id",
                "",
            )
            .strip()
        )

        if selected_address_id:

            try:

                address_obj = (
                    request.user.addresses.get(
                        pk=int(selected_address_id)
                    )
                )

            except (
                ValueError,
                TypeError,
                Address.DoesNotExist,
            ):

                messages.error(
                    request,
                    "The selected address could not be found.",
                )

                return render(
                    request,
                    "products/checkout.html",
                    context,
                )

        first_name = request.POST.get(
            "first_name",
            "",
        ).strip()

        last_name = request.POST.get(
            "last_name",
            "",
        ).strip()

        email = request.POST.get(
            "email",
            "",
        ).strip().lower()

        phone = request.POST.get(
            "phone",
            "",
        ).strip()

        address = request.POST.get(
            "address",
            "",
        ).strip()

        city = request.POST.get(
            "city",
            "",
        ).strip()

        state = request.POST.get(
            "state",
            "",
        ).strip()

        pincode = request.POST.get(
            "pincode",
            "",
        ).strip()

        notes = request.POST.get(
            "notes",
            "",
        ).strip()

        if address_obj:

            parts = (
                address_obj.full_name
                .strip()
                .split()
            )

            first_name = (
                parts[0]
                if parts
                else ""
            )

            last_name = (
                " ".join(parts[1:])
            )

            phone = address_obj.phone
            address = address_obj.address_line
            city = address_obj.city
            state = address_obj.state
            pincode = address_obj.pincode

        if not all(
            [
                first_name,
                email,
                phone,
                address,
                city,
                state,
                pincode,
            ]
        ):

            messages.error(
                request,
                "Please complete your delivery address and contact details.",
            )

            context["checkout_data"] = (
                request.POST
            )

            return render(
                request,
                "products/checkout.html",
                context,
            )

        if (
            "@"
            not in email
            or "."
            not in email.split("@")[-1]
        ):

            messages.error(
                request,
                "Please enter a valid email address.",
            )

            return render(
                request,
                "products/checkout.html",
                context,
            )

        normalized_phone = (
            phone
            .replace("+", "")
            .replace(" ", "")
            .replace("-", "")
        )

        if (
            not normalized_phone.isdigit()
            or not 10
            <= len(normalized_phone)
            <= 15
        ):

            messages.error(
                request,
                "Please enter a valid phone number.",
            )

            return render(
                request,
                "products/checkout.html",
                context,
            )

        if not pincode.isdigit() or len(pincode) != 6:

            messages.error(
                request,
                "Please enter a valid 6-digit pincode.",
            )

            return render(
                request,
                "products/checkout.html",
                context,
            )

        if (
            not address_obj
            and request.POST.get(
                "save_address"
            )
            == "on"
        ):

            full_name = (
                f"{first_name} {last_name}"
                .strip()
            )

            Address.objects.create(
                user=request.user,
                label=(
                    request.POST.get(
                        "address_label",
                        "Home",
                    )
                    .strip()
                    or "Home"
                ),
                full_name=full_name,
                phone=phone,
                address_line=address,
                city=city,
                state=state,
                pincode=pincode,
                is_default=(
                    request.user.addresses.count()
                    == 0
                ),
            )

            context["addresses"] = (
                request.user.addresses.all()
            )

        try:

            with transaction.atomic():

                fresh_cart = (
                    _build_cart_context(
                        request
                    )
                )

                if not fresh_cart["cart_items"]:
                    raise ValueError(
                        "Your cart is empty."
                    )

                order = Order.objects.create(
                    customer=request.user,
                    full_name=(
                        f"{first_name} {last_name}"
                        .strip()
                    ),
                    email=email,
                    phone=phone,
                    address=address,
                    city=city,
                    state=state,
                    pincode=pincode,
                    notes=notes,
                    payment_method=payment_method,
                    subtotal=fresh_cart[
                        "subtotal"
                    ],
                    shipping_fee=fresh_cart[
                        "shipping"
                    ],
                    discount_amount=fresh_cart[
                        "discount_amount"
                    ],
                    total_price=fresh_cart[
                        "total"
                    ],
                    coupon=fresh_cart[
                        "coupon"
                    ],
                )

                for item in fresh_cart[
                    "cart_items"
                ]:

                    product = (
                        Product.objects
                        .select_for_update()
                        .get(
                            pk=item[
                                "product"
                            ].pk
                        )
                    )

                    quantity = item[
                        "quantity"
                    ]

                    if (
                        product.status
                        != "active"
                        or product.stock
                        < quantity
                    ):

                        raise ValueError(
                            f"{product.name} is no longer available in the requested quantity."
                        )

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        quantity=quantity,
                        price=(
                            product.discounted_price
                        ),
                    )

                    product.stock -= quantity

                    product.save(
                        update_fields=[
                            "stock"
                        ]
                    )

                if fresh_cart["coupon"]:

                    coupon = (
                        Coupon.objects
                        .select_for_update()
                        .get(
                            pk=fresh_cart[
                                "coupon"
                            ].pk
                        )
                    )

                    if not coupon.is_valid(
                        fresh_cart["subtotal"]
                    ):

                        raise ValueError(
                            "The coupon is no longer valid. Please review your cart."
                        )

                    if CouponUsage.objects.filter(
                        coupon=coupon,
                        user=request.user,
                    ).exists():

                        raise ValueError(
                            "You have already used this coupon."
                        )

                    coupon.used_count += 1

                    coupon.save(
                        update_fields=[
                            "used_count"
                        ]
                    )

                    CouponUsage.objects.create(
                        coupon=coupon,
                        user=request.user,
                        order=order,
                    )

                OrderStatusHistory.objects.create(
                    order=order,
                    status=order.order_status,
                    note="Order placed successfully.",
                )

        except ValueError as error:

            messages.error(
                request,
                str(error),
            )

            return redirect("cart")

        except Exception:

            messages.error(
                request,
                "Something went wrong while placing your order. Please try again.",
            )

            return render(
                request,
                "products/checkout.html",
                context,
            )

        try:

            emails.send_order_confirmation_email(
                order
            )

        except Exception:

            pass

        _save_cart(
            request,
            {},
        )

        request.session.pop(
            "coupon_code",
            None,
        )

        request.session.modified = True

        return redirect(
            "order_success",
            id=order.id,
        )

    return render(
        request,
        "products/checkout.html",
        context,
    )


@login_required(login_url="login")
def order_success(request, id):

    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items",
            "status_history",
        ),
        pk=id,
        customer=request.user,
    )

    return render(
        request,
        "products/order_success.html",
        {
            "order": order
        },
    )


# =====================================================================
# RAZORPAY
# =====================================================================

def _razorpay_client():

    if (
        not settings.RAZORPAY_KEY_ID
        or not settings.RAZORPAY_KEY_SECRET
    ):

        raise ValueError(
            "Online payment is not configured yet. "
            "Add Razorpay credentials to your .env file."
        )

    return razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET,
        )
    )


def _checkout_customer_data(request):
    """Validate checkout data and return normalized delivery data."""

    address_obj = None

    selected_address_id = (
        request.POST.get(
            "address_id",
            "",
        )
        .strip()
    )

    if selected_address_id:

        try:

            address_obj = (
                request.user.addresses.get(
                    pk=int(selected_address_id)
                )
            )

        except (
            ValueError,
            TypeError,
            Address.DoesNotExist,
        ):

            raise ValueError(
                "The selected address could not be found."
            )

    first_name = request.POST.get(
        "first_name",
        "",
    ).strip()

    last_name = request.POST.get(
        "last_name",
        "",
    ).strip()

    email = request.POST.get(
        "email",
        "",
    ).strip().lower()

    phone = request.POST.get(
        "phone",
        "",
    ).strip()

    address = request.POST.get(
        "address",
        "",
    ).strip()

    city = request.POST.get(
        "city",
        "",
    ).strip()

    state = request.POST.get(
        "state",
        "",
    ).strip()

    pincode = request.POST.get(
        "pincode",
        "",
    ).strip()

    notes = request.POST.get(
        "notes",
        "",
    ).strip()

    if address_obj:

        parts = (
            address_obj.full_name
            .strip()
            .split()
        )

        first_name = (
            parts[0]
            if parts
            else ""
        )

        last_name = (
            " ".join(parts[1:])
        )

        phone = address_obj.phone
        address = address_obj.address_line
        city = address_obj.city
        state = address_obj.state
        pincode = address_obj.pincode

    if not all(
        [
            first_name,
            email,
            phone,
            address,
            city,
            state,
            pincode,
        ]
    ):

        raise ValueError(
            "Please complete your delivery address and contact details."
        )

    if (
        "@"
        not in email
        or "."
        not in email.split("@")[-1]
    ):

        raise ValueError(
            "Please enter a valid email address."
        )

    normalized_phone = (
        phone
        .replace("+", "")
        .replace(" ", "")
        .replace("-", "")
    )

    if (
        not normalized_phone.isdigit()
        or not 10
        <= len(normalized_phone)
        <= 15
    ):

        raise ValueError(
            "Please enter a valid phone number."
        )

    if not pincode.isdigit() or len(pincode) != 6:

        raise ValueError(
            "Please enter a valid 6-digit pincode."
        )

    return {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "address": address,
        "city": city,
        "state": state,
        "pincode": pincode,
        "notes": notes,
        "address_obj": address_obj,
    }


def _create_pending_razorpay_order(request, data):
    """
    Create a pending local order and its Razorpay order
    without reducing stock.
    """

    with transaction.atomic():

        fresh_cart = _build_cart_context(
            request
        )

        if not fresh_cart["cart_items"]:

            raise ValueError(
                "Your cart is empty."
            )

        locked_items = []

        for item in fresh_cart[
            "cart_items"
        ]:

            product = (
                Product.objects
                .select_for_update()
                .get(
                    pk=item[
                        "product"
                    ].pk
                )
            )

            if (
                product.status != "active"
                or product.stock
                < item["quantity"]
            ):

                raise ValueError(
                    f"{product.name} is no longer available in the requested quantity."
                )

            locked_items.append(
                (
                    product,
                    item["quantity"],
                )
            )

        order = Order.objects.create(
            customer=request.user,
            full_name=(
                f'{data["first_name"]} '
                f'{data["last_name"]}'
            ).strip(),
            email=data["email"],
            phone=data["phone"],
            address=data["address"],
            city=data["city"],
            state=data["state"],
            pincode=data["pincode"],
            notes=data["notes"],
            payment_method="razorpay",
            payment_status="pending",
            order_status="pending",
            subtotal=fresh_cart[
                "subtotal"
            ],
            shipping_fee=fresh_cart[
                "shipping"
            ],
            discount_amount=fresh_cart[
                "discount_amount"
            ],
            total_price=fresh_cart[
                "total"
            ],
            coupon=fresh_cart[
                "coupon"
            ],
        )

        for product, quantity in locked_items:

            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                quantity=quantity,
                price=product.discounted_price,
            )

        client = _razorpay_client()

        rp_order = client.order.create(
            {
                "amount": int(
                    order.total_price * 100
                ),
                "currency": "INR",
                "receipt": (
                    f"GOODY-{order.id}"
                ),
                "notes": {
                    "goody_order_id": str(
                        order.id
                    ),
                    "customer_id": str(
                        request.user.id
                    ),
                },
            }
        )

        order.razorpay_order_id = (
            rp_order["id"]
        )

        order.save(
            update_fields=[
                "razorpay_order_id"
            ]
        )

        OrderStatusHistory.objects.create(
            order=order,
            status="pending",
            note="Awaiting online payment.",
        )

    return order, rp_order


@login_required(login_url="login")
@require_POST
def create_razorpay_order(request):

    try:

        data = _checkout_customer_data(
            request
        )

        order, rp_order = (
            _create_pending_razorpay_order(
                request,
                data,
            )
        )

        return JsonResponse(
            {
                "ok": True,
                "order_id": order.id,
                "razorpay_order_id": rp_order[
                    "id"
                ],
                "amount": int(
                    order.total_price * 100
                ),
                "currency": "INR",
                "key": settings.RAZORPAY_KEY_ID,
                "name": "THE GOODY CO.",
                "description": (
                    f"Goody Order #{order.id}"
                ),
                "prefill": {
                    "name": order.full_name,
                    "email": order.email,
                    "contact": order.phone,
                },
            }
        )

    except ValueError as exc:

        return JsonResponse(
            {
                "ok": False,
                "error": str(exc),
            },
            status=400,
        )

    except Exception:

        return JsonResponse(
            {
                "ok": False,
                "error": (
                    "Unable to start online payment. "
                    "Please try again."
                ),
            },
            status=500,
        )


@login_required(login_url="login")
@require_POST
def retry_razorpay_payment(request, id):

    try:

        order = get_object_or_404(
            Order,
            id=id,
            customer=request.user,
        )

        if (
            order.payment_method
            != "razorpay"
            or order.payment_status
            == "paid"
        ):

            return JsonResponse(
                {
                    "ok": False,
                    "error": (
                        "This order is not eligible "
                        "for payment retry."
                    ),
                },
                status=400,
            )

        if order.order_status in {
            "cancelled",
            "delivered",
            "shipped",
        }:

            return JsonResponse(
                {
                    "ok": False,
                    "error": (
                        "This order cannot be paid now."
                    ),
                },
                status=400,
            )

        client = _razorpay_client()

        rp_order = client.order.create(
            {
                "amount": int(
                    order.total_price * 100
                ),
                "currency": "INR",
                "receipt": (
                    f"GOODY-{order.id}-RETRY"
                ),
                "notes": {
                    "goody_order_id": str(
                        order.id
                    )
                },
            }
        )

        order.razorpay_order_id = (
            rp_order["id"]
        )

        order.payment_status = "pending"

        order.save(
            update_fields=[
                "razorpay_order_id",
                "payment_status",
                "updated_at",
            ]
        )

        return JsonResponse(
            {
                "ok": True,
                "order_id": order.id,
                "razorpay_order_id": rp_order[
                    "id"
                ],
                "amount": int(
                    order.total_price * 100
                ),
                "currency": "INR",
                "key": settings.RAZORPAY_KEY_ID,
                "name": "THE GOODY CO.",
                "description": (
                    f"Goody Order #{order.id}"
                ),
                "prefill": {
                    "name": order.full_name,
                    "email": order.email,
                    "contact": order.phone,
                },
            }
        )

    except ValueError as exc:

        return JsonResponse(
            {
                "ok": False,
                "error": str(exc),
            },
            status=400,
        )

    except Exception:

        return JsonResponse(
            {
                "ok": False,
                "error": (
                    "Unable to retry payment right now."
                ),
            },
            status=500,
        )


@login_required(login_url="login")
@require_POST
def verify_razorpay_payment(request):

    try:

        payload = json.loads(
            request.body.decode(
                "utf-8"
            )
        )

        order = get_object_or_404(
            Order,
            id=int(
                payload.get(
                    "order_id"
                )
            ),
            customer=request.user,
        )

        razorpay_order_id = (
            payload.get(
                "razorpay_order_id",
                "",
            )
        )

        payment_id = (
            payload.get(
                "razorpay_payment_id",
                "",
            )
        )

        signature = (
            payload.get(
                "razorpay_signature",
                "",
            )
        )

        if (
            not all(
                [
                    razorpay_order_id,
                    payment_id,
                    signature,
                ]
            )
            or razorpay_order_id
            != order.razorpay_order_id
        ):

            return JsonResponse(
                {
                    "ok": False,
                    "error": (
                        "Invalid payment details."
                    ),
                },
                status=400,
            )

        client = _razorpay_client()

        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": (
                    razorpay_order_id
                ),
                "razorpay_payment_id": (
                    payment_id
                ),
                "razorpay_signature": (
                    signature
                ),
            }
        )

        with transaction.atomic():

            locked_order = (
                Order.objects
                .select_for_update()
                .get(
                    pk=order.pk,
                    customer=request.user,
                )
            )

            if (
                locked_order.payment_status
                == "paid"
            ):

                return JsonResponse(
                    {
                        "ok": True,
                        "redirect": reverse(
                            "order_success",
                            kwargs={
                                "id": (
                                    locked_order.id
                                )
                            },
                        ),
                    }
                )

            items = list(
                locked_order.items
                .select_related("product")
            )

            for item in items:

                product = (
                    Product.objects
                    .select_for_update()
                    .get(
                        pk=item.product_id
                    )
                )

                if (
                    product.status
                    != "active"
                    or product.stock
                    < item.quantity
                ):

                    raise ValueError(
                        f"{product.name} is no longer available in the requested quantity."
                    )

                product.stock -= (
                    item.quantity
                )

                product.save(
                    update_fields=[
                        "stock"
                    ]
                )

            if locked_order.coupon_id:

                coupon = (
                    Coupon.objects
                    .select_for_update()
                    .get(
                        pk=locked_order.coupon_id
                    )
                )

                if (
                    not coupon.is_valid(
                        locked_order.subtotal
                    )
                    or CouponUsage.objects.filter(
                        coupon=coupon,
                        user=request.user,
                    ).exists()
                ):

                    raise ValueError(
                        "The coupon is no longer valid. "
                        "Please contact support before completing payment."
                    )

                coupon.used_count += 1

                coupon.save(
                    update_fields=[
                        "used_count"
                    ]
                )

                CouponUsage.objects.create(
                    coupon=coupon,
                    user=request.user,
                    order=locked_order,
                )

            locked_order.payment_status = (
                "paid"
            )

            locked_order.order_status = (
                "processing"
            )

            locked_order.razorpay_payment_id = (
                payment_id
            )

            locked_order.razorpay_signature = (
                signature
            )

            locked_order.save(
                update_fields=[
                    "payment_status",
                    "order_status",
                    "razorpay_payment_id",
                    "razorpay_signature",
                    "updated_at",
                ]
            )

            OrderStatusHistory.objects.create(
                order=locked_order,
                status="processing",
                note=(
                    "Online payment verified successfully."
                ),
            )

        try:

            emails.send_order_confirmation_email(
                locked_order
            )

        except Exception:

            pass

        _save_cart(
            request,
            {},
        )

        request.session.pop(
            "coupon_code",
            None,
        )

        request.session.modified = True

        return JsonResponse(
            {
                "ok": True,
                "redirect": reverse(
                    "order_success",
                    kwargs={
                        "id": locked_order.id
                    },
                ),
            }
        )

    except ValueError as exc:

        return JsonResponse(
            {
                "ok": False,
                "error": str(exc),
            },
            status=400,
        )

    except Exception:

        return JsonResponse(
            {
                "ok": False,
                "error": (
                    "Payment verification failed. "
                    "Please contact support."
                ),
            },
            status=400,
        )


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """
    Optional Razorpay webhook endpoint.
    Configure this URL in Razorpay dashboard.
    """

    if not settings.RAZORPAY_WEBHOOK_SECRET:

        return JsonResponse(
            {
                "ok": False,
                "error": (
                    "Webhook is not configured."
                ),
            },
            status=503,
        )

    try:

        client = _razorpay_client()

        client.utility.verify_webhook_signature(
            request.body.decode("utf-8"),
            request.headers.get(
                "X-Razorpay-Signature",
                "",
            ),
            settings.RAZORPAY_WEBHOOK_SECRET,
        )

        payload = json.loads(
            request.body.decode(
                "utf-8"
            )
        )

        event = payload.get(
            "event",
            "",
        )

        payment_entity = (
            payload
            .get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )

        rp_order_id = payment_entity.get(
            "order_id"
        )

        if (
            event
            in {
                "payment.captured",
                "order.paid",
            }
            and rp_order_id
        ):

            with transaction.atomic():

                order = (
                    Order.objects
                    .select_for_update()
                    .filter(
                        razorpay_order_id=rp_order_id
                    )
                    .first()
                )

                if (
                    order
                    and order.payment_status
                    != "paid"
                ):

                    order.payment_status = (
                        "paid"
                    )

                    order.razorpay_payment_id = (
                        payment_entity.get(
                            "id",
                            "",
                        )
                    )

                    order.save(
                        update_fields=[
                            "payment_status",
                            "razorpay_payment_id",
                            "updated_at",
                        ]
                    )

        elif (
            event == "payment.failed"
            and rp_order_id
        ):

            Order.objects.filter(
                razorpay_order_id=rp_order_id,
                payment_status="pending",
            ).update(
                payment_status="failed"
            )

        return JsonResponse(
            {
                "ok": True
            }
        )

    except Exception:

        return JsonResponse(
            {
                "ok": False
            },
            status=400,
        )


# =====================================================================
# CANCEL ORDER
# =====================================================================

@login_required(login_url="login")
def cancel_order(request, id):

    if request.method != "POST":

        return redirect(
            "order_detail",
            id=id,
        )

    order = get_object_or_404(
        Order,
        id=id,
        customer=request.user,
    )

    if order.order_status in {
        "shipped",
        "delivered",
        "cancelled",
    }:

        messages.error(
            request,
            "This order can no longer be cancelled.",
        )

        return redirect(
            "order_detail",
            id=id,
        )

    if order.payment_status == "paid":

        messages.info(
            request,
            "Your paid order requires a refund review. Please contact support.",
        )

        return redirect(
            "order_detail",
            id=id,
        )

    with transaction.atomic():

        order.order_status = (
            "cancelled"
        )

        order.save(
            update_fields=[
                "order_status",
                "updated_at",
            ]
        )

        OrderStatusHistory.objects.create(
            order=order,
            status="cancelled",
            note="Cancelled by customer.",
        )

    messages.success(
        request,
        "Your order has been cancelled.",
    )

    return redirect(
        "order_detail",
        id=id,
    )


# =====================================================================
# INVOICE
# =====================================================================

@login_required(login_url="login")
def invoice_pdf(request, id):

    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items"
        ),
        id=id,
        customer=request.user,
    )

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm

    response = HttpResponse(
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="Goody-Invoice-{order.id}.pdf"'
    )

    pdf = canvas.Canvas(
        response,
        pagesize=A4,
    )

    width, height = A4

    y = (
        height
        - 25 * mm
    )

    pdf.setFont(
        "Helvetica-Bold",
        20,
    )

    pdf.drawString(
        20 * mm,
        y,
        "THE GOODY CO.",
    )

    y -= 10 * mm

    pdf.setFont(
        "Helvetica",
        10,
    )

    pdf.drawString(
        20 * mm,
        y,
        f"Invoice / Order #{order.id}",
    )

    pdf.drawRightString(
        width - 20 * mm,
        y,
        order.created_at.strftime(
            "%d %b %Y"
        ),
    )

    y -= 14 * mm

    pdf.setFont(
        "Helvetica-Bold",
        11,
    )

    pdf.drawString(
        20 * mm,
        y,
        "Bill To",
    )

    y -= 6 * mm

    pdf.setFont(
        "Helvetica",
        10,
    )

    for line in [
        order.full_name,
        order.email,
        order.phone,
        order.address,
        (
            f"{order.city}, "
            f"{order.state} - "
            f"{order.pincode}"
        ),
    ]:

        pdf.drawString(
            20 * mm,
            y,
            line[:95],
        )

        y -= 5 * mm

    y -= 5 * mm

    pdf.setFont(
        "Helvetica-Bold",
        10,
    )

    pdf.drawString(
        20 * mm,
        y,
        "Product",
    )

    pdf.drawRightString(
        125 * mm,
        y,
        "Qty",
    )

    pdf.drawRightString(
        width - 20 * mm,
        y,
        "Amount",
    )

    y -= 6 * mm

    pdf.setFont(
        "Helvetica",
        10,
    )

    for item in order.items.all():

        pdf.drawString(
            20 * mm,
            y,
            item.product_name[:55],
        )

        pdf.drawRightString(
            125 * mm,
            y,
            str(item.quantity),
        )

        pdf.drawRightString(
            width - 20 * mm,
            y,
            f"Rs. {item.total:.2f}",
        )

        y -= 6 * mm

        if y < 35 * mm:

            pdf.showPage()

            y = (
                height
                - 25 * mm
            )

            pdf.setFont(
                "Helvetica",
                10,
            )

    y -= 8 * mm

    for label, value in [
        ("Subtotal", order.subtotal),
        ("Shipping", order.shipping_fee),
        ("Discount", order.discount_amount),
        ("Grand Total", order.total_price),
    ]:

        pdf.setFont(
            (
                "Helvetica-Bold"
                if label == "Grand Total"
                else "Helvetica"
            ),
            10,
        )

        pdf.drawRightString(
            150 * mm,
            y,
            label,
        )

        pdf.drawRightString(
            width - 20 * mm,
            y,
            f"Rs. {value:.2f}",
        )

        y -= 6 * mm

    y -= 8 * mm

    pdf.setFont(
        "Helvetica",
        9,
    )

    pdf.drawString(
        20 * mm,
        y,
        (
            f"Payment: "
            f"{order.get_payment_method_display()} "
            f"| Status: "
            f"{order.get_payment_status_display()}"
        ),
    )

    y -= 8 * mm

    pdf.drawString(
        20 * mm,
        y,
        "Thank you for shopping with THE GOODY CO.",
    )

    pdf.save()

    return response


# =====================================================================
# CUSTOMER ACCOUNT / ADDRESSES / ORDERS / REVIEWS
# =====================================================================

@login_required(login_url="login")
def account(request):

    orders = (
        request.user.orders
        .prefetch_related("items")
        .all()[:10]
    )

    addresses = (
        request.user.addresses.all()
    )

    return render(
        request,
        "products/account.html",
        {
            "orders": orders,
            "addresses": addresses,
        },
    )


@login_required(login_url="login")
def add_address(request):

    if request.method != "POST":
        return redirect("account")

    required = [
        "full_name",
        "phone",
        "address_line",
        "city",
        "state",
        "pincode",
    ]

    if not all(
        request.POST.get(
            field,
            "",
        ).strip()
        for field in required
    ):

        messages.error(
            request,
            "Please fill in all address fields.",
        )

        return redirect("account")

    address = Address.objects.create(
        user=request.user,
        label=(
            request.POST.get(
                "label",
                "Home",
            )
            .strip()
            or "Home"
        ),
        full_name=request.POST[
            "full_name"
        ].strip(),
        phone=request.POST[
            "phone"
        ].strip(),
        address_line=request.POST[
            "address_line"
        ].strip(),
        city=request.POST[
            "city"
        ].strip(),
        state=request.POST[
            "state"
        ].strip(),
        pincode=request.POST[
            "pincode"
        ].strip(),
        is_default=(
            request.POST.get(
                "is_default"
            )
            == "on"
        ),
    )

    messages.success(
        request,
        f"{address.label} address saved.",
    )

    return redirect("account")


@login_required(login_url="login")
def delete_address(request, id):

    if request.method == "POST":

        Address.objects.filter(
            id=id,
            user=request.user,
        ).delete()

        messages.success(
            request,
            "Address removed.",
        )

    return redirect("account")


@login_required(login_url="login")
def order_history(request):

    orders = (
        request.user.orders
        .prefetch_related(
            "items",
            "status_history",
        )
        .all()
    )

    return render(
        request,
        "products/orders.html",
        {
            "orders": orders
        },
    )


@login_required(login_url="login")
def order_detail(request, id):

    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items",
            "status_history",
        ),
        id=id,
        customer=request.user,
    )

    return render(
        request,
        "products/order_detail.html",
        {
            "order": order
        },
    )


@login_required(login_url="login")
def add_review(request, id):

    product = get_object_or_404(
        Product,
        id=id,
        status="active",
    )

    if request.method != "POST":

        return redirect(
            "product_detail",
            id=id,
        )

    try:

        rating = int(
            request.POST.get(
                "rating",
                "0",
            )
        )

    except (ValueError, TypeError):

        rating = 0

    comment = request.POST.get(
        "comment",
        "",
    ).strip()

    if rating not in range(1, 6):

        messages.error(
            request,
            "Please choose a rating from 1 to 5.",
        )

        return redirect(
            "product_detail",
            id=id,
        )

    if not OrderItem.objects.filter(
        order__customer=request.user,
        product=product,
        order__order_status="delivered",
    ).exists():

        messages.error(
            request,
            "You can review a product after it has been delivered to you.",
        )

        return redirect(
            "product_detail",
            id=id,
        )

    review, created = (
        Review.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={
                "rating": rating,
                "comment": comment,
                "approved": True,
            },
        )
    )

    messages.success(
        request,
        (
            "Your review has been submitted."
            if created
            else "Your review has been updated."
        ),
    )

    return redirect(
        "product_detail",
        id=id,
    )


# =====================================================================
# NEWSLETTER
# =====================================================================

def newsletter_subscribe(request):

    if request.method != "POST":
        return redirect("home")

    email = request.POST.get(
        "email",
        "",
    ).strip().lower()

    if not email:

        messages.error(
            request,
            "Please enter your email address.",
        )

        return redirect(
            request.META.get(
                "HTTP_REFERER"
            )
            or reverse("home")
        )

    if (
        "@"
        not in email
        or "."
        not in email.split("@")[-1]
    ):

        messages.error(
            request,
            "Please enter a valid email address.",
        )

        return redirect(
            request.META.get(
                "HTTP_REFERER"
            )
            or reverse("home")
        )

    if NewsletterSubscriber.objects.filter(
        email=email
    ).exists():

        messages.info(
            request,
            "You are already subscribed.",
        )

        return redirect(
            request.META.get(
                "HTTP_REFERER"
            )
            or reverse("home")
        )

    NewsletterSubscriber.objects.create(
        email=email
    )

    messages.success(
        request,
        "Thank you for subscribing to Goody!",
    )

    return redirect(
        request.META.get(
            "HTTP_REFERER"
        )
        or reverse("home")
    )


# =====================================================================
# AUTHENTICATION
# =====================================================================

User = get_user_model()

def login(request):

    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":

        login_method = request.POST.get(
            "login_method",
            "password",
        )

        # ============================================================
        # USERNAME + PASSWORD LOGIN
        # ============================================================

        if login_method == "password":

            username = request.POST.get(
                "username",
                "",
            ).strip()

            password = request.POST.get(
                "password",
                "",
            )

            if not username or not password:

                messages.error(
                    request,
                    "Please enter your username and password.",
                )

                return redirect("login")

            user = authenticate(
                request,
                username=username,
                password=password,
            )

            if user is not None:

                if not user.is_active:

                    messages.error(
                        request,
                        "Your account is inactive. Please contact support.",
                    )

                    return redirect("login")

                auth_login(
                    request,
                    user,
                )

                messages.success(
                    request,
                    f"Welcome back, {user.first_name or user.username}!",
                )

                next_url = request.POST.get(
                    "next"
                )

                if next_url:
                    return redirect(next_url)

                return redirect("home")

            messages.error(
                request,
                "Invalid username or password.",
            )

            return redirect("login")

        # ============================================================
        # EMAIL OTP LOGIN
        # ============================================================

        elif login_method == "otp":

            email = request.POST.get(
                "email",
                "",
            ).strip().lower()

            if not email:

                messages.error(
                    request,
                    "Please enter your email address.",
                )

                return redirect("login")

            try:

                user = User.objects.get(
                    email__iexact=email
                )

            except User.DoesNotExist:

                messages.error(
                    request,
                    "No account is registered with this email address.",
                )

                return redirect("login")

            if not user.is_active:

                messages.error(
                    request,
                    "Your account is inactive. Please contact support.",
                )

                return redirect("login")

            # Generate OTP
            otp = generate_otp()

            request.session[
                "login_otp"
            ] = otp

            request.session[
                "login_otp_email"
            ] = email

            request.session[
                "login_otp_user_id"
            ] = user.pk

            expiry_time = (
                timezone.now()
                + timedelta(minutes=5)
            )

            request.session[
                "login_otp_expiry"
            ] = expiry_time.isoformat()

            request.session[
                "login_otp_attempts"
            ] = 0

            request.session.modified = True

            try:

                _send_app_email(
                    subject=(
                        "Your THE GOODY CO. "
                        "Login Verification Code"
                    ),
                    message=f"""
Hello {user.first_name or user.username},

You requested to log in to THE GOODY CO.

Your login verification OTP is:

{otp}

This OTP is valid for 5 minutes.

If you did not request this login, please ignore this email.

THE GOODY CO.
Premium Handmade Chocolates
""",
                    recipient=email,
                )

            except Exception:

                clear_login_otp_session(
                    request
                )

                messages.error(
                    request,
                    (
                        "Unable to send OTP. "
                        "Please check the email configuration "
                        "and try again later."
                    ),
                )

                return redirect("login")

            messages.success(
                request,
                f"OTP sent successfully to {email}.",
            )

            return redirect(
                "login_otp"
            )

    return render(
        request,
        "products/login.html",
    )


# =====================================================================
# EMAIL OTP VERIFICATION
# =====================================================================

def login_otp(request):

    if request.user.is_authenticated:
        return redirect("home")

    email = request.session.get(
        "login_otp_email"
    )

    if not email:

        messages.error(
            request,
            "Your OTP session has expired. Please request a new OTP.",
        )

        return redirect("login")

    if request.method == "POST":

        entered_otp = request.POST.get(
            "otp",
            "",
        ).strip()

        stored_otp = request.session.get(
            "login_otp"
        )

        expiry_string = request.session.get(
            "login_otp_expiry"
        )

        user_id = request.session.get(
            "login_otp_user_id"
        )

        if (
            not stored_otp
            or not expiry_string
            or not user_id
        ):

            messages.error(
                request,
                "OTP session expired. Please request a new OTP.",
            )

            return redirect("login")

        attempts = request.session.get(
            "login_otp_attempts",
            0,
        )

        if attempts >= 5:

            clear_login_otp_session(
                request
            )

            messages.error(
                request,
                "Too many incorrect OTP attempts. Please request a new OTP.",
            )

            return redirect("login")

        try:

            expiry_time = (
                timezone.datetime.fromisoformat(
                    expiry_string
                )
            )

            if timezone.is_naive(
                expiry_time
            ):

                expiry_time = (
                    timezone.make_aware(
                        expiry_time
                    )
                )

        except (
            ValueError,
            TypeError,
        ):

            clear_login_otp_session(
                request
            )

            messages.error(
                request,
                "Invalid OTP session. Please request a new OTP.",
            )

            return redirect("login")

        if timezone.now() > expiry_time:

            clear_login_otp_session(
                request
            )

            messages.error(
                request,
                "Your OTP has expired. Please request a new OTP.",
            )

            return redirect("login")

        if (
            not entered_otp.isdigit()
            or len(entered_otp) != 6
        ):

            request.session[
                "login_otp_attempts"
            ] = attempts + 1

            messages.error(
                request,
                "Please enter the 6-digit OTP.",
            )

            return redirect(
                "login_otp"
            )

        if entered_otp != stored_otp:

            request.session[
                "login_otp_attempts"
            ] = attempts + 1

            remaining = 4 - attempts

            if remaining > 0:

                messages.error(
                    request,
                    f"Incorrect OTP. {remaining} attempts remaining.",
                )

            else:

                clear_login_otp_session(
                    request
                )

                messages.error(
                    request,
                    "Too many incorrect OTP attempts. Please request a new OTP.",
                )

                return redirect("login")

            return redirect(
                "login_otp"
            )

        try:

            user = User.objects.get(
                pk=user_id
            )

        except User.DoesNotExist:

            clear_login_otp_session(
                request
            )

            messages.error(
                request,
                "User account could not be found.",
            )

            return redirect("login")

        if not user.is_active:

            clear_login_otp_session(
                request
            )

            messages.error(
                request,
                "Your account is inactive.",
            )

            return redirect("login")

        auth_login(
            request,
            user,
        )

        clear_login_otp_session(
            request
        )

        messages.success(
            request,
            f"Welcome back, {user.first_name or user.username}!",
        )

        next_url = request.POST.get(
            "next"
        )

        if next_url:
            return redirect(next_url)

        return redirect("home")

    return render(
        request,
        "products/login_otp.html",
        {
            "email": email,
        },
    )


# =====================================================================
# RESEND LOGIN OTP
# =====================================================================

def resend_login_otp(request):

    if request.user.is_authenticated:
        return redirect("home")

    email = request.session.get(
        "login_otp_email"
    )

    if not email:

        messages.error(
            request,
            "Please enter your email address first.",
        )

        return redirect("login")

    try:

        user = User.objects.get(
            email__iexact=email
        )

    except User.DoesNotExist:

        clear_login_otp_session(
            request
        )

        messages.error(
            request,
            "Account not found.",
        )

        return redirect("login")

    if not user.is_active:

        clear_login_otp_session(
            request
        )

        messages.error(
            request,
            "Your account is inactive.",
        )

        return redirect("login")

    otp = generate_otp()

    request.session[
        "login_otp"
    ] = otp

    request.session[
        "login_otp_email"
    ] = email

    request.session[
        "login_otp_user_id"
    ] = user.pk

    expiry_time = (
        timezone.now()
        + timedelta(minutes=5)
    )

    request.session[
        "login_otp_expiry"
    ] = expiry_time.isoformat()

    request.session[
        "login_otp_attempts"
    ] = 0

    request.session.modified = True

    try:

        _send_app_email(
            subject=(
                "Your New THE GOODY CO. "
                "Login OTP"
            ),
            message=f"""
Hello {user.first_name or user.username},

Here is your new THE GOODY CO. login OTP:

{otp}

This OTP is valid for 5 minutes.

If you did not request this OTP, please ignore this email.

THE GOODY CO.
Premium Handmade Chocolates
""",
            recipient=email,
        )

    except Exception:

        clear_login_otp_session(
            request
        )

        messages.error(
            request,
            "Unable to send OTP. Please check the email configuration and try again.",
        )

        return redirect(
            "login"
        )

    messages.success(
        request,
        "A new OTP has been sent to your email.",
    )

    return redirect(
        "login_otp"
    )


# =====================================================================
# CLEAR LOGIN OTP SESSION
# =====================================================================

def clear_login_otp_session(request):

    keys = [
        "login_otp",
        "login_otp_email",
        "login_otp_user_id",
        "login_otp_expiry",
        "login_otp_attempts",
    ]

    for key in keys:

        request.session.pop(
            key,
            None,
        )

    request.session.modified = True


# =====================================================================
# LOGOUT
# =====================================================================

def user_logout(request):

    auth_logout(
        request
    )

    messages.success(
        request,
        "You have been logged out.",
    )

    return redirect("home")


# =====================================================================
# REGISTER
# =====================================================================

def register(request):

    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":

        first_name = request.POST.get(
            "first_name",
            "",
        ).strip()

        last_name = request.POST.get(
            "last_name",
            "",
        ).strip()

        username = request.POST.get(
            "username",
            "",
        ).strip()

        email = request.POST.get(
            "email",
            "",
        ).strip().lower()

        password1 = request.POST.get(
            "password1",
            "",
        )

        password2 = request.POST.get(
            "password2",
            "",
        )

        # ============================================================
        # REQUIRED FIELDS
        # ============================================================

        if not all(
            [
                first_name,
                last_name,
                username,
                email,
                password1,
                password2,
            ]
        ):

            messages.error(
                request,
                "Please fill in all required fields.",
            )

            return redirect(
                "register"
            )

        # ============================================================
        # BASIC EMAIL VALIDATION
        # ============================================================

        if (
            "@"
            not in email
            or "."
            not in email.split("@")[-1]
        ):

            messages.error(
                request,
                "Please enter a valid email address.",
            )

            return redirect(
                "register"
            )

        # ============================================================
        # PASSWORD MATCH
        # ============================================================

        if password1 != password2:

            messages.error(
                request,
                "Passwords do not match.",
            )

            return redirect(
                "register"
            )

        # ============================================================
        # PASSWORD LENGTH
        # ============================================================

        if len(password1) < 8:

            messages.error(
                request,
                "Password must contain at least 8 characters.",
            )

            return redirect(
                "register"
            )

        # ============================================================
        # USERNAME CHECK
        # ============================================================

        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                "Username already exists.",
            )

            return redirect(
                "register"
            )

        # ============================================================
        # EMAIL CHECK
        # ============================================================

        if User.objects.filter(
            email__iexact=email
        ).exists():

            messages.error(
                request,
                "Email already registered. Please login instead.",
            )

            return redirect(
                "login"
            )

        # ============================================================
        # CHECK EMAIL CONFIGURATION BEFORE CREATING OTP
        # ============================================================

        try:

            sender = _get_email_sender()

        except ValueError:

            messages.error(
                request,
                (
                    "Email service is not configured. "
                    "Please configure EMAIL_HOST_USER, "
                    "EMAIL_HOST_PASSWORD and DEFAULT_FROM_EMAIL "
                    "in your .env file."
                ),
            )

            return redirect(
                "register"
            )

        # ============================================================
        # GENERATE OTP
        # ============================================================

        otp = generate_otp()

        # Remove previous registration OTP
        EmailOTP.objects.filter(
            email=email
        ).delete()

        # Save new OTP
        EmailOTP.objects.create(
            email=email,
            otp=otp,
        )

        # ============================================================
        # STORE REGISTRATION DATA SAFELY
        # ============================================================
        #
        # IMPORTANT:
        # Never store the plain password in the session.
        #
        # We hash the password before putting it into the session.
        #
        # The password is NEVER sent by email.
        #

        password_hash = make_password(
            password1
        )

        request.session[
            "registration_data"
        ] = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "first_name": first_name,
            "last_name": last_name,
        }

        request.session.modified = True

        # ============================================================
        # SEND REGISTRATION OTP
        # ============================================================

        try:

            send_mail(
                subject=(
                    "Your THE GOODY CO. "
                    "Verification Code"
                ),
                message=f"""
Hello {first_name} {last_name},

Thank you for registering with THE GOODY CO.

Your username is:
{username}

Your email is:
{email}

Your email verification OTP is:

{otp}

This OTP is valid for 5 minutes.

For your security, your password is not included in this email.

If you did not request this registration, please ignore this email.

THE GOODY CO.
Premium Handmade Chocolates
""",
                from_email=sender,
                recipient_list=[email],
                fail_silently=False,
            )

        except Exception:

            # Delete OTP if email failed
            EmailOTP.objects.filter(
                email=email
            ).delete()

            # Delete registration session
            request.session.pop(
                "registration_data",
                None,
            )

            request.session.modified = True

            messages.error(
                request,
                (
                    "Unable to send verification OTP. "
                    "Please check your email configuration "
                    "and try again."
                ),
            )

            return redirect(
                "register"
            )

        messages.success(
            request,
            "OTP sent successfully to your email.",
        )

        return redirect(
            "verify_otp"
        )

    return render(
        request,
        "products/register.html",
    )


# =====================================================================
# GENERATE OTP
# =====================================================================

def generate_otp():

    return str(
        random.randint(
            100000,
            999999,
        )
    )


# =====================================================================
# VERIFY REGISTRATION OTP
# =====================================================================

def verify_registration_otp(request):

    registration_data = request.session.get(
        "registration_data"
    )

    if not registration_data:

        messages.error(
            request,
            "Registration session expired. Please register again.",
        )

        return redirect(
            "register"
        )

    email = registration_data.get(
        "email"
    )

    if not email:

        request.session.pop(
            "registration_data",
            None,
        )

        messages.error(
            request,
            "Invalid registration session. Please register again.",
        )

        return redirect(
            "register"
        )

    if request.method == "POST":

        entered_otp = request.POST.get(
            "otp",
            "",
        ).strip()

        # ============================================================
        # FIND OTP
        # ============================================================

        try:

            otp_record = EmailOTP.objects.get(
                email=email
            )

        except EmailOTP.DoesNotExist:

            messages.error(
                request,
                "OTP not found. Please register again.",
            )

            return redirect(
                "register"
            )

        # ============================================================
        # CHECK EXPIRATION
        # ============================================================

        try:

            expired = otp_record.is_expired()

        except Exception:

            expired = False

        if expired:

            otp_record.delete()

            request.session.pop(
                "registration_data",
                None,
            )

            request.session.modified = True

            messages.error(
                request,
                "OTP has expired. Please register again.",
            )

            return redirect(
                "register"
            )

        # ============================================================
        # CHECK OTP
        # ============================================================

        if (
            not entered_otp.isdigit()
            or len(entered_otp) != 6
        ):

            messages.error(
                request,
                "Please enter the 6-digit OTP.",
            )

            return render(
                request,
                "products/verify_otp.html",
                {
                    "email": email
                },
            )

        if entered_otp != otp_record.otp:

            messages.error(
                request,
                "Invalid OTP. Please try again.",
            )

            return render(
                request,
                "products/verify_otp.html",
                {
                    "email": email
                },
            )

        # ============================================================
        # DOUBLE-CHECK ACCOUNT BEFORE CREATE
        # ============================================================

        if User.objects.filter(
            username=registration_data[
                "username"
            ]
        ).exists():

            otp_record.delete()

            request.session.pop(
                "registration_data",
                None,
            )

            messages.error(
                request,
                "Username already exists. Please register again.",
            )

            return redirect(
                "register"
            )

        if User.objects.filter(
            email__iexact=registration_data[
                "email"
            ]
        ).exists():

            otp_record.delete()

            request.session.pop(
                "registration_data",
                None,
            )

            messages.error(
                request,
                "Email already registered. Please login instead.",
            )

            return redirect(
                "login"
            )

        # ============================================================
        # CREATE USER
        # ============================================================

        try:

            with transaction.atomic():

                # Mark OTP verified
                otp_record.is_verified = True

                otp_record.save(
                    update_fields=[
                        "is_verified"
                    ]
                )

                # Create user with hashed password
                user = User(
                    username=registration_data[
                        "username"
                    ],
                    email=registration_data[
                        "email"
                    ],
                    first_name=registration_data.get(
                        "first_name",
                        "",
                    ),
                    last_name=registration_data.get(
                        "last_name",
                        "",
                    ),
                    password=registration_data[
                        "password_hash"
                    ],
                )

                user.save()

                # Delete OTP
                otp_record.delete()

        except Exception:

            messages.error(
                request,
                (
                    "Unable to create your account. "
                    "Please try registering again."
                ),
            )

            return redirect(
                "register"
            )

        # ============================================================
        # CLEAR REGISTRATION SESSION
        # ============================================================

        request.session.pop(
            "registration_data",
            None,
        )

        request.session.modified = True

        # ============================================================
        # SUCCESS
        # ============================================================

        messages.success(
            request,
            (
                "Email verified successfully! "
                "Your account has been created. "
                "You can now login."
            ),
        )

        return redirect(
            "login"
        )

    return render(
        request,
        "products/verify_otp.html",
        {
            "email": email
        },
    )


# =====================================================================
# COMPATIBILITY ALIAS
# =====================================================================
#
# Your existing urls.py may use:
#
#     path("verify-otp/", views.verify_otp, ...)
#
# while the function is named verify_registration_otp.
#
# This alias prevents that mismatch.
#

verify_otp = verify_registration_otp


# =====================================================================
# FORGOT PASSWORD - SEND OTP
# =====================================================================

def forgot_password(request):

    if request.method == "POST":

        email = request.POST.get(
            "email",
            "",
        ).strip().lower()

        User = get_user_model()

        if not email:

            messages.error(
                request,
                "Please enter your email address.",
            )

            return redirect(
                "forgot_password"
            )

        if (
            "@"
            not in email
            or "."
            not in email.split("@")[-1]
        ):

            messages.error(
                request,
                "Please enter a valid email address.",
            )

            return redirect(
                "forgot_password"
            )

        try:

            user = User.objects.get(
                email__iexact=email
            )

        except User.DoesNotExist:

            messages.error(
                request,
                "No account exists with this email address.",
            )

            return redirect(
                "forgot_password"
            )

        otp = generate_otp()

        request.session[
            "forgot_password_email"
        ] = email

        request.session[
            "forgot_password_otp"
        ] = otp

        request.session[
            "forgot_password_otp_created"
        ] = time.time()

        request.session[
            "forgot_password_verified"
        ] = False

        request.session.modified = True

        subject = (
            "Password Reset OTP | "
            "THE GOODY CO."
        )

        message = f"""
Hello {user.first_name or user.username},

We received a request to reset your password for THE GOODY CO.

Your password reset OTP is:

{otp}

This OTP is valid for 10 minutes.

If you did not request a password reset, please ignore this email.

Regards,
THE GOODY CO.
"""

        try:

            _send_app_email(
                subject=subject,
                message=message,
                recipient=email,
            )

        except Exception:

            request.session.pop(
                "forgot_password_email",
                None,
            )

            request.session.pop(
                "forgot_password_otp",
                None,
            )

            request.session.pop(
                "forgot_password_otp_created",
                None,
            )

            request.session.pop(
                "forgot_password_verified",
                None,
            )

            request.session.modified = True

            messages.error(
                request,
                (
                    "Unable to send OTP. "
                    "Please check the email configuration "
                    "and try again."
                ),
            )

            return redirect(
                "forgot_password"
            )

        messages.success(
            request,
            f"OTP sent successfully to {email}.",
        )

        return redirect(
            "forgot_password_otp"
        )

    return render(
        request,
        "products/forgot_password.html",
    )


# =====================================================================
# FORGOT PASSWORD - VERIFY OTP
# =====================================================================

def forgot_password_otp(request):

    email = request.session.get(
        "forgot_password_email"
    )

    if not email:

        messages.error(
            request,
            "Please request a password reset first.",
        )

        return redirect(
            "forgot_password"
        )

    if request.method == "POST":

        entered_otp = request.POST.get(
            "otp",
            "",
        ).strip()

        saved_otp = request.session.get(
            "forgot_password_otp"
        )

        if not saved_otp:

            messages.error(
                request,
                "OTP expired. Please request a new OTP.",
            )

            return redirect(
                "forgot_password"
            )

        created_time = request.session.get(
            "forgot_password_otp_created"
        )

        if created_time:

            try:

                if (
                    time.time()
                    - float(created_time)
                    > 600
                ):

                    request.session.pop(
                        "forgot_password_otp",
                        None,
                    )

                    request.session.pop(
                        "forgot_password_otp_created",
                        None,
                    )

                    request.session.pop(
                        "forgot_password_verified",
                        None,
                    )

                    request.session.modified = True

                    messages.error(
                        request,
                        "OTP has expired. Please request a new OTP.",
                    )

                    return redirect(
                        "forgot_password"
                    )

            except (
                ValueError,
                TypeError,
            ):

                messages.error(
                    request,
                    "Invalid OTP session. Please request a new OTP.",
                )

                return redirect(
                    "forgot_password"
                )

        if (
            not entered_otp.isdigit()
            or len(entered_otp) != 6
        ):

            messages.error(
                request,
                "Please enter the 6-digit OTP.",
            )

            return redirect(
                "forgot_password_otp"
            )

        if entered_otp == saved_otp:

            request.session[
                "forgot_password_verified"
            ] = True

            request.session.pop(
                "forgot_password_otp",
                None,
            )

            request.session.pop(
                "forgot_password_otp_created",
                None,
            )

            request.session.modified = True

            messages.success(
                request,
                "OTP verified successfully.",
            )

            return redirect(
                "reset_password"
            )

        messages.error(
            request,
            "Invalid OTP. Please try again.",
        )

        return redirect(
            "forgot_password_otp"
        )

    return render(
        request,
        "products/forgot_password_otp.html",
        {
            "email": email
        },
    )


# =====================================================================
# RESEND FORGOT PASSWORD OTP
# =====================================================================

def resend_forgot_password_otp(request):

    if request.method != "POST":

        return redirect(
            "forgot_password"
        )

    email = request.session.get(
        "forgot_password_email"
    )

    if not email:

        messages.error(
            request,
            "Please enter your email first.",
        )

        return redirect(
            "forgot_password"
        )

    User = get_user_model()

    try:

        user = User.objects.get(
            email__iexact=email
        )

    except User.DoesNotExist:

        messages.error(
            request,
            "Account not found.",
        )

        return redirect(
            "forgot_password"
        )

    otp = generate_otp()

    request.session[
        "forgot_password_otp"
    ] = otp

    request.session[
        "forgot_password_otp_created"
    ] = time.time()

    request.session[
        "forgot_password_verified"
    ] = False

    request.session.modified = True

    subject = (
        "New Password Reset OTP | "
        "THE GOODY CO."
    )

    message = f"""
Hello {user.first_name or user.username},

Your new password reset OTP for THE GOODY CO. is:

{otp}

This OTP is valid for 10 minutes.

If you did not request this OTP, please ignore this email.

Regards,
THE GOODY CO.
"""

    try:

        _send_app_email(
            subject=subject,
            message=message,
            recipient=email,
        )

        messages.success(
            request,
            "A new OTP has been sent to your email.",
        )

    except Exception:

        messages.error(
            request,
            (
                "Unable to send OTP. "
                "Please check the email configuration "
                "and try again."
            ),
        )

    return redirect(
        "forgot_password_otp"
    )


# =====================================================================
# RESET PASSWORD
# =====================================================================

def reset_password(request):

    email = request.session.get(
        "forgot_password_email"
    )

    verified = request.session.get(
        "forgot_password_verified"
    )

    if not email or not verified:

        messages.error(
            request,
            "Please verify your OTP first.",
        )

        return redirect(
            "forgot_password"
        )

    if request.method == "POST":

        password = request.POST.get(
            "password",
            "",
        )

        confirm_password = request.POST.get(
            "confirm_password",
            "",
        )

        if not password or not confirm_password:

            messages.error(
                request,
                "Please fill in both password fields.",
            )

            return redirect(
                "reset_password"
            )

        if password != confirm_password:

            messages.error(
                request,
                "Passwords do not match.",
            )

            return redirect(
                "reset_password"
            )

        if len(password) < 8:

            messages.error(
                request,
                "Password must contain at least 8 characters.",
            )

            return redirect(
                "reset_password"
            )

        User = get_user_model()

        try:

            user = User.objects.get(
                email__iexact=email
            )

        except User.DoesNotExist:

            messages.error(
                request,
                "Account not found.",
            )

            return redirect(
                "forgot_password"
            )

        # Django automatically hashes the password.
        user.set_password(
            password
        )

        user.save()

        # ============================================================
        # CLEAR PASSWORD RESET SESSION
        # ============================================================

        request.session.pop(
            "forgot_password_email",
            None,
        )

        request.session.pop(
            "forgot_password_verified",
            None,
        )

        request.session.pop(
            "forgot_password_otp",

            None
        )
           

        request.session.modified = True

        messages.success(
            request,
            "Password reset successfully. You can now login.",
        )

        return redirect(
            "login"
        )

    return render(
        request,
        "products/reset_password.html",
        {
            "email": email
        },
    )