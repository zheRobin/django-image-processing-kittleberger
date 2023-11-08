from django.contrib import admin
from .models import *
class ComposingTemplateAdmin(admin.ModelAdmin):
    list_display = [field.name for field in ComposingTemplate._meta.fields]
class ArticleTemplateAdmin(admin.ModelAdmin):
    list_display = [field.name for field in ComposingArticleTemplate._meta.fields]
class ComposingAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Composing._meta.fields]
admin.site.register(ComposingTemplate, ComposingTemplateAdmin)
admin.site.register(ComposingArticleTemplate, ArticleTemplateAdmin)
admin.site.register(Composing, ComposingAdmin)
admin.site.register([Brand,Application,Article,ComposingBlockList,Country])
