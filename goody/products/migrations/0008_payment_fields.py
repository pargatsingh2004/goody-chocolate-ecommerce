from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0007_ecommerce_architecture'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='razorpay_order_id',
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.AddField(
            model_name='order',
            name='razorpay_payment_id',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='order',
            name='razorpay_signature',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='order',
            name='payment_method',
            field=models.CharField(choices=[('cod', 'Cash on Delivery'), ('upi', 'UPI / QR Payment'), ('bank', 'Bank Transfer'), ('razorpay', 'Online Payment (Razorpay)')], default='cod', max_length=10),
        ),
    ]
