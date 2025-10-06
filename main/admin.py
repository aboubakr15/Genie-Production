from django.contrib import admin

from .models import *

# Register your models here.
admin.site.register(Sheet)
admin.site.register(Lead)
admin.site.register(LeadPhoneNumbers)
admin.site.register(LeadEmails)
admin.site.register(LeadContactNames)
admin.site.register(Acceptance)
admin.site.register(SalesShow)
admin.site.register(TerminationCode)
admin.site.register(LeadTerminationCode)
admin.site.register(Notification)
admin.site.register(UserLeader)
admin.site.register(Log)
admin.site.register(SalesTeams)
admin.site.register(FilterType)
admin.site.register(FilterWords)
admin.site.register(OldShow)
admin.site.register(LeadTerminationHistory)
admin.site.register(TaskLog)
admin.site.register(Credits)
admin.site.register(CreditHistory)