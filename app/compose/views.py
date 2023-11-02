from django.db.models import Count, Q
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import uuid
from .models import *
from .serializers import *
from django.core.exceptions import ValidationError
from rest_framework.exceptions import NotFound
from django.shortcuts import get_object_or_404
from app.util import *
from compose.util import *
import environ
env = environ.Env()
environ.Env.read_env()

# Create your views here.


class TemplateAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    def post(self, request):
        try:
            preview_image = request.FILES['preview_image']
            background_image = request.FILES['background_image']            
            preview_image_cdn_url = '/mediafils/preview_images' + f"{str(uuid.uuid4())}_{preview_image.name}"
            bg_image_cdn_url = '/mediafils/background_images' + f"{str(uuid.uuid4())}_{background_image.name}"
            preview_image_cdn_url = s3_upload(self,preview_image, preview_image_cdn_url)
            bg_image_cdn_url = s3_upload(self,background_image, bg_image_cdn_url)
            data=request.POST.dict()
            brands, applications, article_placements = [], [], []
            for brand in data['brand']:
                brand_obj = Brand.objects.get(name=brand)
                brands.append(brand_obj.pk)
            for app in data['application']:
                app_obj = Application.objects.get(name=app)
                applications.append(app_obj.pk)
            for placement in data['article_placements']:
                placement_obj = ComposingArticleTemplate.objects.create(pos_index=placement['pos_index'], position_x = placement['position_x'], position_y = placement['position_y'], height = placement['height'], width = placement['width'], z_index = placement['z_index'],  created_by_id = request.user.pk, modified_by_id = request.user.pk)
                article_placements.append(placement_obj.pk)
            template = ComposingTemplate.objects.create(name = data['name'], is_shadow = data['is_shadow'],resolution_width = data['resolution_width'], resolution_height=data['resolution_height'], created_by_id = request.user.pk, modified_by_id = request.user.pk, preview_image_cdn_url = preview_image_cdn_url, bg_image_cdn_url = bg_image_cdn_url)
            template.brand.set(brands)
            template.application.set(applications)
            template.article_placements.set(article_placements)
            serializer = ComposingTemplateSerializer(template)
            if serializer.is_valid():
                return Response(created(self, serializer.data))
            return Response(error(self, serializer.errors))
        except KeyError as e:
            return Response(error(self, "All field are required: {}".format(str(e))))
        except Exception as e:
            return Response(error(self, str(e)))
    def put(self, request):
        template_pk = request.POST.get('pk')
        template = get_object_or_404(ComposingTemplate, pk=template_pk)        
        preview_image = request.FILES.get('preview_image')
        background_image = request.FILES.get('background_image')
        if preview_image:
            preview_image_cdn_url = '/mediafils/preview_images' + f"{str(uuid.uuid4())}_{preview_image.name}"
            preview_image_cdn_url = s3_upload(self,preview_image, preview_image_cdn_url)
            template.preview_image_cdn_url = preview_image_cdn_url
        if background_image:
            bg_image_cdn_url = '/mediafils/background_images' + f"{str(uuid.uuid4())}_{background_image.name}"
            bg_image_cdn_url = s3_upload(self,background_image, bg_image_cdn_url)
            template.bg_image_cdn_url = bg_image_cdn_url
        data = request.POST.dict()
        template.name = data.get('name', template.name)
        template.resolution_width = data.get('resolution_width', template.resolution_width)
        template.resolution_height = data.get('resolution_height', template.resolution_height)
        template.is_shadow = data.get('is_shadow', template.is_shadow)
        template.resolution_dpi = data.get('resolution_dpi', template.resolution_dpi)
        template.file_type = data.get('file_type', template.file_type)
        template.modified_by_id = request.user.pk

        try:
            template.save()
        except Exception as e:
            return Response(error(self, str(e)), status=500)

        serializer = ComposingTemplateSerializer(template)

        return Response(serializer.data, status=200)
    def delete(self, request):
        template_pk = request.POST.get('pk')
        template = ComposingTemplate.objects.get(pk=template_pk)
        if template:
            template.is_deleted = True
            template.modified_by_id = request.user.pk
            template.save()

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(status=status.HTTP_404_NOT_FOUND)
    def get(self, request, format=None):
        templates = ComposingTemplate.objects.all()
        serializer = ComposingTemplateSerializer(templates, many=True)
        return StreamingHttpResponse(event_stream(serializer.data), content_type="text/event-stream")
