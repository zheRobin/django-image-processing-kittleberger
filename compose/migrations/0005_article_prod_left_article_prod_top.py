# Generated by Django 4.2.6 on 2023-11-12 21:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compose', '0004_alter_composingtemplate_file_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='prod_left',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='article',
            name='prod_top',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]