from rest_framework import serializers
from pymongo import MongoClient
from .models import *
from master.models import *
import environ, os
env = environ.Env()
environ.Env.read_env()
class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'
class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = '__all__'
class CountrySerializer(serializers.ModelSerializer):
    class Meta:
      model = Country
      fields = '__all__'
class ComposingArticleTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComposingArticleTemplate
        fields = '__all__'
class ComposingTemplateSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(many=True)
    application = ApplicationSerializer(many=True)
    article_placements = ComposingArticleTemplateSerializer(many=True)
    class Meta:
        model = ComposingTemplate
        fields = '__all__'
    def create(self, validated_data):
        brands_data = validated_data.pop('brand')
        template = ComposingTemplate.objects.create(**validated_data)
        for brand_data in brands_data:
            template.brand.add(brand_data)
        return template

class ArticleSerializer(serializers.ModelSerializer):
    render_url = serializers.SerializerMethodField()
    tiff_url = serializers.SerializerMethodField()
    class Meta:
        model = Article
        fields = '__all__'
    def get_render_url(self, obj):
        client = MongoClient(host=os.getenv('MONGO_DB_HOST'))
        db = client[os.getenv('MONGO_DB_NAME')]
        file_id = Document.objects.latest('id').file_id
        document = db[file_id].find_one({'id': obj.mediaobject_id})
        if document:
            cdn_urls = document.get('urls', {})
            return cdn_urls.get('jpeg') or cdn_urls.get('png')

    def get_tiff_url(self, obj):
        client = MongoClient(host=os.getenv('MONGO_DB_HOST'))
        db = client[os.getenv('MONGO_DB_NAME')]
        file_id = Document.objects.latest('id').file_id
        document = db[file_id].find_one({'id': obj.mediaobject_id})
        if document:
            cdn_urls = document.get('urls', {})
            return cdn_urls.get('tiff')
        
class ComposingSerializer(serializers.ModelSerializer):
    template = ComposingTemplateSerializer()
    articles = ArticleSerializer(many=True)
    class Meta:
        model = Composing
        fields = '__all__'


class ComposingBlockListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComposingBlockList
        fields = '__all__'