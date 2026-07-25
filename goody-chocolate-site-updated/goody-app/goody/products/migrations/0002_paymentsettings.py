# Generated manually to add PaymentSettings (admin-editable QR / bank details)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('upi_id', models.CharField(blank=True, help_text='e.g. goodyco@upi — shown to the customer for UPI payment.', max_length=100)),
                ('qr_code', models.ImageField(blank=True, help_text='Upload the UPI / payment QR code image.', null=True, upload_to='payment/')),
                ('bank_name', models.CharField(blank=True, max_length=150)),
                ('account_holder_name', models.CharField(blank=True, max_length=150)),
                ('account_number', models.CharField(blank=True, max_length=50)),
                ('ifsc_code', models.CharField(blank=True, max_length=20)),
                ('bank_branch', models.CharField(blank=True, max_length=150)),
                ('instructions', models.TextField(blank=True, help_text="Extra note shown to the customer under the payment details (e.g. 'Send payment screenshot on WhatsApp after transfer').")),
            ],
            options={
                'verbose_name': 'Payment Setting',
                'verbose_name_plural': 'Payment Settings',
            },
        ),
    ]
