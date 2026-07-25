# THE GOODY CO. - E-Commerce Platform

A **complete, production-ready** Django e-commerce website with a custom admin panel, email system, and order management.

## 🎯 What's Included

### ✅ Customer-Facing Website
- Browse products by category
- Search functionality
- Shopping cart & checkout
- Multiple payment methods (COD, UPI, Bank Transfer)
- User registration & login
- Secure password reset
- Order tracking
- Wishlist
- Contact form
- Newsletter subscription

### ✅ Custom Admin Panel
- Professional dark-themed dashboard
- Statistics with Chart.js graphs
- Product management (CRUD + image upload)
- Category management
- Order management with status tracking
- Customer profiles & history
- Contact inbox with reply system
- Newsletter composer & sender
- Payment settings (UPI, bank details)
- Admin login with "remember me"

### ✅ Email System
- Transactional emails (welcome, order confirmation, status updates)
- Promotional newsletters
- Password reset emails
- Automatic email logging & failure tracking
- Support for Gmail, SendGrid, or any SMTP service

### ✅ Database Models
- Product, Category, Order, Customer, Contact, EmailLog
- Payment settings singleton
- Newsletter subscribers
- Wishlist
- Full order management with order items

---

## 🚀 Quick Start

### 1. Navigate to Project
```bash
cd goody-chocolate-site-updated/goody-app/goody
```

### 2. Create Virtual Environment
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
pip install -r ../requirements.txt
```

### 4. Configure Email
```bash
cp .env.example .env
# Edit .env with your SMTP credentials (Gmail, SendGrid, etc.)
```

### 5. Setup Database
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 6. Run Server
```bash
python manage.py runserver
```

### 7. Access the Application
- **Customer Site:** http://127.0.0.1:8000/
- **Admin Panel:** http://127.0.0.1:8000/control-panel/
- **Django Admin (Fallback):** http://127.0.0.1:8000/django-admin/

---

## 📚 Documentation

- **`SETUP.md`** – Comprehensive setup guide, email configuration, deployment checklist
- **`IMPLEMENTATION_SUMMARY.md`** – Complete list of all files created/modified

---

## 📁 Project Structure

```
goody-app/goody/
├── manage.py
├── .env                          # Email configuration (copy from .env.example)
├── requirements.txt              # Python dependencies
│
├── products/                     # Customer-facing app
│   ├── models.py                # Product, Order, Customer, Contact models
│   ├── views.py                 # Shop, checkout, auth views
│   ├── emails.py                # Email sending helpers
│   ├── signals.py               # Auto-create Customer on registration
│   ├── templates/products/      # Customer HTML templates
│   ├── templates/emails/        # Email templates (7 types)
│   └── static/                  # Customer CSS, images
│
├── admin_panel/                 # Custom admin dashboard
│   ├── views.py                 # 20+ admin views (CRUD, dashboard, etc.)
│   ├── forms.py                 # Admin forms
│   ├── decorators.py            # @staff_required decorator
│   ├── templates/admin_panel/   # Admin HTML templates
│   ├── static/admin_panel/      # Admin CSS (dark theme), JS
│   └── urls.py                  # Admin URL routing
│
├── goody/                       # Django project settings
│   ├── settings.py              # Django configuration + .env loader
│   └── urls.py                  # Main URL routing
│
└── media/                       # Uploaded files (products, categories)
```

---

## 🔑 Key Features

### Admin Panel Dashboard
- 4 statistics cards (total products, orders, customers, revenue)
- 4 Chart.js graphs (monthly sales, orders, category distribution, revenue)
- Recent orders table
- Notification badges for pending orders, new messages, low stock

### Product Management
- Add/edit/delete products
- Upload product images (with validation)
- Set prices, discounts, stock
- Mark as featured
- Category assignment
- Pagination & search/filter

### Order Management
- View all orders
- Update order & payment status
- Automatic customer notification emails on status change
- Customer shipping info
- Order items breakdown

### Customer Management
- Customer profiles with purchase history
- Edit customer details
- Total spent tracking

### Contact Management
- Customer inquiry inbox
- Reply directly from admin panel (auto-sends email)
- Mark as read/replied
- Search & filter

### Newsletter
- Compose promotional emails (HTML support)
- Send to all customers or select specific ones
- Track email sending history

---

## 📧 Email Configuration

### Development (Console Backend)
Emails print to terminal - perfect for testing without an SMTP account.

### Production (Real SMTP)
Edit `.env` with real SMTP credentials:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=your-email@gmail.com
SITE_URL=https://yourdomain.com
```

