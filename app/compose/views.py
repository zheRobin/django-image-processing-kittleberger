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
            if 'preview_image' in request.FILES:
                preview_image = request.FILES['preview_image']
                preview_image_cdn_url = 'mediafiles/preview_images' + f"{str(uuid.uuid4())}_{preview_image.name}"
                preview_image_cdn_url = s3_upload(preview_image, preview_image_cdn_url)
            else:
                preview_image_cdn_url = ""
            background_image = request.FILES['background_image']
            bg_image_cdn_url = 'mediafiles/background_images' + f"{str(uuid.uuid4())}_{background_image.name}"
            resolution_dpi_mapping = {"PNG": 72, "JPEG": 72, "TIFF": 300}
            resolution_dpi = resolution_dpi_mapping.get(data['type'], 72)
            bg_image_cdn_url = resize_save_img(background_image, (int(data['resolution_width']),int(data['resolution_height'])),data['type'],bg_image_cdn_url,resolution_dpi)
            data['is_shadow'] = json.loads(data['is_shadow'].lower())
            brands, applications, article_placements = [], [], []
            pos_index = 0
            for brand in list(map(int, data['brands'].split(','))):
                brand_obj = Brand.objects.get(id=brand)
                brands.append(brand_obj.pk)
            for app in list(map(int, data['applications'].split(','))):
                app_obj = Application.objects.get(id=app)
                applications.append(app_obj.pk)
            for placement in json.loads(data['article_placements']):
                pos_index += 1
                placement_obj = ComposingArticleTemplate.objects.create(pos_index = pos_index, position_x = placement['position_x'], position_y = placement['position_y'], height = placement['height'], width = placement['width'], z_index = placement['z_index'],  created_by_id = request.user.pk, modified_by_id = request.user.pk)
                article_placements.append(placement_obj.pk)
            template = ComposingTemplate.objects.create(name = data['name'], is_shadow = data['is_shadow'],resolution_width = data['resolution_width'],resolution_dpi = resolution_dpi, file_type = data['type'],resolution_height=data['resolution_height'], created_by_id = request.user.pk, modified_by_id = request.user.pk, preview_image_cdn_url = preview_image_cdn_url, bg_image_cdn_url = bg_image_cdn_url)
            template.brand.set(brands)
            template.application.set(applications)
            template.article_placements.set(article_placements)
            serializer = ComposingTemplateSerializer(template)
            return Response(created(self, serializer.data))
        except KeyError as e:
            print(str(e))
            return Response(error( "All field are required: {}".format(str(e))))
        except Exception as e:
            print(str(e))

            return Response(error( str(e)))
    def put(self, request, pk):
        try:
            data = request.data
            template = ComposingTemplate.objects.get(pk=pk)
            resolution_dpi_mapping = {"PNG": 72, "JPEG": 72, "TIFF": 300}
            if 'name' in data:
                template.name = data['name']
            if 'type' in data:
                template.file_type = data['type']
                resolution_dpi = resolution_dpi_mapping.get(data['type'], 72)
                template.resolution_dpi = resolution_dpi

            if 'preview_image' in request.FILES:
                preview_image = request.FILES['preview_image']
                preview_image_cdn_url = 'mediafiles/preview_images' + f"{str(uuid.uuid4())}_{preview_image.name}"
                template.preview_image_cdn_url = s3_upload(preview_image, preview_image_cdn_url)

            if 'background_image' in request.FILES:
                background_image = request.FILES['background_image']
                bg_image_cdn_url = 'mediafiles/background_images' + f"{str(uuid.uuid4())}_{background_image.name}"
                template.bg_image_cdn_url = resize_save_img(background_image, (int(data['resolution_width']),int(data['resolution_height'])),data['type'],bg_image_cdn_url,resolution_dpi_mapping.get(data['type'], 72))

            if 'is_shadow' in data:
                template.is_shadow = json.loads(data['is_shadow'].lower())

            brand_ids, app_ids, placements_ids = [], [], []
            if 'brands' in data:
                for brand in data['brands'].split(','):
                    if brand.isdigit():
                        brand_obj = Brand.objects.get(id=int(brand))
                        brand_ids.append(brand_obj.pk)
                template.brand.set(brand_ids)

            if 'applications' in data:
                for app in data['applications'].split(','):
                    if app.isdigit():
                        app_obj = Application.objects.get(id=int(app))
                        app_ids.append(app_obj.pk)
                template.application.set(app_ids)

            if 'article_placements' in data:
                for placement in json.loads(data['article_placements']):
                    if 'id' in placement and ComposingArticleTemplate.objects.filter(id=placement['id']).exists():
                        placement_obj = ComposingArticleTemplate.objects.get(id=placement['id'])
                        placement_obj.pos_index = placement['pos_index']
                        placement_obj.position_x = placement['position_x']
                        placement_obj.position_y = placement['position_y']
                        placement_obj.height = placement['height']
                        placement_obj.width = placement['width']
                        placement_obj.z_index = placement['z_index']
                        placement_obj.modified_by_id = request.user.pk
                        placement_obj.save()
                    else:
                        placement_obj = ComposingArticleTemplate.objects.create(pos_index = placement['pos_index'],position_x=placement['position_x'], position_y=placement['position_y'], height= placement['height'], width= placement['width'], z_index = placement['z_index'],  created_by_id=request.user.pk, modified_by_id=request.user.pk)
                    placements_ids.append(placement_obj.pk)
                template.article_placements.set(placements_ids)

            template.save()

            serializer = ComposingTemplateSerializer(template)
            return Response(created(self, serializer.data))
        except ComposingTemplate.DoesNotExist:
            return Response(error( "The playlist does not exist"))
        except Brand.DoesNotExist:
            return Response(error( "The brand does not exist"))
        except Application.DoesNotExist:
            return Response(error( "The applications does not exist"))
        except Exception as e:
            return Response(error( str(e)))
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
            return Response(error( 'Invalid limit/offset.'))
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
        if 'base64_img' in data and ',' in data['base64_img']:
            product = save_product_image(data['base64_img'])
        else:
            return Response(error("Invalid or missing base64_img"))

        articles_data = data.get('articles', [])
        articles = []
        for article_data in articles_data:
            article_data['created_by_id'] = request.user.id
            article_data['modified_by_id'] = request.user.id
            try:
                article = Article.objects.create(**article_data)
                articles.append(article.pk)
            except Exception as e:
                return Response(error(str(e)))
        try:
            composing = Composing.objects.create(name = data['name'], template_id = data['template_id'], cdn_url = product, created_by_id = request.user.id, modified_by_id = request.user.id)
            composing.articles.set(articles)
        except Exception as e:
            return Response(error(str(e)))
        
        return Response(created(self, product))
    def put(self, request, format=None):
        data = request.data
        data['modified_by_id'] = request.user.id

        if 'base64_img' in data and ',' in data['base64_img']:
            product = save_product_image(data['base64_img'])
        else:
            return Response(error("Invalid or missing base64_img"))
        
        articles_data = data.get('articles', [])
        articles = []
        for article_data in articles_data:
            article_data['modified_by_id'] = request.user.id
            try:
                article, created = Article.objects.update_or_create(
                    id=article_data['id'], defaults=article_data)
                articles.append(article.pk)
            except Article.DoesNotExist:
                return Response(error('Article with id does not exist.'))
            except Exception as e:
                return Response(error(str(e)))
        
        try:
            composing, created = Composing.objects.update_or_create(
                id=data['id'], 
                defaults ={
                    'name' : data.get('name', composing.name),
                    'template_id' : data.get('template_id', composing.template_id),
                    'cdn_url' : product,
                    'modified_by_id' : request.user.id
                }) 

            composing.articles.set(articles)
        except Composing.DoesNotExist:
            return Response(error('Composing with id does not exist.'))
        except Exception as e:
            return Response(error(str(e)))
        
        return Response(updated(self, product))  
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
