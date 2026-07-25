from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def staff_required(view_func):
    """
    Protects every admin-panel route. Only logged-in users with
    is_staff=True (set via Django's createsuperuser or the 'Staff status'
    checkbox on a User) may access the custom admin panel.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to access the admin panel.")
            return redirect('admin_login')
        if not request.user.is_staff:
            messages.error(request, "You do not have permission to access the admin panel.")
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return _wrapped