**For Gmail:**
1. Enable 2-Step Verification
2. Generate [App Password](https://support.google.com/accounts/answer/185833)
3. Use the 16-character password in `.env`

---

## 🔒 Security

- ✅ CSRF protection on all forms
- ✅ Secure password hashing
- ✅ Staff-only admin access
- ✅ Secure password reset flow
- ✅ File upload validation (images only, size limits)
- ✅ Input sanitization
- ✅ Never hardcoded secrets (all in .env)

---

## 📊 Database Models

### Product
- name, description, price, discount, stock
- image, status, featured flag, category

### Order
- customer, full_name, email, phone
- address, city, state, pincode
- payment_method, payment_status, order_status
- subtotal, shipping_fee, total_price

### Customer
- user (OneToOne), phone, address
- Auto-created when user registers

### Contact
- name, email, phone, subject, message
- reply, status (new/read/replied)

### EmailLog
- Tracks all sent emails (recipient, subject, type, status)

### PaymentSettings
- Singleton config for UPI, bank details

---

## 🚢 Deployment

### Before Going Live
1. Set `DEBUG = False` in settings.py
2. Update `ALLOWED_HOSTS` with your domain
3. Configure real SMTP email service
4. Switch to PostgreSQL (not SQLite)
5. Collect static files: `python manage.py collectstatic`
6. Use production WSGI server (Gunicorn, uWSGI)
7. Configure reverse proxy (Nginx)
8. Enable HTTPS/SSL

See **SETUP.md** → **Deployment Checklist** for full details.

---

## 🛠️ Customization

### Change Admin Theme
Edit `admin_panel/static/admin_panel/css/admin.css` (uses CSS variables)

### Customize Email Templates
Edit `products/templates/emails/*.html` (extends base_email.html)

### Add New Features
1. Create model in `products/models.py`
2. Create view in `admin_panel/views.py`
3. Create template in `admin_panel/templates/`
4. Register URL in `admin_panel/urls.py`

---

## 📞 Support & Troubleshooting

### Emails not sending?
- Check `.env` credentials
- Verify EMAIL_BACKEND in `.env`
- Check logs for SMTP errors
- Test with console backend first

### "Module not found" errors?
- Activate virtual environment
- Reinstall: `pip install -r requirements.txt`

### Admin panel not accessible?
- User must have `is_staff = True`
- Created via `python manage.py createsuperuser`

### Images not displaying?
- Check `MEDIA_URL` and `MEDIA_ROOT` in settings.py
- Ensure `DEBUG = True` in development

---

## 📝 Files Changed

- **42 new files created** (models, views, templates, CSS, JS)
- **16 files modified** (settings, views, URLs, templates)
- **~5,000+ lines of code**

See **IMPLEMENTATION_SUMMARY.md** for complete file-by-file breakdown.

---

## 🎉 What's Next?

Optional enhancements:
- [ ] Payment gateway (Razorpay, Stripe)
- [ ] Analytics dashboard
- [ ] Promotional codes/coupons
- [ ] SMS notifications
- [ ] Product reviews & ratings
- [ ] Inventory alerts
- [ ] AI recommendations
- [ ] Multi-language support

---

## 📄 License

Developed for **THE GOODY CO.** chocolate company.

---

**Happy coding! 🍫**

For detailed setup instructions, see **SETUP.md** in the `goody-app/` folder.
