from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Customer, Order, OrderStatusHistory


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_customer_profile(sender, instance, created, **kwargs):
    """Every time a User is created, make sure a matching Customer profile exists."""
    if created:
        Customer.objects.get_or_create(user=instance)


@receiver(post_save, sender=Order)
def create_order_status_history(sender, instance, created, **kwargs):
    """Keep a timeline entry whenever an order is created or its status changes."""
    if created:
        OrderStatusHistory.objects.get_or_create(
            order=instance,
            status=instance.order_status,
            defaults={"note": "Order placed successfully."},
        )
        return

    previous = getattr(instance, "_previous_order_status", None)
    if previous and previous != instance.order_status:
        OrderStatusHistory.objects.create(
            order=instance,
            status=instance.order_status,
            note=f"Order status changed from {previous} to {instance.order_status}.",
        )



@receiver(pre_save, sender=Order)
def remember_previous_order_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_order_status = None
        return
    try:
        instance._previous_order_status = sender.objects.only("order_status").get(pk=instance.pk).order_status
    except sender.DoesNotExist:
        instance._previous_order_status = None
