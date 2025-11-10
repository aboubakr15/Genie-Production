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