# Generated by Django 4.2.6 on 2023-11-25 22:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compose', '0012_rename_number_article_article_number_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='article',
            name='render_url',
        ),
        migrations.RemoveField(
            model_name='article',
            name='tiff_url',
        ),
        migrations.AddField(
            model_name='article',
            name='mediaobject_id',
            field=models.CharField(default=None, max_length=50),
            preserve_default=False,
        ),
    ]
