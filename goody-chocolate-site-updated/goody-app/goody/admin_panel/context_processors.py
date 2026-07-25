from products.models import Order, Contact, Product


def admin_notifications(request):
    """Badge counters shown in the admin topbar icons. Cheap counts only."""
    if not request.path.startswith('/control-panel/') or not request.user.is_authenticated:
        return {}
    return {
        "notif_new_orders": Order.objects.filter(order_status='pending').exists(),
        "notif_new_messages": Contact.objects.filter(status='new').exists(),
        "notif_low_stock": Product.objects.filter(stock__lte=Product.LOW_STOCK_THRESHOLD).exists(),
    }
