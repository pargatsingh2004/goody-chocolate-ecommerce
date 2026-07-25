# THE GOODY CO. — Complete E-Commerce Website

## 🎯 Project Overview

A professional Django e-commerce website for THE GOODY CO. chocolate company, featuring:
- ✅ Beautiful customer-facing website (Bootstrap 5)
- ✅ Custom professional admin panel (NOT Django admin)
- ✅ Complete order management system
- ✅ Customer profile & order history tracking
- ✅ Comprehensive email system (transactional + newsletters)
- ✅ Product & category management with images
- ✅ Shopping cart & checkout
- ✅ User authentication with password reset
- ✅ Contact form with admin reply system
- ✅ Dashboard with analytics & charts
- ✅ Multi-method payment configuration (COD, UPI, Bank Transfer)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip

### Installation

```bash
# Navigate to the project folder
cd goody-app/goody/

# Install dependencies
pip install -r ../requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your email settings (Gmail recommended)

# Apply database migrations
python manage.py migrate

# Create admin account
python manage.py createsuperuser
# Username: admin
# Email: admin@example.com
# Password: (secure password)

# Start development server
python manage.py runserver
```

Visit **http://127.0.0.1:8000** 🎉

---

## 📍 Key URLs

### Customer Site
| Page | URL | Features |
|------|-----|----------|
| Home | `/` | Featured products, newsletter signup |
| Shop | `/shop` | Browse all products, filter by category |
| Product | `/product/<id>` | Details, reviews, related products |
| Cart | `/cart` | Review items, update quantities |
| Checkout | `/checkout` | Billing, payment method selection |
| Account | `/login`, `/register` | Authentication |
| Wishlist | `/wishlist` | Save favorites |
| Contact | `/contact` | Send message to admin |

### Admin Panel
| Section | URL | Features |
|---------|-----|----------|
| Login | `/control-panel/login/` | Staff-only access |
| Dashboard | `/control-panel/` | Stats, charts, notifications |
| Products | `/control-panel/products/` | CRUD + image uploads |
| Categories | `/control-panel/categories/` | Manage product categories |
| Orders | `/control-panel/orders/` | View & update order status |
| Customers | `/control-panel/customers/` | View profiles & order history |
| Contacts | `/control-panel/contacts/` | Reply to customer messages |
| Newsletter | `/control-panel/newsletter/` | Send campaigns |
| Settings | `/control-panel/settings/` | Payment configuration |

### Django Admin (Fallback)
- URL: `/django-admin/` (use superuser credentials)

---

## 📧 Email System

### Automatic Emails Sent
1. **Welcome** — on user registration
2. **Contact Confirmation** — immediately after form submission
3. **Admin Reply** — when admin replies to a contact
4. **Order Confirmation** — after successful order placement
5. **Order Status Update** — when order status changes
6. **Password Reset** — secure password reset link
7. **Newsletter** — admin-sent promotional campaigns

