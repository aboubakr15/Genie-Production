# leads/forms.py
from django import forms

class CompanyListForm(forms.Form):
    company_names = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Enter company names, one per line.\nExample:\nGoogle\nApple\nAmazon',
            'rows': 10,
            'class': 'form-textarea' # We'll use this class for styling
        }),
        label='', # We'll handle the label in the template for more control
        help_text='' # We'll add help text manually in the template
    )