# Generated by Django 4.2.6 on 2023-11-22 17:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0004_apikey_created_at_apikey_last_used_apikey_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='apikey',
            name='last_used',
            field=models.DateTimeField(null=True),
        ),
    ]
