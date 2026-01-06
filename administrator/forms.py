from django import forms
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

class UserUpdateForm(forms.ModelForm):
    new_password = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput,
        required=False,
        validators=[validate_password],
    )
    confirm_password = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput,
        required=False,
    )
    role = forms.ChoiceField(choices=[
        ('administrator', 'Administrator'),
        ('leads', 'Leads'),
        ('operations_team_leader', 'Operations Team Leader'),
        ('operations_manager', 'Operations Manager'),
        ('sales', 'Sales'),
        ('sales_team_leader', 'Sales Team Leader'),
        ('sales_manager', 'Sales Manager'),
    ])

    class Meta:
        model = User
        fields = ['username', 'role']

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and new_password != confirm_password:
            raise ValidationError("Passwords do not match")

        return cleaned_data


class UserCreationFormWithRole(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput,
        validators=[validate_password],
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput,
        validators=[validate_password],
    )
    role = forms.ChoiceField(choices=[
        ('administrator', 'Administrator'),
        ('leads', 'Leads'),
        ('operations_team_leader', 'Operations Team Leader'),
        ('operations_manager', 'Operations Manager'),
        ('sales', 'Sales'),
        ('sales_team_leader', 'Sales Team Leader'),
        ('sales_manager', 'Sales Manager'),
    ])

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2', 'role']

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match")

        return password2

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("Username already exists")
        return username
