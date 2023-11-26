# Generated by Django 4.2.6 on 2023-11-24 23:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compose', '0011_alter_composing_png_result'),
    ]

    operations = [
        migrations.RenameField(
            model_name='article',
            old_name='number',
            new_name='article_number',
        ),
        migrations.RemoveField(
            model_name='article',
            name='cdn_url',
        ),
        migrations.AddField(
            model_name='article',
            name='render_url',
            field=models.CharField(default=None, max_length=250),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='article',
            name='tiff_url',
            field=models.CharField(default=None, max_length=250),
            preserve_default=False,
        ),
    ]
