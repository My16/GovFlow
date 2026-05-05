# Generated manually to add position field to UserProfile
from django.db import migrations, models


def create_missing_profiles(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('GovFlowApp', 'UserProfile')
    for user in User.objects.all():
        UserProfile.objects.get_or_create(user=user)


class Migration(migrations.Migration):

    dependencies = [
        ('GovFlowApp', '0006_alter_document_status_alter_documenthistory_action'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='position',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.RunPython(create_missing_profiles, reverse_code=migrations.RunPython.noop),
    ]
