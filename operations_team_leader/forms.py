from django import forms
from django.forms import inlineformset_factory
from main.models import Sheet, Lead, LeadPhoneNumbers, LeadEmails, LeadContactNames
from django.contrib.auth.models import User
from main.models import UserLeader

LeadPhoneNumbersFormSet = inlineformset_factory(
    Lead, LeadPhoneNumbers, fields=('value',), extra=1, can_delete=True
)

LeadEmailsFormSet = inlineformset_factory(
    Lead, LeadEmails, fields=('value',), extra=1, can_delete=True
)

LeadContactNamesFormSet = inlineformset_factory(
    Lead, LeadContactNames, fields=('value',), extra=1, can_delete=True
)


class AssignLeadsToLeaderForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name='leads').exclude(id__in=UserLeader.objects.values('user')),
        label='Select User'
    )
    leader = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name='operations_team_leader'),
        label='Select Team Leader'
    )

