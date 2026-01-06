
from django import forms
from main.models import PriceRequest
from django.contrib.auth.models import User, Group
from main.models import UserLeader

class AssignLeadsToLeaderForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name='leads').exclude(id__in=UserLeader.objects.values('user')),
        label='Select User'
    )
    leader = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name='operations_team_leader'),
        label='Select Team Leader'
    )

class PriceRequestForm(forms.ModelForm):
    class Meta:
        model = PriceRequest
        fields = ['lead', 'show', 'options', 'status', 'num_rooms', 'num_nights', 'notes', 'email_status', 'lead_status']