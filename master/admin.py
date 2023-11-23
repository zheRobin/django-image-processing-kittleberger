from django.contrib import admin
from .models import *
class Admin(admin.ModelAdmin):
    list_display = [field.name for field in Document._meta.fields]
admin.site.register(Document, Admin)
admin.site.register(APIKey)
