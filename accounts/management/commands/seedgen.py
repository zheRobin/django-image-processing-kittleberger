from django.core.management.base import BaseCommand
from accounts.models import User
from compose.models import *
class Command(BaseCommand):

    def handle(self, *args, **options):
        if not User.objects.filter(username="admin").exists() and not User.objects.filter(username="superadmin").exists():
            User.objects.create_superuser(
                username="superadmin",
                email="superuser@email.com",
                password="superuser123"
            )
            User.objects.create_admin(
                username="admin",
                email="admin@email.com",
                password="adminuser123"
            )

            brands = ["Bosch", "Buderus"]
            applications = ["Print", "eShop", "WebSite"]
            countries = [
                "Deutschland", "Frankreich", "Italien", "Schweiz", "USA", "Vereinigte Staaten",
                "England", "Irland", "Polen", "Portugal", "Spanien", "Tschechische Republik",
                "Ungarn", "Österreich", "Belgien", "Kanada", "Mexiko", "Niederlande",
                "Schweden", "Südafrika"
            ]

            for brand in brands:
                Brand.objects.create(name=brand)

            for application in applications:
                Application.objects.create(name=application)

            for country in countries:
                Country.objects.create(name=country)
