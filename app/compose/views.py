from django.db.models import Count, Q
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import uuid
from .models import *
from .serializers import *
from rest_framework.pagination import LimitOffsetPagination
from django.core.exceptions import ValidationError
from rest_framework.exceptions import NotFound
from django.shortcuts import get_object_or_404
from app.util import *
from master.util import *
import json
import environ
env = environ.Env()
environ.Env.read_env()

# Create your views here.


class TemplateAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    def post(self, request):
        try:
            data=request.POST.dict()
            preview_image = request.FILES['preview_image']
            background_image = request.FILES['background_image']
            preview_image_cdn_url = '/mediafils/preview_images' + f"{str(uuid.uuid4())}_{preview_image.name}"
            bg_image_cdn_url = '/mediafils/background_images' + f"{str(uuid.uuid4())}_{background_image.name}"
            preview_image_cdn_url = s3_upload(self,preview_image, preview_image_cdn_url)
            bg_image_cdn_url = save_img(self,background_image, (int(data['resolution_width']),int(data['resolution_height'])),data['type'],bg_image_cdn_url)
            data['is_shadow'] = json.loads(data['is_shadow'].lower())
            brands, applications, article_placements = [], [], []
            for brand in list(map(int, data['brands'].split(','))):
                brand_obj = Brand.objects.get(id=brand)
                brands.append(brand_obj.pk)
            for app in list(map(int, data['applications'].split(','))):
                app_obj = Application.objects.get(id=app)
                applications.append(app_obj.pk)
            for placement in json.loads(data['article_placements']):
                placement_obj = ComposingArticleTemplate.objects.create( position_x = placement['position_x'], position_y = placement['position_y'], height = placement['height'], width = placement['width'], z_index = placement['z_index'],  created_by_id = request.user.pk, modified_by_id = request.user.pk)
                article_placements.append(placement_obj.pk)
            template = ComposingTemplate.objects.create(name = data['name'], is_shadow = data['is_shadow'],resolution_width = data['resolution_width'], file_type = data['type'],resolution_height=data['resolution_height'], created_by_id = request.user.pk, modified_by_id = request.user.pk, preview_image_cdn_url = preview_image_cdn_url, bg_image_cdn_url = bg_image_cdn_url)
            template.brand.set(brands)
            template.application.set(applications)
            template.article_placements.set(article_placements)
            serializer = ComposingTemplateSerializer(template)
            return Response(created(self, serializer.data))
        except KeyError as e:
            return Response(error(self, "All field are required: {}".format(str(e))))
        except Exception as e:
            return Response(error(self, str(e)))
    def put(self, request, pk):
        try:
            data = request.data
            template = ComposingTemplate.objects.get(pk=pk)

            if 'preview_image' in request.FILES:
                preview_image = request.FILES['preview_image']
                preview_image_cdn_url = '/mediafils/preview_images' + f"{str(uuid.uuid4())}_{preview_image.name}"
                template.preview_image_cdn_url = s3_upload(self, preview_image, preview_image_cdn_url)

            if 'background_image' in request.FILES:
                background_image = request.FILES['background_image']
                bg_image_cdn_url = '/mediafils/background_images' + f"{str(uuid.uuid4())}_{background_image.name}"
                template.bg_image_cdn_url = save_img(self, background_image, (int(data['resolution_width']),int(data['resolution_height'])),data['type'],bg_image_cdn_url)

            if 'is_shadow' in data:
                template.is_shadow = json.loads(data['is_shadow'].lower())

            brand_ids, app_ids, placements_ids = [], [], []
            if 'brands' in data:
                for brand in list(map(int, data['brands'].split(','))):
                    brand_obj = Brand.objects.get(id=brand)
                    brand_ids.append(brand_obj.pk)
                template.brand.set(brand_ids)

            if 'applications' in data:
                for app in list(map(int, data['applications'].split(','))):
                    app_obj = Application.objects.get(id=app)
                    app_ids.append(app_obj.pk)
                template.application.set(app_ids)

            if 'article_placements' in data:
                for placement in json.loads(data['article_placements']):
                    placement_obj = ComposingArticleTemplate.objects.create(position_x=placement['position_x'], position_y=placement['position_y'], height= placement['height'], width= placement['width'], z_index = placement['z_index'],  created_by_id=request.user.pk, modified_by_id=request.user.pk)
                    placements_ids.append(placement_obj.pk)
                template.article_placements.set(placements_ids)

            template.save()

            serializer = ComposingTemplateSerializer(template)
            return Response(created(self, serializer.data))
        except ComposingTemplate.DoesNotExist:
            return Response(error(self, "The playlist does not exist"))
        except Brand.DoesNotExist:
            return Response(error(self, "The brand does not exist"))
        except Application.DoesNotExist:
            return Response(error(self, "The applications does not exist"))
        except Exception as e:
            return Response(error(self, str(e)))
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
        def event_stream():
            chunk = []
            for template in serializer.data:
                if template:
                    chunk.append(template)
                    if len(chunk) == 10:
                        yield json.dumps(chunk) + '\n\n'
                        chunk.clear()
            if chunk:
                yield json.dumps(chunk) + '\n\n'
                chunk.clear()
        return StreamingHttpResponse(event_stream(), content_type='text/event-stream')
class ComposingTemplateDetail(APIView):
    def get(self, request, pk):
        template = get_object_or_404(ComposingTemplate, pk=pk)
        serializer = ComposingTemplateSerializer(template)
        return Response(serializer.data)

class ComposingTemplateFilter(APIView):
    def post(self, request, format=None):
        try:
            limit = int(request.data.get('limit', 10))
            offset = int(request.data.get('offset', 0))
        except ValueError:
            return Response(error(self, 'Invalid limit/offset.'))
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
        templates = ComposingTemplate.objects.all().order_by('id')
        if brands:
            templates = templates.filter(brand__pk__in=brands).distinct()

        if applications:
            templates = templates.filter(application__pk__in=applications).distinct()
        templates = templates.annotate(count=Count('article_placements')).filter(article_filter)
        paginator = LimitOffsetPagination()
        paginator.default_limit = limit
        paginator.offset = offset
        context = paginator.paginate_queryset(templates, request)
        products = Composing.objects.filter(template__in=context)
        template_serializer = ComposingTemplateSerializer(context, many=True)
        product_serializer = ComposingSerializer(products, many=True)
        result = {
            "templates":template_serializer.data,
            "products":product_serializer.data
        }  
        return paginator.get_paginated_response(result)
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

class CountryAPIView(APIView):
    def get(self, request):
        countries = Country.objects.all()
        serializer = CountrySerializer(countries, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CountrySerializer(data=request.data)
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