### Configuration
- Edit `.env` with SMTP credentials
- Gmail: Use [App Passwords](https://myaccount.google.com/apppasswords) (not regular password)
- Development: Use `console` backend to see emails in terminal

### Email Logs
All emails are logged in admin panel at `/control-panel/` (check database)

---

## 🛍️ Customer Features

### Browse & Shop
- Browse products by category
- Search products
- View product details & related items
- Add to wishlist
- Add to cart with quantity selection

### Checkout
- Session-based cart
- Billing address capture
- Multiple payment methods:
  - Cash on Delivery (COD)
  - UPI / QR Code (configured in admin)
  - Bank Transfer (account details in admin)
- Order total with shipping

### Account
- Create account (auto-creates customer profile)
- Login with "Remember Me" option
- Secure password reset via email
- View order history & status
- Manage profile information

### Communication
- Contact form (saves to database, sends confirmation email)
- Newsletter subscription
- Admin can reply to messages

---

## 🎛️ Admin Panel Features

### Dashboard
- **Statistics Cards**: Total products, orders, customers, revenue
- **Notifications**: New orders, unread messages, low stock items
- **Charts** (Chart.js):
  - Monthly sales (last 6 months)
  - Orders per month
  - Product category distribution
  - Revenue overview
- **Recent Orders Table**: Quick overview of latest orders

### Product Management
- View, add, edit, delete products
- Upload product images
- Set price, discount, stock levels
- Assign categories
- Mark as featured
- Filter by category and status
- Search by name

### Category Management
- Create categories
- Upload category images
- View product count per category
- Edit and delete

### Order Management
- View all orders
- Filter by order status & payment status
- See order details (items, totals, addresses)
- Update order status (auto-sends email to customer)
- Track payment status

### Customer Management
- View all customers
- See customer profile (name, email, phone, address)
- View order history
- Edit customer information
- Delete customer account

### Contact Management
- View all customer messages
- Filter by status (new, read, replied)
- Reply to messages (auto-sends email)
- Mark as read
- Delete messages
- Track conversation history

### Newsletter
- Send promotional emails to:
  - All registered customers
  - Selected customers
- Track send status & delivery logs
- View email history

### Settings
- Configure payment methods:
  - UPI ID & QR code
  - Bank account details (IFSC, account number, etc.)
  - Additional payment instructions
- Settings displayed to customers at checkout

---

## 🔒 Security

### Built-In
- CSRF protection on all forms
- Password hashing (Django default)
- Secure password reset tokens
- File upload validation
- SQL injection prevention (ORM)

### Admin Access
- Staff-only access (`is_staff=True`)
- Separate login from customer site
- Session management

### Best Practices
- Never commit `.env` file
- Use strong passwords
- Keep Django & dependencies updated
- Use HTTPS in production

---

## 💾 Database Schema

### Key Models
```
User
├── Customer (profile, phone, address)
├── Order (multiple per customer)
│   └── OrderItem (line items)
├── Wishlist items
└── (Django built-in auth fields)

Product
├── Category (FK)
├── Image
├── Price & discount
├── Stock levels
└── Status (active/inactive)

Category
├── Name, slug
├── Image
└── Description

Contact
├── Name, email, phone
├── Subject & message
├── Admin reply
└── Status & timestamps

EmailLog
├── Recipient email
├── Email type (welcome, order, etc.)
├── Status (sent/failed)
├── Error message (if failed)
└── Timestamp

NewsletterSubscriber
├── Email
├── Subscription status
└── Timestamp

PaymentSettings (singleton)
├── UPI ID & QR code
├── Bank account details
└── Payment instructions
```

---

## 🛠️ Development

### File Structure
```
goody-app/
├── requirements.txt          (Python dependencies)
├── SETUP_INSTRUCTIONS.md    (detailed setup guide)
├── IMPLEMENTATION_SUMMARY.md (complete changes list)
└── goody/
    ├── manage.py
    ├── .env.example         (copy to .env)
    ├── goody/              (project settings)
    │   ├── settings.py     (email, apps, database)
    │   ├── urls.py         (routing)
    │   └── wsgi.py
    ├── products/           (main app)
    │   ├── models.py       (Category, Product, Order, etc.)
    │   ├── views.py        (customer website)
    │   ├── forms.py
    │   ├── emails.py       (email helpers)
    │   ├── signals.py      (auto-create Customer)
    │   ├── admin.py        (Django admin fallback)
    │   ├── urls.py
    │   ├── static/         (CSS, JS, images)
    │   ├── media/          (uploaded files)
    │   └── templates/
    │       ├── products/   (customer pages)
    │       └── emails/     (email templates)
    └── admin_panel/        (custom admin panel)
        ├── views.py        (admin logic)
        ├── forms.py        (admin forms)
        ├── decorators.py   (staff_required)
        ├── urls.py
        ├── context_processors.py
        ├── static/
        │   ├── css/admin.css
        │   └── js/admin.js
        └── templates/admin_panel/
            ├── base.html
            ├── login.html
            ├── dashboard.html
            ├── products.html
            ├── orders.html
            ├── customers.html
            ├── contacts.html
            ├── newsletter.html
            └── ... (15+ templates)
```

### Common Tasks

#### Add a Product Programmatically
```python
python manage.py shell
>>> from products.models import Category, Product
>>> cat = Category.objects.get(name="Dark Chocolate")
>>> Product.objects.create(
...     category=cat,
...     name="85% Dark",
...     description="Intense and bitter",
...     price=399,
...     discount=5,
...     stock=100,
...     status='active',
... )
```

#### Send Test Email
```python
python manage.py shell
>>> from products import emails
>>> from django.contrib.auth.models import User
>>> user = User.objects.first()
>>> emails.send_welcome_email(user)
```

#### Make a User Staff
```python
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username='alice')
>>> user.is_staff = True
>>> user.save()
```

---

## 🚢 Deployment

### Checklist
- [ ] Set `DEBUG=False` in settings
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Use PostgreSQL (not SQLite)
- [ ] Set up HTTPS/SSL
- [ ] Configure production email service
- [ ] Set strong `SECRET_KEY`
- [ ] Use environment variables for all secrets
- [ ] Run `collectstatic`
- [ ] Set up database backups
- [ ] Configure logging & monitoring
- [ ] Use Gunicorn/uWSGI + Nginx

### Hosting Options
- **Heroku** — easy, free tier available
- **DigitalOcean** — affordable VPS
- **AWS** — scalable, production-grade
- **PythonAnywhere** — Python-specific hosting

---

## 📚 Documentation

### In This Repository
- `SETUP_INSTRUCTIONS.md` — Step-by-step setup
- `IMPLEMENTATION_SUMMARY.md` — All files changed
- `README.md` — This file

### External Resources
- [Django Documentation](https://docs.djangoproject.com/)
- [Bootstrap 5](https://getbootstrap.com/docs/5.0/)
- [Chart.js](https://www.chartjs.org/docs/latest/)
- [Django Email](https://docs.djangoproject.com/en/stable/topics/email/)

---

## 🐛 Troubleshooting

### Email Not Sending?
```bash
# Check .env file has correct credentials
# Check EMAIL_LOG table for errors
# During dev, use console backend to see emails
```

### Import Errors?
```bash
# Make sure all migrations ran
python manage.py migrate

# Make sure admin_panel is in INSTALLED_APPS
# Check settings.py
```

### Port Conflicts?
```bash
# Use different port
python manage.py runserver 8001

# Or kill process on port 8000
sudo lsof -ti:8000 | xargs kill -9
```

### Database Locked?
```bash
# Reset database (development only!)
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

---

## 📞 Support

Need help? Check these in order:
1. `SETUP_INSTRUCTIONS.md` (step-by-step)
2. `IMPLEMENTATION_SUMMARY.md` (what was added)
3. Django Docs: https://docs.djangoproject.com/
4. Comments in the code (well-documented)

---

## 📄 License

Internal use for THE GOODY CO. © 2026

---

## ✨ Credits

Built with Django, Bootstrap 5, Chart.js, and Font Awesome.

---

**Last Updated:** July 19, 2026  
**Version:** 1.0.0  
**Django:** 5.0+  
**Python:** 3.8+

