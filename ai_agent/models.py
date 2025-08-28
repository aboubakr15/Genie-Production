from django.db import models

################################################################################################################################
###################################### Global Database For multiple clients to enrich ##########################################
################################################################################################################################

class GlobalLead(models.Model):
    name = models.CharField(max_length=255, db_collation='utf8mb4_general_ci')
    primary_domain = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    employee_count = models.IntegerField(blank=True, null=True) 
    logo_url = models.URLField(max_length=500, blank=True, null=True)
    website_url = models.URLField(max_length=500, blank=True, null=True)
    linkedin_url = models.URLField(max_length=500, blank=True, null=True)
    twitter_url = models.URLField(max_length=500, blank=True, null=True)
    facebook_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.name}"
    
class GlobalLeadPhoneNumbers(models.Model):
    lead = models.ForeignKey(GlobalLead, on_delete=models.CASCADE)
    time_zone = models.CharField(max_length=30, blank=True, null=True)
    value = models.CharField(max_length=255)

    class Meta:
        unique_together = ('lead', 'value')

class GlobalLeadEmails(models.Model):
    lead = models.ForeignKey(GlobalLead, on_delete=models.CASCADE)
    value = models.CharField(max_length=255)
    
    class Meta:
        unique_together = ('lead', 'value')

class GlobalLeadContactNames(models.Model):
    lead = models.ForeignKey(GlobalLead, on_delete=models.CASCADE)
    value = models.CharField(max_length=255)

    class Meta:
        unique_together = ('lead', 'value')