from django.db import migrations

def create_termination_codes(apps, schema_editor):
    TerminationCodes = apps.get_model('main', 'TerminationCode')
    
    termination_codes = [
        ("CD", "Closed deal"),
        ("PR", "Prospect"),
        ("Show", "Moved in blacklist"),
        ("CB", "Call back"),
        ("FL", "Flag"),
        ("IC", "Incoming"),
        ("IP", "Info passed"),
        ("DNC", "Do not call"),
        ("VM", "Voice mail"),
    ]

    for code in termination_codes:
        # Use get_or_create to avoid duplicates
        TerminationCodes.objects.get_or_create(name=code[0], full_name=code[1])

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0032_alter_terminationcode_full_name'),  
    ]

    operations = [
        migrations.RunPython(create_termination_codes),
    ]
