from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django's built-in admin stays available (superuser fallback / data
    # inspection) but is moved off the obvious /admin/ path since the
    # project now ships its own custom admin panel at /control-panel/.
    path('django-admin/', admin.site.urls),

    # Custom admin panel (not Django Admin) — dashboard, product/order/
    # customer/contact/newsletter management, its own login/logout.
    path('control-panel/', include('admin_panel.urls')),

    path('', include('products.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
