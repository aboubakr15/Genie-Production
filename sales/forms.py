from django import forms
from main.models import LeadPhoneNumbers, LeadEmails, LeadContactNames

class LeadPhoneNumberForm(forms.ModelForm):
    class Meta:
        model = LeadPhoneNumbers
        fields = ['value']
        widgets = {
            'value': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Add phone number',
                "required":"false"
            }),
        }

class LeadEmailForm(forms.ModelForm):
    class Meta:
        model = LeadEmails
        fields = ['value']
        widgets = {
            'value': forms.EmailInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Add email',
                "required":"false"
            }),
        }

class LeadContactNameForm(forms.ModelForm):
    class Meta:
        model = LeadContactNames
        fields = ['value']
        widgets = {
            'value': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Add contact name',
                "required":"false"
            }),
        }