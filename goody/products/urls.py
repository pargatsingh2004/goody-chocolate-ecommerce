
from django.urls import path
from django.contrib.auth import views as auth_views

from . import views


urlpatterns = [

    # ================================================================
    # HOME
    # ================================================================

    path(
        "",
        views.home,
        name="home"
    ),

    # ================================================================
    # NEWSLETTER
    # ================================================================

    path(
        "newsletter/subscribe/",
        views.newsletter_subscribe,
        name="newsletter_subscribe"
    ),


    # ================================================================
    # SHOP
    # ================================================================

    path(
        "shop/",
        views.shop,
        name="shop"
    ),

    path(
        "search/",
        views.search,
        name="search"
    ),

    path(
        "product/<int:id>/",
        views.product_detail,
        name="product_detail"
    ),

    # ================================================================
    # INFORMATION PAGES
    # ================================================================

    path(
        "about/",
        views.about,
        name="about"
    ),

    path(
        "contact/",
        views.contact,
        name="contact"
    ),

    # ================================================================
    # CART
    # ================================================================

    path(
        "cart/",
        views.cart,
        name="cart"
    ),

    path(
        "cart/add/<int:id>/",
        views.add_to_cart,
        name="add_to_cart"
    ),

    path(
        "cart/update/<int:id>/",
        views.update_cart_item,
        name="update_cart_item"
    ),

    path(
        "cart/remove/<int:id>/",
        views.remove_from_cart,
        name="remove_from_cart"
    ),

    path("cart/coupon/apply/", views.apply_coupon, name="apply_coupon"),
    path("cart/coupon/remove/", views.remove_coupon, name="remove_coupon"),

    # ================================================================
    # WISHLIST
    # ================================================================

    path("account/", views.account, name="account"),
    path("account/address/add/", views.add_address, name="add_address"),
    path("account/address/delete/<int:id>/", views.delete_address, name="delete_address"),
    path("orders/", views.order_history, name="order_history"),
    path("orders/<int:id>/", views.order_detail, name="order_detail"),
    path("product/<int:id>/review/", views.add_review, name="add_review"),

    path(
        "wishlist/",
        views.wishlist,
        name="wishlist"
    ),

    path(
        "wishlist/add/<int:id>/",
        views.add_to_wishlist,
        name="add_to_wishlist"
    ),

    path(
        "wishlist/remove/<int:id>/",
        views.remove_from_wishlist,
        name="remove_from_wishlist"
    ),

    # ================================================================
    # CHECKOUT
    # ================================================================

    path("checkout/", views.checkout, name="checkout"),
    path("checkout/razorpay/create/", views.create_razorpay_order, name="create_razorpay_order"),
    path("checkout/razorpay/verify/", views.verify_razorpay_payment, name="verify_razorpay_payment"),
    path("orders/<int:id>/payment/retry/", views.retry_razorpay_payment, name="retry_razorpay_payment"),
    path("payments/razorpay/webhook/", views.razorpay_webhook, name="razorpay_webhook"),
    path("orders/<int:id>/cancel/", views.cancel_order, name="cancel_order"),
    path("orders/<int:id>/invoice/", views.invoice_pdf, name="invoice_pdf"),

    # ================================================================
    # AUTHENTICATION
    # ================================================================

    path("login/",views.login,name="login"),
    path("login/otp/", views.login_otp, name="login_otp"),
    path("login/otp/resend/", views.resend_login_otp, name="resend_login_otp"),

    path(
        "logout/",
        views.user_logout,
        name="logout"
    ),

    path(
        "register/",
        views.register,
        name="register"
    ),

        path(
        "forgot-password/",
        views.forgot_password,
        name="forgot_password"
    ),

    path(
        "forgot-password/otp/",
        views.forgot_password_otp,
        name="forgot_password_otp"
    ),

    path(
        "forgot-password/resend-otp/",
        views.resend_forgot_password_otp,
        name="resend_forgot_password_otp"
    ),

    path(
        "reset-password/",
        views.reset_password,
        name="reset_password"
    ),


   path(
    "verify-registration-otp/",
    views.verify_registration_otp,
    name="verify_registration_otp",
),

]