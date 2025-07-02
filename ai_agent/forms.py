from django import forms

class CompanyListForm(forms.Form):
    companies = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 20, 'placeholder': 'Paste company names, one per line...'}),
        label='Company Names',
        help_text='Paste a list of company names, one per line.'
    )
