from django import forms

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
        max_length=200,  # Excel sheet name limit
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter Excel sheet name (max 200 characters)',
            'class': 'form-control',
            'maxlength': '200'
        }),
        label='Excel Sheet Name',
        help_text='Maximum 200 characters.'
    )