class ComposingTemplateDetail(APIView):
    def get(self, request, pk):
        template = get_object_or_404(ComposingTemplate, pk=pk)
        serializer = ComposingTemplateSerializer(template)
        return Response(serializer.data)

class ComposingTemplateFilter(APIView):
    def post(self, request, format=None):
        brands = request.data.get('brand', [])
        applications = request.data.get('application', [])
        article_numbers = request.data.get('article_number', [])
        article_filter = Q()
        for number in article_numbers:
            if '+' in number:
                number = int(number.replace('+', ''))
                article_filter |= Q(count__gte=number)
            else:
                number = int(number)
                article_filter |= Q(count=number)
        templates = ComposingTemplate.objects.all()
        if brands:
            templates = templates.filter(brand__pk__in=brands).distinct()

        if applications:
            templates = templates.filter(application__pk__in=applications).distinct()
        templates = templates.annotate(count=Count('article_placements')).filter(article_filter)

        serializer = ComposingTemplateSerializer(templates, many=True)

        return Response(data=serializer.data, status=status.HTTP_200_OK)
class ComposingArticleTemplateList(APIView):
    def get(self, request):
        articles = ComposingArticleTemplate.objects.all()
        serializer = ComposingArticleTemplateSerializer(articles, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ComposingArticleTemplateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ComposingAPIView(APIView):
    def get(self, request):
        products = Composing.objects.all()
        serializer = ComposingSerializer(products, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        data = request.data
        data['created_by_id'] = request.user.id
        data['modified_by_id'] = request.user.id
        articles_data = data.get('articles', [])
        articles = []
        for article_data in articles_data:
            article_data['created_by_id'] = request.user.id
            article_data['modified_by_id'] = request.user.id
            try:
                article = Article.objects.create(**article_data)
                articles.append(article.pk)
            except Exception as e:
                return Response(error(self, str(e)))
        try:
            composing = Composing.objects.create(name = data['name'],template_id = data['template_id'], created_by_id = request.user.id, modified_by_id = request.user.id)
            composing.articles.set(articles)
        except Exception as e:
            return Response(error(self, str(e)))
        serializer = ComposingSerializer(composing)
        return Response(created(self, serializer.data))
class ComposingArticleTemplateDetail(APIView):
    def get_object(self, pk):
        try:
            return ComposingArticleTemplate.objects.get(pk=pk)
        except ComposingArticleTemplate.DoesNotExist as e:
            raise e

    def get(self, request, pk):
        template = self.get_object(pk)
        serializer = ComposingArticleTemplateSerializer(template)
        return Response(serializer.data)

    def put(self, request, pk):
        template = self.get_object(pk)
        serializer = ComposingArticleTemplateSerializer(
            template, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        template = self.get_object(pk)
        template.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ComposingDetail(APIView):
    def get_object(self, pk):
        try:
            return Composing.objects.get(pk=pk)
        except Composing.DoesNotExist as e:
            raise e

    def get(self, request, pk):
        template = self.get_object(pk)
        serializer = ComposingSerializer(template)
        return Response(serializer.data)

    def put(self, request, pk):
        template = self.get_object(pk)
        serializer = ComposingSerializer(template, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        template = self.get_object(pk)
        template.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class BrandAPIView(APIView):
    def get(self, request):
        brands = Brand.objects.all()
        serializer = BrandSerializer(brands, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BrandSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ApplicationAPIView(APIView):
    def get(self, request):
        applications = Application.objects.all()
        serializer = ApplicationSerializer(applications, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ApplicationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ArticleAPIView(APIView):
    def get(self, request):
        articles = Article.objects.all()
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ArticleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
