# Generated by Django 4.1.12 on 2023-10-24 18:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuthTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.TextField(verbose_name='JWT Access Token')),
                ('session', models.TextField(verbose_name='Session Passed')),
                ('refresh_token', models.TextField(blank=True, verbose_name='JWT Refresh Token')),
                ('expires_at', models.DateTimeField(blank=True, null=True, verbose_name='Expires At')),
                ('create_date', models.DateTimeField(auto_now_add=True, verbose_name='Create Date/Time')),
                ('update_date', models.DateTimeField(auto_now=True, verbose_name='Date/Time Modified')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='accounts.user')),
            ],
        ),
    ]