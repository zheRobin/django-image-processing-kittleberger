from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.http import StreamingHttpResponse
from pymongo import MongoClient
import zipfile
import json
import os
import re
import time
from master.models import *
from lxml import etree
from lxml.etree import XMLSyntaxError
from master.util import *
from app.util import *
import environ
from .models import APIKey
from .serializers import *
from compose.serializers import *
from accounts.models import User
from django.contrib.sites.shortcuts import get_current_site
from pymongo.errors import ConnectionFailure
from django.http import Http404
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
env = environ.Env()
environ.Env.read_env()

class APIKeyAPIView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)
    def post(self, request):
        try:
            user = User.objects.get(pk=request.user.pk)
            name = request.data['name']
            ak_obj = APIKey.objects.create(user=user, name = name)
            return Response(success( ak_obj.apikey))
        except User.DoesNotExist:
            return Response(error( "Bad request"))

    def get(self, request):
        try:
            api_keys = APIKey.objects.all()
            data = APIKeySerializer(api_keys, many=True).data
            return Response(success( data))
        except APIKey.DoesNotExist:
            return Response(error( "Bad request"))

    def delete(self, request, pk):
        try:
            apk_key = APIKey.objects.get(pk=pk)
            apk_key.delete()
            return Response(success( str(apk_key.apikey) + ": Deleted"))
        except APIKey.DoesNotExist:
            return Response(error( "Bad request"))
class ParseAPIView(APIView):
    def post(self, request):
        api_key = request.POST.get('api_key')
        api_key_instance = get_object_or_404(APIKey, apikey=api_key)
        api_key_instance.save()
        file = request.FILES['file']
        filepath = default_storage.save(os.path.join('temp', file.name), ContentFile(file.read()))

        try:
            client = MongoClient(host=env('MONGO_DB_HOST'))
            db = client[env('MONGO_DB_NAME')]
            collection_name = str(int(time.time()))
            collection = db[collection_name]
            def process(context):
                chunk = []
                for event, elem in context:
                    try:
                        chunk.append(convert(elem))
                        if len(chunk) == 1000:
                            collection.insert_many(chunk)
                            chunk.clear()  
                    except json.JSONDecodeError:
                        return Response(error( "Failed to decode JSON"))
                    except Exception as e:
                        return Response(server_error( f"Unexpected error: {str(e)}"))
                    finally:
                        elem.clear()
                        while elem.getprevious() is not None:
                            del elem.getparent()[0]
                if chunk:
                    collection.insert_many(chunk)
                    chunk.clear()

                Document.objects.create(file_id=collection_name)

        except ConnectionFailure:
            return Response(server_error( "Unable to connect to MongoDB"))

        if not zipfile.is_zipfile(filepath):
            return Response(error( "Not a valid zip file"))

        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            errors = []
            for f in zip_ref.namelist():
                if f.endswith('.xml'):
                    try:
                        start_time = time.time()
                        context = etree.iterparse(zip_ref.open(f), events=('end',), tag='mediaobject')
                        process(context)
                        end_time = time.time()
                        duration = end_time - start_time
                        print(f'Time taken: {duration} seconds')
                    except XMLSyntaxError:
                        errors.append(f"File {f} is not a well-formed XML document.")
                    except Exception as e:
                        return Response(error( str(e)))

        zip_ref.close()
        os.remove(filepath)

        if errors.__len__() > 0:
            return Response(created(self, errors))
        return Response(created(self, "Data inserted successfully"))
class ProductFilterAPIView(APIView):
    def get(self, request, format = None):
        client = MongoClient(host=os.getenv('MONGO_DB_HOST'))
        db = client[os.getenv('MONGO_DB_NAME')]
        file_id = Document.objects.latest('id').file_id
        product = request.GET.get('product', None)
        country = request.GET.get('country', None)
        page = int(request.GET.get('page', '1'))
        iter_limit = int(request.GET.get('limit', 30))
        regex_product = re.compile(product, re.IGNORECASE) if product else None
        regex_country = re.compile(country, re.IGNORECASE) if country else None
        query = []
        results = []
        if regex_product:
            query.append({"$or": [{"linked_products.mfact_key": regex_product}, {"linked_products.name": regex_product}]})

        if regex_country:
            query.append({"1_COUNTRY": regex_country})

        cursor = db[file_id].find({"$and": query}).skip((page-1) * iter_limit) if query else db[file_id].find().skip((page-1) * iter_limit)
        for document in cursor:
            cdn_urls = document.get('CDN_URLS')
            linked_products = document.get("linked_products", [])
            if cdn_urls and linked_products:
                document_id = str(document.get('_id', ''))
                for product in linked_products:
                    if regex_product is None or regex_product.search(product.get('mfact_key', '')) or regex_product.search(product.get('name', '')):
                        results.append({'document_id': document_id, 'article_number': product.get('mfact_key', ''), 'name': product.get('name', ''), 'cdn_urls': cdn_urls})
                    if len(results) == iter_limit:
                        break
            if len(results) == iter_limit:
                break
        result = {
            "current_page": page,
            "count": len(results),
            "products": results
        }
        return Response(success(result))
class SaveMediaAPIView(APIView):
    def post(self, request):
        image_url = request.data.get('image_url')
        remove_bg = request.data.get('remove_bg')
        if remove_bg == 1:
            result = remove_background(image_url)
        else:
            result = save_origin(image_url) 
        return Response(success(result))        
class ComposingGenAPIView(APIView):
    def validate_data(self, data):
        required_keys = ['template_id', 'articles']
        if not all(key in data for key in required_keys):
            raise ValidationError("Missing required field(s)")
        return data
    def get_template(self, template_id):
        try:
            return ComposingTemplate.objects.get(pk=template_id)
        except ComposingTemplate.DoesNotExist:
            raise Http404("The requested template does not exist")
    def post(self, request):
        data = self.validate_data(request.data)
        template = self.get_template(data['template_id'])
        compose = compose_render(template, data['articles'])

        return Response(success(compose))