from django.db import models
from django.conf import settings
import os


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
    organization = models.ForeignKey(GlobalOrganization, on_delete=models.CASCADE, related_name='phone_numbers')
    value = models.CharField(max_length=255)
    time_zone = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        app_label = 'ai_agent'
        unique_together = ('organization', 'value')

    def __str__(self):
        return self.value

class GlobalEmails(models.Model):
    organization = models.ForeignKey(GlobalOrganization, on_delete=models.CASCADE, related_name='emails')
    value = models.CharField(max_length=255)

    class Meta:
        app_label = 'ai_agent'
        unique_together = ('organization', 'value')

    def __str__(self):
        return self.value

class GlobalContactNames(models.Model):
    organization = models.ForeignKey(GlobalOrganization, on_delete=models.CASCADE, related_name='contact_names')
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, null=True, blank=True)

    class Meta:
        app_label = 'ai_agent'
        unique_together = ('organization', 'name')

    def __str__(self):
        return self.name

class EnrichmentTask(models.Model):
    task_id = models.CharField(max_length=255, unique=True)
    excel_sheet_name = models.CharField(max_length=255, default='Enriched Leads')
    status = models.CharField(max_length=50, default='PENDING')
    progress = models.IntegerField(default=0)
    results = models.JSONField(null=True, blank=True)  # We'll keep this for potential small-scale data or metadata
    results_file_content = models.BinaryField(null=True, blank=True)  # To store the generated Excel file
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    request_count = models.IntegerField(default=0)
    company_count = models.IntegerField(default=0)
    total_chunks = models.IntegerField(default=0)
    chunks_completed = models.IntegerField(default=0)

    # Dynamically set owner to Django project name
    owner = models.CharField(max_length=255)

    # This FileField will no longer be used for storage, but can be kept for other metadata if needed
    results_file = models.FileField(upload_to='enrichment_results/', null=True, blank=True)
    is_result_downloaded = models.BooleanField(default=False)

    def __str__(self):
        return self.task_id
