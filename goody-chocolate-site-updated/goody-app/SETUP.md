# THE GOODY CO. - E-Commerce Website Setup Guide

## Overview

This is a **production-ready** Django e-commerce platform for THE GOODY CO. chocolate company featuring:
- **Customer-facing website** (shop, checkout, user accounts)
- **Custom admin panel** (not Django admin) with dark theme for managing products, orders, customers, contacts, and newsletters
- **Email system** (transactional & promotional emails via SMTP)
- **Order management** with multiple payment methods
- **Newsletter system** for promotional campaigns
- **Security & authentication** with password reset flows

---

## Prerequisites

- Python 3.8+
- pip (Python package manager)
- A text editor or IDE (VS Code, PyCharm, etc.)
- A Gmail account (or any SMTP email service) for sending emails

---

## Quick Setup

### 1. Extract & Navigate

```bash
cd goody-chocolate-site-updated/goody-app/goody
```

### 2. Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and fill in **real values** (this file is read by Django automatically):

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
# During development, use console backend (prints emails to terminal).
# For production, use SMTP backend:
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password  # NOT your Gmail password!
EMAIL_USE_TLS=True

DEFAULT_FROM_EMAIL=your-email@gmail.com
SITE_URL=http://127.0.0.1:8000
```

**Note:** For Gmail, generate a 16-character [App Password](https://support.google.com/accounts/answer/185833) instead of using your regular password.

### 5. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create a Superuser (Admin Account)

```bash
python manage.py createsuperuser
# Follow the prompts to create your admin account
```

### 7. Run the Development Server

```bash
python manage.py runserver
```

Visit: **http://127.0.0.1:8000**

---

## Access Points

### Customer Website
- **Home:** http://127.0.0.1:8000/
- **Shop:** http://127.0.0.1:8000/shop/
- **Contact:** http://127.0.0.1:8000/contact/
- **Login/Register:** http://127.0.0.1:8000/register/

### Custom Admin Panel
- **Login:** http://127.0.0.1:8000/control-panel/login/
- **Dashboard:** http://127.0.0.1:8000/control-panel/ (after login)

**Admin Credentials:** Use the superuser account created in step 6.

### Django Admin (Fallback)
- **Admin:** http://127.0.0.1:8000/django-admin/

---

## Key Features

### Customer Features
- Browse products by category
- Add items to cart & wishlist
- Checkout with multiple payment methods (COD, UPI, Bank Transfer)
- User registration & login (with remember me)
- Password reset via email
- Order tracking
- Contact form submission

### Admin Panel Features

#### Dashboard
- Statistics cards (products, orders, customers, revenue)
- Monthly sales & orders charts
- Category distribution pie chart
- Notification badges for pending orders, messages, low stock

#### Product Management
- Add/edit/delete products
- Upload product images
- Set discounts & prices
- Mark as featured
- Manage inventory/stock
- Category filtering

#### Order Management
- View all orders with filters
- Update order status & payment status
- Track customer info & shipping address
- Send automated status update emails

#### Customer Management
- View customer profiles
- Track purchase history & total spent
- Edit customer details

#### Contact Management
- View customer inquiries
- Reply to messages (auto-sends email)
- Mark as read/replied
- Search & filter

#### Newsletter System
- Send promotional emails to all or selected customers
- Track email send history
- HTML template support

#### Settings
- Configure UPI/QR code details
- Bank account information
- Payment instructions for customers

---

## Email Configuration

### Development (Console Backend)
By default, `.env.example` uses the console backend. Emails print to the terminal—perfect for testing without an actual SMTP account.

### Production (Gmail SMTP)

1. **Enable 2-Step Verification** on your Gmail account.
2. **Generate an App Password** at: https://support.google.com/accounts/answer/185833
3. **Update `.env`:**

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=your-email@gmail.com
SITE_URL=https://yourdomain.com  # Your production URL
```

### Email Templates

All email templates are in `products/templates/emails/`:
- `welcome.html` – Welcome email on registration
- `contact_confirmation.html` – Confirmation when customer submits contact form
- `admin_reply.html` – Admin reply to customer inquiry
- `order_confirmation.html` – Order confirmation with items & totals
- `order_status_update.html` – Notification when order status changes
- `password_reset.html` – Password reset link (Django built-in)
- `newsletter.html` – Promotional newsletter template

You can customize these HTML templates to match your brand.

---

## Database Models

### Key Models

**Product**
- name, description, price, discount, stock
- image, status (active/inactive), featured flag
- category (ForeignKey to Category)

**Category**
- name, slug, image, description

**Order**
- customer (ForeignKey to User), full_name, email, phone
- address, city, state, pincode
- payment_method, payment_status, order_status
- subtotal, shipping_fee, total_price
- created_at, updated_at

**OrderItem**
- order (ForeignKey), product, product_name, quantity, price

**Contact**
- name, email, phone, subject, message
- reply, status (new/read/replied), created_at, replied_at

**Customer**
- user (OneToOneField), phone, address, created_at
- Auto-created when a User is registered (via Django signals)

**EmailLog**
- recipient, subject, email_type, status (sent/failed)
- sent_by, error_message, created_at

**NewsletterSubscriber**
- email, subscribed_at, is_active

**PaymentSettings**
- Singleton model (always pk=1)
- upi_id, qr_code (image)
- bank_name, account_number, ifsc_code, etc.

