from django.db.models import Count, Q
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import *
from .serializers import *
from rest_framework.pagination import LimitOffsetPagination
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from app.util import *
from master.util import *
from master.models import *
from functools import reduce
from operator import and_
import json

# Create your views here.

class SetPreviewImageAPIView(APIView):
    permission_classes = (IsAuthenticated,IsAdminUser)
    def post(self, request, format = None):
        data = request.data
        template_id = data.get('template_id', None)
        if not template_id:
            return Response(error("Template id is required"))
        try:
            template = ComposingTemplate.objects.get(pk=template_id)
        except ComposingTemplate.DoesNotExist:
            return Response(error("Template does not exist"))
        preview_img = data.get('preview_img', None)
        if not preview_img:
            return Response(error("Image Content is required"))
        if preview_img.startswith('http'):
            template.preview_image_cdn_url = preview_img
            template.save()
        elif preview_img.startswith('data:image'):
            result = save_preview_image(preview_img)
            template.preview_image_cdn_url = result
            template.save()
        else:
            return Response(error("Image Content is invalid"))
        return Response(success(template.preview_image_cdn_url))
class TemplateAPIView(APIView):
    permission_classes = (IsAuthenticated,IsAdminUser)
    def post(self, request):
        try:
            data=request.POST.dict()
            if int(data['resolution_width'])*int(data['resolution_height'])>=10000000:
                return Response(error("Image resolution must be under 10M pixel"))            
            resolution_dpi_mapping = {"PNG": 72, "JPEG": 72, "TIFF": 300}
            resolution_dpi = resolution_dpi_mapping.get(data['type'], 72)
            if 'preview_image' in request.FILES:
                preview_image = request.FILES['preview_image']
                preview_image_cdn_url = resize_save_img(preview_image, (400,int(400*int(data['resolution_height'])/int(data['resolution_width']))),'JPEG','mediafiles/preview_images/',72)
            else:
                preview_image_cdn_url = ""
            background_image = request.FILES['background_image']
            bg_image_tiff_url = ''
            bg_image_cdn_url = resize_save_img(background_image, (int(data['resolution_width']),int(data['resolution_height'])),'PNG','mediafiles/background_images/',72)
            data['is_shadow'] = json.loads(data['is_shadow'].lower())
            brands, applications, article_placements = [], [], []
            pos_index = 0
            if data.get('brands'):
                for brand in list(map(int, data['brands'].split(','))):
                    if brand:
                        brand_obj = Brand.objects.get(id=brand)
                        brands.append(brand_obj.pk)

            if data.get('applications'):
                for app in list(map(int, data['applications'].split(','))):
                    if app:
                        app_obj = Application.objects.get(id=app)
                        applications.append(app_obj.pk)
            for placement in json.loads(data['article_placements']):
                pos_index += 1
                if data.get('z_index') != "":
                    z_index = data.get('z_index', 0)
                if int(placement['width']) == 0 or int(placement['height']) == 0:
                    return Response(error("Not allowed 0 value for width or height!"))
                placement_obj = ComposingArticleTemplate.objects.create(pos_index = pos_index, position_x = placement['position_x'], position_y = placement['position_y'], height = placement['height'], width = placement['width'], z_index = z_index,  created_by_id = request.user.pk, modified_by_id = request.user.pk)
                article_placements.append(placement_obj.pk)
            template = ComposingTemplate.objects.create(name = data['name'], is_shadow = data['is_shadow'],resolution_width = data['resolution_width'],resolution_dpi = resolution_dpi, file_type = data['type'],resolution_height=data['resolution_height'], created_by_id = request.user.pk, modified_by_id = request.user.pk, preview_image_cdn_url = preview_image_cdn_url, bg_image_cdn_url = bg_image_cdn_url, bg_image_tiff_url = bg_image_tiff_url)
            template.brand.set(brands)
            template.application.set(applications)
            template.article_placements.set(article_placements)
            serializer = ComposingTemplateSerializer(template)
            return Response(created(self, serializer.data))
        except KeyError as e:
            return Response(error( "All field are required: {}".format(str(e))))
        except Exception as e:

            return Response(error( str(e)))
    def put(self, request, pk):
        try:
            data = request.data
            if int(data['resolution_width'])*int(data['resolution_height'])>=10000000:
                return Response(error("Image resolution must be under 10M pixel"))
            template = ComposingTemplate.objects.get(pk=pk)
            resolution_dpi_mapping = {"PNG": 72, "JPEG": 72, "TIFF": 300}
            resolution_dpi = template.resolution_dpi
            if 'name' in data:
                template.name = data['name']
            if 'type' in data:
                template.file_type = data['type']
                resolution_dpi = resolution_dpi_mapping.get(data['type'], 72)
                template.resolution_dpi = resolution_dpi
            if 'is_deleted' in data and json.loads(data['is_deleted'].lower()) == True:
                template.preview_image_cdn_url = ""
            if 'preview_image' in request.FILES:
                preview_image = request.FILES['preview_image']
                template.preview_image_cdn_url = resize_save_img(preview_image, (400,int(400*int(data['resolution_height'])/int(data['resolution_width']))),'JPEG','mediafiles/preview_images/',72)

            if 'background_image' in request.FILES:
                background_image = request.FILES['background_image']
                template.bg_image_cdn_url = resize_save_img(background_image, (int(data['resolution_width']),int(data['resolution_height'])),'PNG','mediafiles/background_images/',72)
            if 'resolution_width' in data and 'resolution_height' in data:
                if (template.resolution_width, template.resolution_height) != (int(data['resolution_width']), int(data['resolution_height'])):
                    template.resolution_width = data['resolution_width']
                    template.resolution_height = data['resolution_height']
                    template.bg_image_cdn_url = resize_save_img(template.bg_image_cdn_url, (template.resolution_width, template.resolution_height),'PNG','mediafiles/background_images/',72)
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
                existing_placements = ComposingArticleTemplate.objects.filter(id__in=template.article_placements.all().values_list('id', flat=True))
                existing_placements.delete()
                pos_index = 1
                for placement in json.loads(data['article_placements']):
                    if int(placement['width']) == 0 or int(placement['height']) == 0:
                        return Response(error("Not allowed 0 value for width or height!"))
                    placement_obj = ComposingArticleTemplate.objects.create(
                        pos_index = pos_index,
                        position_x = placement['position_x'], 
                        position_y = placement['position_y'], 
                        height = placement['height'], 
                        width = placement['width'], 
                        z_index = placement ['z_index'], 
                        created_by_id = request.user.pk, 
                        modified_by_id = request.user.pk
                    )
                    
                    placements_ids.append(placement_obj.pk)
                    pos_index += 1
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
    permission_classes = (IsAuthenticated,)
    def post(self, request, format=None):
        try:
            limit = int(request.data.get('limit', 10))
            offset = int(request.data.get('offset', 0))
        except ValueError:
            return Response(error( 'Invalid limit/offset.'))
        brands = request.data.get('brand', [])
        applications = request.data.get('application', [])
        article_numbers = request.data.get('article_number', [])
        article_list = request.data.get('article_list',[])
        article_filter = Q()
        for number in article_numbers:
            if '+' in number:
                number = int(number.replace('+', ''))
                article_filter |= Q(count__gte=number)
            else:
                number = int(number)
                article_filter |= Q(count=number)
        templates = ComposingTemplate.objects.all().order_by('-created')
        template_count = templates.count()
        products = Composing.objects.all().order_by('-created')
        articles = Article.objects.filter(articles__in=products).distinct()
        product_count = products.count()
        if brands:
            templates = templates.filter(brand__pk__in=brands).distinct()
            products = products.filter(template__brand__pk__in=brands)
        if applications:
            templates = templates.filter(application__pk__in=applications).distinct()
            products = products.filter(template__application__pk__in=applications).distinct()
        if article_list:
            product_ids = set(products.values_list('id', flat=True))
            for article_id in article_list:
                current_article_product_ids = set(products.filter(articles__mediaobject_id=article_id).values_list('id', flat=True))
                product_ids.intersection_update(current_article_product_ids)
            products = products.filter(id__in=product_ids) 
        templates = templates.annotate(count=Count('article_placements')).filter(article_filter)
        products = products.annotate(count=Count('articles')).filter(article_filter)
        paginator = LimitOffsetPagination()
        paginator.default_limit = limit
        paginator.offset = offset
        context_products = paginator.paginate_queryset(products, request)
        context_template = paginator.paginate_queryset(templates, request)
        template_serializer = ComposingTemplateSerializer(context_template, many=True)
        product_serializer = ComposingSerializer(context_products, many=True)
        article_serializer = ArticleSerializer(articles, many=True)
        document_last_update = Document.objects.latest('id').upload_date
        result = {
            "document_last_update":document_last_update,
            "template_count":template_count,
            "product_count":product_count,
            "templates":template_serializer.data,
            "products":product_serializer.data,
            "articles":article_serializer.data,
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
        template_id = data.get('template_id')
        articles_data = data.get('articles', [])
        articles = []
        if 'base64_img' not in data or ',' not in data['base64_img']:
            return Response(error("Invalid or missing base64_img"))
        template = ComposingTemplate.objects.get(id=template_id)
        base64_image = compose_render(template, articles_data) if data.get('base64_img', None) is None else data['base64_img']
        product = save_product_image(convert_image(base64_image, template.file_type, template.resolution_dpi), None)
        png_result = save_product_image(data['base64_img'], None) if template.file_type == 'TIFF' else ''
        for article_data in articles_data:
            article_data['created_by_id'] = request.user.id
            article_data['modified_by_id'] = request.user.id
            try:
                article = Article.objects.create(pos_index=article_data['pos_index'], name=article_data['name'], article_number=article_data['article_number'],mediaobject_id=article_data['mediaobject_id'],is_transparent=article_data['is_transparent'],scaling=article_data['scaling'],alignment=article_data['alignment'],height=article_data['height'],width=article_data['width'],z_index=article_data['z_index'],created_by_id=article_data['created_by_id'],modified_by_id=article_data['modified_by_id'])
                articles.append(article.pk)
            except Exception as e:
                return Response(error(str(e)))
        try:
            composing = Composing.objects.create(name = data['name'], template_id = data['template_id'], cdn_url = product, png_result = png_result,created_by_id = request.user.id, modified_by_id = request.user.id)
            composing.articles.set(articles)
        except Exception as e:
            return Response(error(str(e)))
        serializer = ComposingSerializer(composing)
        return Response(created(self, serializer.data))
    
    def put(self, request, format=None):
        data = request.data
        data['modified_by_id'] = request.user.id
        template_id = data.get('template_id')
        articles_data = data.get('articles', [])    
        composing = Composing.objects.get(id = data['id'])
        img_data = data.get('base64_img', None)
        if img_data is not None and img_data.startswith(f"data:image"):
            template = ComposingTemplate.objects.get(id=template_id)
            base64_image = compose_render(template, articles_data) if data.get('base64_img', None) is None else data['base64_img']
            product = save_product_image(convert_image(base64_image, template.file_type, template.resolution_dpi), composing.cdn_url)
            png_result = save_product_image(data['base64_img'], composing.png_result) if template.file_type == 'TIFF' else ''
            articles = []
            allowable_fields = ['id', 'pos_index', 'name', 'article_number', 'mediaobject_id', 'scaling', 'alignment', 'height', 'width', 'z_index', 'created_by_id', 'modified_by_id']
            for article_data in articles_data:
                article_data['modified_by_id'] = request.user.id
                article_data = {field: value for field, value in article_data.items() if field in allowable_fields}
                try:
                    if 'id' in article_data and Article.objects.filter(id=article_data['id']).exists():
                        article, created = Article.objects.update_or_create(
                            id=article_data['id'], defaults=article_data)
                    else:
                        article_data['created_by_id'] = request.user.id
                        article = Article.objects.create(**article_data)
                    
                    articles.append(article.pk)
                except Exception as e:
                    return Response(error(str(e)))
            try:
                composing.template_id = data.get('template_id', composing.template_id)
                composing.cdn_url = product
                composing.png_result = png_result
                composing.articles.set(articles)
            except Exception as e:
                return Response(error(str(e)))
        try:
            composing.name = data.get('name', composing.name)
            composing.modified_by_id = request.user.id
            composing.save()

        except Composing.DoesNotExist:
            return Response(error('Composing with id does not exist.'))
        except Exception as e:
            return Response(error(str(e)))
        composing = Composing.objects.get(id = data['id'])
        serializer = ComposingSerializer(composing)
        return Response(updated(self, serializer.data))  
class RefreshAPIView(APIView):
    def post(self, request, format=None):
        data = request.data
        template_id = data.get('template_id')
        if not template_id:
            return Response(error("Invalid or missing template_id"))
        articles_data = data.get('articles', [])
        try:
            template = ComposingTemplate.objects.get(id=template_id)
        except ComposingTemplate.DoesNotExist:
            return Response(error("Invalid or missing template_id"))
        try:
            base64_image = compose_render(template, articles_data)
        except Exception as e:
            return Response(server_error(str(e)))
        return Response(success(base64_image))
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
        composing = self.get_object(pk)
        serializer = ComposingSerializer(composing)
        return Response(serializer.data)

    def put(self, request, pk):
        composing = self.get_object(pk)
        serializer = ComposingSerializer(composing, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        composing = self.get_object(pk)
        composing.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
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
class PageDataAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self, request):
        brands = Brand.objects.all()
        applications = Application.objects.all()
        countries = Country.objects.all()
        templates = ComposingTemplate.objects.all()
        brand_data,application_data = {},{}
        for brand_el in brands:
            template_count = templates.filter(brand=brand_el).count()
            brand_data[str(brand_el.index)] = template_count
        for application_el in applications:
            template_count = templates.filter(application=application_el).count()
            application_data[str(application_el.index)] = template_count
        brand_serializer = BrandSerializer(brands, many=True)
        application_serializer = ApplicationSerializer(applications, many=True)
        country_serializer = CountrySerializer(countries, many=True)
        response_data = {
            'brands': brand_serializer.data,
            'applications': application_serializer.data,
            'country_list':country_serializer.data,            
            "brand_data":brand_data,
            "application_data":application_data,
        }
        return Response(success(response_data))
    def post(self, request):
        if request.user.is_staff is False:
            return Response(error("You are not authorized to perform this action"))
        data = request.data
        host = data.get('host')
        value = data.get('value')
        if not host or not value:
            return Response(error("Invalid or missing host or value id"))
        try:
            if host == 'brand':
                Brand.objects.create(name = value)
            elif host == 'application':
                Application.objects.create(name = value)
            elif host == 'country':
                Country.objects.create(name = value)
            else:
                return Response(error("Invalid host"))
        except IntegrityError:
            return Response(error("Name field must be unique"))
        except Exception as e:
            return Response(error(str(e)))
        brands = Brand.objects.all()
        applications = Application.objects.all()
        countries = Country.objects.all()

        brand_serializer = BrandSerializer(brands, many=True)
        application_serializer = ApplicationSerializer(applications, many=True)
        country_serializer = CountrySerializer(countries, many=True)
        response_data = {
            'brands': brand_serializer.data,
            'applications': application_serializer.data,
            'country_list':country_serializer.data
        }
        return Response(success(response_data))
    def put(self, request):
        if request.user.is_staff is False:
            return Response(error("You are not authorized to perform this action"))
        data = request.data
        host = data.get('host')
        pk = data.get('pk')
        value = data.get('value')
        if not host or not value:
            return Response(error("Invalid or missing host or value id"))
        try:
            if host == 'brand':
                brand = Brand.objects.get(pk=pk)
                brand.name = value
                brand.save()
            elif host == 'application':
                application = Application.objects.get(pk=pk)
                application.name = value
                application.save()
            elif host == 'country':
                country = Country.objects.get(pk=pk)
                country.name = value
                country.save()
            else:
                return Response(error("Invalid host"))

        except Brand.DoesNotExist:
            return Response(error("Brand does not exist"))
        except Application.DoesNotExist:
            return Response(error("Application does not exist"))
        except Country.DoesNotExist:
            return Response(error("Country does not exist"))
        except Exception as e:
            return Response(error(str(e)))
        brands = Brand.objects.all()
        applications = Application.objects.all()
        countries = Country.objects.all()

        brand_serializer = BrandSerializer(brands, many=True)
        application_serializer = ApplicationSerializer(applications, many=True)
        country_serializer = CountrySerializer(countries, many=True)
        response_data = {
            'brands': brand_serializer.data,
            'applications': application_serializer.data,
            'country_list':country_serializer.data
        }
        return Response(success(response_data))
    def delete(self, request):
        if request.user.is_staff is False:
            return Response(error("You are not authorized to perform this action"))
        data = request.data
        host = data.get('host')
        pk = data.get('pk')
        if not host:
            return Response(error("Invalid or missing host id"))
        try:
            if host == 'brand':
                brand = Brand.objects.get(pk=pk)
                brand.delete()
            elif host == 'application':
                application = Application.objects.get(pk=pk)
                application.delete()
            elif host == 'country':
                country = Country.objects.get(pk=pk)
                country.delete()
            else:
                return Response(error("Invalid host"))
        except Brand.DoesNotExist:
            return Response(error("Brand does not exist"))
        except Application.DoesNotExist:
            return Response(error("Application does not exist"))
        except Country.DoesNotExist:
            return Response(error("Country does not exist"))
        except Exception as e:
            return Response(error(str(e)))
        brands = Brand.objects.all()
        applications = Application.objects.all()
        countries = Country.objects.all()

        brand_serializer = BrandSerializer(brands, many=True)
        application_serializer = ApplicationSerializer(applications, many=True)
        country_serializer = CountrySerializer(countries, many=True)
        response_data = {
            'brands': brand_serializer.data,
            'applications': application_serializer.data,
            'country_list':country_serializer.data
        }
        return Response(success(response_data))