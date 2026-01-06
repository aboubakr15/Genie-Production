from django import forms
from main.models import Sheet

class AutoFillForm(forms.Form):
    file = forms.FileField(
        required=True, 
        label="Choose a file",
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'id': 'file'
        })
    )
    latest_sheet = forms.ModelChoiceField(
        queryset=Sheet.objects.all(), 
        required=False, 
        label="Select a Latest Sheet",
        widget=forms.Select(attrs={'class': 'form-select'})
    ) 

class UploadSheetsForm(forms.Form):
        file = forms.FileField(
            widget=forms.ClearableFileInput(attrs={
                'class': 'form-control-file',  # Bootstrap class for file input
                'id': 'fileInput'
            })
        )