---

## Common Tasks

### Add a New Product (Admin)
1. Login at http://127.0.0.1:8000/control-panel/login/
2. Go to **Product Management → Add Product**
3. Fill in name, price, stock, upload image
4. Click **Create Product**

### Manage Orders
1. Go to **Order Management**
2. Click on an order to view details
3. Update order status (pending → processing → shipped → delivered)
4. An email is automatically sent to the customer when status changes

### Send Newsletter
1. Go to **Newsletter**
2. Write subject & message (HTML allowed)
3. Choose recipients (all customers or selected)
4. Click **Send Newsletter**

### Receive Customer Messages
1. Customer submits contact form on website
2. Message appears in **Contact Management**
3. Admin can reply directly from the panel
4. Reply is emailed to customer & marked as "Replied"

### Reset Admin Password
If you forget the admin password:
```bash
python manage.py changepassword admin_username
```

---

## Static Files & Media

- **Static files** (CSS, JS, images): `products/static/`
- **Uploaded images**: `media/products/`, `media/categories/`, `media/payment/`

In development, Django serves these automatically. For production, run:
```bash
python manage.py collectstatic
```

---

## Deployment Checklist

Before going live:

1. **Set DEBUG = False** in `settings.py`
2. **Update ALLOWED_HOSTS** with your domain
3. **Use a production email service** (Gmail, SendGrid, AWS SES, etc.)
4. **Configure SSL/HTTPS**
5. **Use a production database** (PostgreSQL recommended)
6. **Set SECRET_KEY** as an environment variable
7. **Run collectstatic** for static files
8. **Use a production WSGI server** (Gunicorn, uWSGI)
9. **Serve with Nginx or Apache**
10. **Enable CSRF_TRUSTED_ORIGINS** for your domain

For detailed deployment help, see [Django Deployment Checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/).

---

## Troubleshooting

### Emails not sending?
- Check `.env` is in the same folder as `manage.py`
- Verify SMTP credentials (especially App Password for Gmail)
- Check console/logs for errors
- Try with `console` backend first to rule out template issues

### "ModuleNotFoundError: No module named 'django'"
- Activate virtual environment: `source venv/bin/activate`
- Reinstall: `pip install -r requirements.txt`

### Images not displaying?
- Ensure `MEDIA_URL` and `MEDIA_ROOT` in `settings.py`
- Run `python manage.py runserver` with DEBUG = True

### Admin panel login not working?
- Ensure you created a superuser: `python manage.py createsuperuser`
- Check that user has `is_staff = True` (set by `createsuperuser`)

---

## File Structure

```
goody-app/goody/
├── manage.py
├── .env                          # Email config (create from .env.example)
├── requirements.txt              # Python dependencies
├── db.sqlite3                    # SQLite database (dev only)
│
├── goody/                        # Project settings
│   ├── settings.py              # Django settings
│   ├── urls.py                  # Main URL routing
│   ├── wsgi.py
│   └── asgi.py
│
├── products/                     # Customer-facing app
│   ├── models.py                # Product, Order, Contact, etc.
│   ├── views.py                 # Shop, checkout, auth views
│   ├── urls.py
│   ├── forms.py
│   ├── emails.py                # Email sending helpers
│   ├── signals.py               # Auto-create Customer on User registration
│   ├── admin.py                 # Django admin registrations
│   ├── templates/products/      # Customer templates
│   │   ├── home.html
│   │   ├── shop.html
│   │   ├── checkout.html
│   │   ├── contact.html
│   │   ├── login.html
│   │   └── ...
│   ├── templates/emails/        # Transactional email templates
│   │   ├── welcome.html
│   │   ├── order_confirmation.html
│   │   ├── password_reset.html
│   │   └── ...
│   ├── static/products/         # Customer CSS, JS, images
│   └── migrations/
│
├── admin_panel/                 # Custom admin panel
│   ├── views.py                 # Dashboard, CRUD views
│   ├── urls.py
│   ├── forms.py                 # Product, Order, Newsletter forms
│   ├── decorators.py            # @staff_required decorator
│   ├── context_processors.py   # Notification badges
│   ├── templates/admin_panel/   # Admin UI templates
│   │   ├── base.html            # Sidebar layout
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── products.html
│   │   ├── orders.html
│   │   ├── customers.html
│   │   ├── contacts.html
│   │   ├── newsletter.html
│   │   ├── settings.html
│   │   └── ...
│   ├── static/admin_panel/
│   │   ├── css/admin.css        # Dark admin theme
│   │   └── js/admin.js          # Sidebar, modals, filters
│   └── migrations/
│
└── media/                       # Uploaded files
    ├── products/
    ├── categories/
    └── payment/
```

---

## Support & Customization

### Customizing the Theme
- Customer site: Edit `products/static/` CSS
- Admin panel: Edit `admin_panel/static/admin_panel/css/admin.css`

### Adding New Features
- Create models in `products/models.py`
- Create views in `admin_panel/views.py` or `products/views.py`
- Create templates in respective `templates/` folders
- Register models in Django admin (`products/admin.py`)

### Email Customization
Edit HTML templates in `products/templates/emails/` to add your logo, adjust colors, or change wording.

---

## License & Credits

Developed for **THE GOODY CO.** chocolate company.

Enjoy! 🍫
