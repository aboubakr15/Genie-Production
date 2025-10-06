from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


################################################################################################################################
###################################### Global Database For multiple clients to enrich ##########################################
################################################################################################################################

class GlobalOrganization(models.Model):
    
    class Meta:
        app_label = 'ai_agent'

    name = models.CharField(max_length=255, unique=True, db_index=True)
    primary_domain = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

class GlobalPhoneNumbers(models.Model):
        
    class Meta:
        app_label = 'ai_agent'
        
    organization = models.ForeignKey(GlobalOrganization, on_delete=models.CASCADE, related_name='phone_numbers')
    value = models.CharField(max_length=255)
    time_zone = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        unique_together = ('organization', 'value')

    def __str__(self):
        return self.value

class GlobalEmails(models.Model):
      
    class Meta:
        app_label = 'ai_agent'
        
    organization = models.ForeignKey(GlobalOrganization, on_delete=models.CASCADE, related_name='emails')
    value = models.CharField(max_length=255)

    class Meta:
        unique_together = ('organization', 'value')

    def __str__(self):
        return self.value

class GlobalContactNames(models.Model):
         
    class Meta:
        app_label = 'ai_agent'
        
    organization = models.ForeignKey(GlobalOrganization, on_delete=models.CASCADE, related_name='contact_names')
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('organization', 'name')

    def __str__(self):
        return self.value
