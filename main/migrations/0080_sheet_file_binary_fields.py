from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0079_sheet_generated_mail_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='sheet',
            name='generated_mail_content',
            field=models.BinaryField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='sheet',
            name='input_file',
            field=models.BinaryField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='sheet',
            name='generated_file',
            field=models.BinaryField(null=True, blank=True),
        ),
    ]

