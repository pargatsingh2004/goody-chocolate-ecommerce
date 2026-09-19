from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('', views.dashboard, name='admin_dashboard'),

    # Products
    path('products/', views.product_list, name='admin_products'),
    path('products/add/', views.product_add, name='admin_product_add'),
    path('products/<int:pk>/', views.product_view, name='admin_product_view'),
    path('products/<int:pk>/edit/', views.product_edit, name='admin_product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='admin_product_delete'),

    # Categories
    path('categories/', views.category_list, name='admin_categories'),
    path('categories/add/', views.category_add, name='admin_category_add'),
    path('categories/<int:pk>/edit/', views.category_edit, name='admin_category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='admin_category_delete'),

    # Orders
    path('orders/', views.order_list, name='admin_orders'),
    path('orders/<int:pk>/', views.order_detail, name='admin_order_detail'),

    # Customers
    path('customers/', views.customer_list, name='admin_customers'),
    path('customers/<int:pk>/', views.customer_detail, name='admin_customer_detail'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='admin_customer_delete'),

    # Contacts
    path('contacts/', views.contact_list, name='admin_contacts'),
    path('contacts/<int:pk>/', views.contact_detail, name='admin_contact_detail'),
    path('contacts/<int:pk>/mark-read/', views.contact_mark_read, name='admin_contact_mark_read'),
    path('contacts/<int:pk>/delete/', views.contact_delete, name='admin_contact_delete'),

    # Newsletter
    path('newsletter/', views.newsletter, name='admin_newsletter'),

    # Settings
    path('settings/', views.admin_settings, name='admin_settings'),
    # Business management
    path('analytics/', views.analytics, name='admin_analytics'),
    path('inventory/', views.inventory, name='admin_inventory'),
    path('inventory/<int:pk>/update/', views.inventory_update, name='admin_inventory_update'),
    path('coupons/', views.coupon_list, name='admin_coupons'),
    path('coupons/add/', views.coupon_create, name='admin_coupon_add'),
    path('coupons/<int:pk>/edit/', views.coupon_edit, name='admin_coupon_edit'),
    path('coupons/<int:pk>/toggle/', views.coupon_toggle, name='admin_coupon_toggle'),
    path('coupons/<int:pk>/delete/', views.coupon_delete, name='admin_coupon_delete'),
    path('reviews/', views.review_list, name='admin_reviews'),
    path('reviews/<int:pk>/toggle/', views.review_toggle, name='admin_review_toggle'),
    path('reviews/<int:pk>/delete/', views.review_delete, name='admin_review_delete'),
    path('payments/', views.payment_overview, name='admin_payments'),
    path('orders/export/', views.export_orders_csv, name='admin_export_orders'),

]
