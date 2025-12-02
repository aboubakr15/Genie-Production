from django import forms
from .models import Category

class CompanyListForm(forms.Form):
    company_names = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Enter company names, one per line.\nExample:\nGoogle\nApple\nAmazon',
            'rows': 10,
            'class': 'form-textarea'
        }),
        label='Company Names'
    )
    
    excel_sheet_name = forms.CharField(
        initial='Enriched Leads',
        max_length=31,  # Excel sheet name limit
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter Excel sheet name (max 31 characters)',
            'class': 'form-control',
            'maxlength': '31'
        }),
        label='Excel Sheet Name',
        help_text='Maximum 31 characters.'
    )

    show_name = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            'placeholder': 'Optional: Enter show or conference name',
            'class': 'form-control'
        }),
        label='Show/Conference Name',
        help_text='Providing a show name helps find the correct company industry.'
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True).order_by('name'),
        required=False,
        empty_label='Select a category (optional)',
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Category',
        help_text='Select a category to help filter companies by industry/type and get more accurate results.'
    )


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name (e.g., Technology, Healthcare, Manufacturing)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional: Enter a description for this category'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'name': 'Category Name',
            'description': 'Description',
            'is_active': 'Active'
        }
        help_texts = {
            'name': 'Enter a descriptive category name (e.g., Technology, Healthcare, Manufacturing)',
            'description': 'Optional description to help users understand what this category represents',
            'is_active': 'Inactive categories will not appear in the dropdown menu'
        }