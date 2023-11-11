from django.db import models
import uuid
from accounts.models import User

class Brand(models.Model):
    name = models.CharField(max_length=50, unique=True)
    index = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    def __str__(self):
        return self.name
class Application(models.Model):
    name = models.CharField(max_length=50, unique=True)
    index = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    def __str__(self):
        return self.name
class Country(models.Model):
    index = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=50, unique=True)
    def __str__(self):
        return self.name
class ComposingArticleTemplate(models.Model):
    position_x = models.IntegerField()
    position_y = models.IntegerField()
    height = models.IntegerField()
    width = models.IntegerField()
    z_index = models.IntegerField()
    created_by = models.ForeignKey(User, related_name='article_template_created', on_delete=models.CASCADE)
    modified_by = models.ForeignKey(User, related_name='article_template_modified', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

class ComposingTemplate(models.Model):
    name = models.CharField(max_length=255)
    slug = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    brand = models.ManyToManyField(Brand)
    application = models.ManyToManyField(Application)
    is_shadow = models.BooleanField(default=False)
    resolution_width = models.IntegerField(default=800)
    resolution_height = models.IntegerField(default=600)
    resolution_dpi = models.IntegerField(default=72)
    bg_image_cdn_url = models.CharField(max_length=255)
    preview_image_cdn_url = models.CharField(max_length=255)
    article_placements = models.ManyToManyField(ComposingArticleTemplate, related_name='articles')
    file_type = models.CharField(max_length=10, default='JPEG')
    created_by = models.ForeignKey(User, related_name='template_created', on_delete=models.CASCADE)
    modified_by = models.ForeignKey(User, related_name='template_modified', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

class Article(models.Model):
    name = models.CharField(max_length=255)
    number = models.CharField(max_length=50)
    cdn_url = models.CharField(max_length=255)
    transparent_cdn_url = models.CharField(max_length=255)
    scaling = models.IntegerField()
    alignment = models.CharField(max_length=20, default='center')
    height = models.IntegerField()
    width = models.IntegerField()
    z_index = models.IntegerField()
    created_by = models.ForeignKey(User, related_name='article_placement_created', on_delete=models.CASCADE)
    modified_by = models.ForeignKey(User, related_name='article_placement_modified', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

class Composing(models.Model):
    name = models.CharField(max_length=255)
    slug = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    template = models.ForeignKey(ComposingTemplate, related_name='template', on_delete=models.CASCADE)
    articles = models.ManyToManyField(Article, related_name='articles')
    created_by = models.ForeignKey(User, related_name='composings_created', on_delete=models.CASCADE)
    modified_by = models.ForeignKey(User, related_name='composings_modified', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

class ComposingBlockList(models.Model):
    composing_template = models.ManyToManyField(ComposingTemplate)
    composing = models.ManyToManyField(Composing)
    created_by = models.ForeignKey(User, related_name='blocks_created', on_delete=models.CASCADE)
    modified_by = models.ForeignKey(User, related_name='blocks_modified', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)