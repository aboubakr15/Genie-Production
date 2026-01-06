from django import forms
from django.contrib.auth.models import User, Group
from main.models import UserLeader

class AssignSalesToLeaderForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name='sales').exclude(id__in=UserLeader.objects.values('user')),
        label='Select User'
    )
    leader = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name='sales_team_leader'),
        label='Select Team Leader'
    )