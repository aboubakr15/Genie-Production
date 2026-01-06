from django.db import migrations

def forwards_func(apps, schema_editor):
    Lead = apps.get_model('main', 'Lead')
    LeadPhoneNumbers = apps.get_model('main', 'LeadPhoneNumbers')
    for lead in Lead.objects.all():
        if lead.time_zone:  # Only copy if there's data
            LeadPhoneNumbers.objects.filter(lead=lead, sheet=lead.sheets.last()).update(time_zone=lead.time_zone)

def reverse_func(apps, schema_editor):
    # Optional: Reverse by copying back (if needed for rollback)
    Lead = apps.get_model('main', 'Lead')
    LeadPhoneNumbers = apps.get_model('main', 'LeadPhoneNumbers')
    for lead in Lead.objects.all():
        first_phone = LeadPhoneNumbers.objects.filter(lead=lead).first()
        if first_phone:
            lead.time_zone = first_phone.time_zone
            lead.save()

class Migration(migrations.Migration):
    dependencies = [
        ('main', '0071_add_time_zone_to_leadphonenumbers'),  # Replace with the actual previous migration name
    ]
    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
