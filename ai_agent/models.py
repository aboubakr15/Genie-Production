from django.db import models

################################################################################################################################
###################################### Global Database For multiple clients to enrich ##########################################
################################################################################################################################

class GlobalOrganization(models.Model):
    apollo_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    website_url = models.URLField(blank=True, null=True)
    angellist_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    alexa_ranking = models.IntegerField(blank=True, null=True)
    linkedin_uid = models.CharField(max_length=255, blank=True, null=True)
    founded_year = models.IntegerField(blank=True, null=True)
    logo_url = models.URLField(blank=True, null=True)
    crunchbase_url = models.URLField(blank=True, null=True)
    primary_domain = models.CharField(max_length=255, blank=True, null=True)
    sanitized_phone = models.CharField(max_length=255, blank=True, null=True)
    owned_by_organization_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

class GlobalPhoneNumbers(models.Model):
    organization = models.ForeignKey(GlobalOrganization, on_delete=models.CASCADE, related_name='phone_numbers')
    value = models.CharField(max_length=255)
    time_zone = models.CharField(max_length=30, blank=True, null=True)
    source = models.CharField(max_length=50, blank=True, null=True)  # e.g., 'Scraped', 'Owler'
    sanitized_number = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('organization', 'value')

    def __str__(self):
        return self.value

class GlobalEmails(models.Model):
    organization = models.ForeignKey(GlobalOrganization, on_delete=models.CASCADE, related_name='emails')
    value = models.CharField(max_length=255)

    class Meta:
        unique_together = ('organization', 'value')

    def __str__(self):
        return self.value

class GlobalContactNames(models.Model):
    organization = models.ForeignKey(GlobalOrganization, on_delete=models.CASCADE, related_name='contact_names')
    value = models.CharField(max_length=255)

    class Meta:
        unique_together = ('organization', 'value')

    def __str__(self):
        return self.value