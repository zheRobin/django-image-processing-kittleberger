from django.db import models
from accounts.models import User
import secrets

def generate_api_key():
    return 'ak_' + secrets.token_hex(16)
class Document(models.Model):
    file_id = models.CharField(max_length=100)
    upload_date = models.DateTimeField(auto_now_add=True)
class APIKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    apikey = models.CharField(max_length=100,default=generate_api_key,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.apikey