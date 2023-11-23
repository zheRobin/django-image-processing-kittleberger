from django.core.management.base import BaseCommand
from accounts.models import User

class Command(BaseCommand):
    help = 'Create a new admin user'

    def handle(self, *args, **options):
        email = input('Email: ')
        password = input('Password: ')
        User.objects.create_user(email, password)