# THE GOODY CO. — Django E-Commerce Setup Instructions

This document guides you through setting up and running the enhanced Django e-commerce website with the new custom admin panel, order management, email system, and more.

---

## 1. Environment Setup

### 1.1 Install Dependencies
```bash
# From the goody-app folder:
pip install -r requirements.txt
```

### 1.2 Configure Environment Variables
```bash
# Copy .env.example to .env and fill in your email credentials
cp goody/.env.example goody/.env
```

Edit `goody/.env`:
```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=your-email@gmail.com
SITE_URL=http://127.0.0.1:8000
```

**For Gmail:**
1. Enable 2-Step Verification on your Google Account
2. Generate an [App Password](https://myaccount.google.com/apppasswords)
3. Use that 16-character password in EMAIL_HOST_PASSWORD

**During Development:** You can use `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` to see emails printed to the terminal instead of sending them.

---

## 2. Database Migrations

Run these commands from the `goody/` folder (where `manage.py` is):

```bash
# Apply all migrations to create tables
python manage.py migrate

# Create a superuser (admin) account
python manage.py createsuperuser
# Follow the prompts to set username, email, and password

# (Optional) Create some sample data
python manage.py shell
>>> from products.models import Category, Product
>>> cat = Category.objects.create(name="Dark Chocolate")
>>> Product.objects.create(
...     category=cat,
...     name="70% Dark Chocolate",
...     description="Rich and intense",
...     price=299.00,
...     discount=10,
...     stock=50,
...     status='active'
... )
>>> exit()
```

---

## 3. Create Admin Panel User

Only users with `is_staff=True` can access the custom admin panel at `/control-panel/`.

### Option A: Use the Superuser (Recommended)
The superuser you created above automatically has `is_staff=True`.

### Option B: Create Additional Staff Users
```bash
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.create_user(
...     username='admin2',
...     email='admin2@goodyco.com',
...     password='SecurePass123!',
...     is_staff=True
... )
>>> exit()
```

---

## 4. Run the Development Server

```bash
python manage.py runserver
```

The site will be available at **http://127.0.0.1:8000**

---

## 5. Access the Application

### Customer Website
- **Home**: http://127.0.0.1:8000/
- **Shop**: http://127.0.0.1:8000/shop
- **Login**: http://127.0.0.1:8000/login
- **Register**: http://127.0.0.1:8000/register
- **Contact**: http://127.0.0.1:8000/contact

### Admin Panel (Custom)
- **Login**: http://127.0.0.1:8000/control-panel/login/
- **Dashboard**: http://127.0.0.1:8000/control-panel/
- **Products**: http://127.0.0.1:8000/control-panel/products/
- **Orders**: http://127.0.0.1:8000/control-panel/orders/
- **Customers**: http://127.0.0.1:8000/control-panel/customers/
- **Contacts**: http://127.0.0.1:8000/control-panel/contacts/

### Django Admin (Fallback)
- **URL**: http://127.0.0.1:8000/django-admin/
- Use your superuser credentials

---

## 6. Key Features

### Customer Features
- ✅ Browse products by category
- ✅ Add to cart & checkout
- ✅ Create account & login (with remember me)
- ✅ Order history & tracking
- ✅ Wishlist
- ✅ Newsletter subscription
- ✅ Contact form (gets saved to admin)
- ✅ Password reset via email
- ✅ Multiple payment methods (COD, UPI, Bank Transfer)

### Admin Panel Features
- ✅ **Dashboard** with charts (Chart.js), stats, recent orders, notifications
- ✅ **Product Management** (CRUD, images, categories, discounts, stock)
- ✅ **Category Management** (CRUD)
- ✅ **Order Management** (view, update status, track payments)
- ✅ **Customer Management** (view profiles, order history)
- ✅ **Contact Management** (view messages, reply to customers)
- ✅ **Newsletter** (send to all or selected customers)
- ✅ **Settings** (payment methods configuration)

### Email System
- ✅ Welcome email on registration
- ✅ Contact form confirmation
- ✅ Admin reply to contacts
- ✅ Order confirmation
- ✅ Order status updates
- ✅ Password reset
- ✅ Newsletter campaigns
- ✅ Email logs (track delivery)

---

## 7. Static Files & Media

During development, static files and media are served automatically:
- **Static files** (CSS, JS, images): `products/static/` and `admin_panel/static/`
- **Media files** (uploaded products, categories): `media/`

For production, run:
```bash
python manage.py collectstatic
```

---

## 8. Troubleshooting

### Email Not Sending?
- Check `.env` credentials
- If using Gmail, verify you have an App Password (not regular password)
- Check `EmailLog` table in admin panel for error messages
- During dev, switch to console backend to see errors immediately

### Migrations Failed?
```bash
# Reset migrations (only in development!)
python manage.py migrate admin_panel zero
python manage.py migrate products zero
python manage.py migrate
```

### Port Already in Use?
```bash
# Use a different port
python manage.py runserver 8001
```

### Can't Access Admin Panel?
- Verify user has `is_staff=True`
- Check `createsuperuser` was run
- Try `/django-admin/` as fallback

---

## 9. Production Deployment Checklist

Before deploying to production:

- [ ] Set `DEBUG=False` in settings.py
- [ ] Set `ALLOWED_HOSTS` to your domain(s)
- [ ] Use a production database (PostgreSQL recommended)
- [ ] Set up HTTPS (SSL certificate)
- [ ] Use a production email service (SendGrid, Mailgun, AWS SES)
- [ ] Use environment variables for all secrets
- [ ] Run `collectstatic` for static files
- [ ] Configure a web server (Gunicorn, uWSGI)
- [ ] Use a reverse proxy (Nginx, Apache)
- [ ] Set up database backups
- [ ] Configure logging
- [ ] Use a task queue (Celery) for async emails if needed

---

## 10. Support

For issues or questions, refer to:
- Django Documentation: https://docs.djangoproject.com/
- Bootstrap Documentation: https://getbootstrap.com/docs/
- Chart.js Documentation: https://www.chartjs.org/docs/latest/

---

**Last Updated:** July 2026
**Django Version:** 5.0+
**Python Version:** 3.8+
