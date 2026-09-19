from .views import cart_item_count
from .models import Wishlist, Category


def cart_context(request):
    """Makes {{ cart_count }} and {{ wishlist_count }} available in every template."""
    wishlist_count = 0
    if request.user.is_authenticated:
        wishlist_count = Wishlist.objects.filter(user=request.user).count()

    return {
        "cart_count": cart_item_count(request),
        "wishlist_count": wishlist_count,
        "nav_categories": Category.objects.all()[:8],
    }
