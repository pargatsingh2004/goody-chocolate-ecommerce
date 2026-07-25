from django import forms
from products.models import Product, Category, Contact, Order


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'description', 'price', 'discount',
            'stock', 'image', 'status', 'featured',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product name'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'content_type'):
            valid_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
            if image.content_type not in valid_types:
                raise forms.ValidationError("Only JPEG, PNG, WEBP or GIF images are allowed.")
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image file too large ( > 5MB ).")
        return image


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'image', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category name'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ContactReplyForm(forms.Form):
    reply = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Write your reply...'}),
        label="Reply message",
    )


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['order_status', 'payment_status']
        widgets = {
            'order_status': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'payment_status': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        }


class AdminLoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))


class NewsletterForm(forms.Form):
    RECIPIENT_CHOICES = [
        ('all', 'All Registered Customers'),
        ('selected', 'Selected Customers'),
    ]
    subject = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email subject'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 8, 'placeholder': 'Write your promotional message (HTML allowed)...'}))
    recipients = forms.ChoiceField(choices=RECIPIENT_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    selected_customers = forms.CharField(required=False, widget=forms.HiddenInput())
