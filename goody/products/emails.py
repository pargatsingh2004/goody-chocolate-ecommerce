"""
Centralised email-sending helpers.

Every function here renders an HTML template under
products/templates/emails/, sends it through Django's SMTP backend, and
writes a row to EmailLog so the admin panel can show a full history —
successes and failures alike.
"""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import EmailLog


def _send(*, to_email, subject, template_name, context, email_type, sent_by="System"):
    """
    Render `template_name` with `context`, send it, and log the result.
    Never raises — a broken SMTP config should not break the request that
    triggered the email (e.g. placing an order).
    """
    context = {**context, "site_name": "THE GOODY CO.", "site_url": getattr(settings, "SITE_URL", "")}
    html_body = render_to_string(f"emails/{template_name}", context)
    text_body = strip_tags(html_body)

    status = "sent"
    error_message = ""

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
    except Exception as exc:  # noqa: BLE001 - we want to log *any* failure
        status = "failed"
        error_message = str(exc)

    EmailLog.objects.create(
        recipient=to_email,
        subject=subject,
        email_type=email_type,
        sent_by=sent_by,
        status=status,
        error_message=error_message,
    )
    return status == "sent"


def send_welcome_email(user):
    return _send(
        to_email=user.email,
        subject="Welcome to THE GOODY CO.! 🍫",
        template_name="welcome.html",
        context={"user": user},
        email_type="welcome",
    )


def send_contact_confirmation_email(contact):
    return _send(
        to_email=contact.email,
        subject="We've received your message — THE GOODY CO.",
        template_name="contact_confirmation.html",
        context={"contact": contact},
        email_type="contact_confirmation",
    )


def send_admin_reply_email(contact, admin_username="Admin"):
    return _send(
        to_email=contact.email,
        subject=f"Re: {contact.subject} — THE GOODY CO.",
        template_name="admin_reply.html",
        context={"contact": contact},
        email_type="admin_reply",
        sent_by=admin_username,
    )


def send_order_confirmation_email(order):
    return _send(
        to_email=order.email or (order.customer.email if order.customer else ""),
        subject=f"Order Confirmation — #{order.id} — THE GOODY CO.",
        template_name="order_confirmation.html",
        context={"order": order, "items": order.items.all()},
        email_type="order_confirmation",
    )


def send_order_status_update_email(order):
    return _send(
        to_email=order.email or (order.customer.email if order.customer else ""),
        subject=f"Your Order #{order.id} is now {order.get_order_status_display()} — THE GOODY CO.",
        template_name="order_status_update.html",
        context={"order": order},
        email_type="order_status_update",
    )


def send_newsletter_email(subject, message_html, recipient_email, admin_username="Admin"):
    return _send(
        to_email=recipient_email,
        subject=subject,
        template_name="newsletter.html",
        context={"message_html": message_html, "subject": subject},
        email_type="newsletter",
        sent_by=admin_username,
    )
