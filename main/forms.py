from django import forms
from .models import Sheet, FilterWords, FilterType, Lead

class ImportSheetsForm(forms.Form):
    folder_path = forms.CharField(label='Folder Path', max_length=255)

# Without acceptance for operations managers and team leader
class AutoFillForm(forms.Form):
    file = forms.FileField(required=True, label="Choose a file")
    latest_sheet = forms.ModelChoiceField(
        queryset=Sheet.objects.all(), 
        required=False, 
        label="Select a Sheet",
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class FilterWordsForm(forms.ModelForm):
    filter_types = forms.ModelMultipleChoiceField(
        queryset=FilterType.objects.all(),
        widget=forms.CheckboxSelectMultiple,  # This will show the filter types as checkboxes
        required=True
    )

    class Meta:
        model = FilterWords
        fields = ['word', 'filter_types']



class LeadForm(forms.ModelForm):
    sheets = forms.ModelMultipleChoiceField(
        queryset=Sheet.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        help_text='Select one or more sheets from the dropdown.',
    )
    phone_numbers = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Enter phone numbers with time zones. Format: "phone_number,time_zone" on each line',
            'rows': 4
        }),
        required=False,
        help_text='Enter one phone number per line with format: "phone_number,time_zone".'
    )
    emails = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Enter emails separated by commas'}),
        required=False,
        help_text='Enter multiple emails separated by commas.'
    )
    contact_names = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Enter contact names separated by commas'}),
        required=False,
        help_text='Enter multiple contact names separated by commas.'
    )

    class Meta:
        model = Lead
        fields = ['name', 'sheets', 'phone_numbers', 'emails', 'contact_names']