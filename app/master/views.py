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
from bson.objectid import ObjectId
from bson.errors import InvalidId
from django.core.exceptions import ObjectDoesNotExist
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
            return Response(success(self, ak_obj.apikey))
        except User.DoesNotExist:
            return Response(error(self, "Bad request"))

    def get(self, request):
        try:
            api_keys = APIKey.objects.all()
            data = APIKeySerializer(api_keys, many=True).data
            return Response(success(self, data))
        except APIKey.DoesNotExist:
            return Response(error(self, "Bad request"))

    def delete(self, request, pk):
        try:
            apk_key = APIKey.objects.get(pk=pk)
            apk_key.delete()
            return Response(success(self, str(apk_key.apikey) + ": Deleted"))
        except APIKey.DoesNotExist:
            return Response(error(self, "Bad request"))
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
                        return Response(error(self, "Failed to decode JSON"))
                    except Exception as e:
                        return Response(server_error(self, f"Unexpected error: {str(e)}"))
                    finally:
                        elem.clear()
                        while elem.getprevious() is not None:
                            del elem.getparent()[0]
                if chunk:
                    collection.insert_many(chunk)
                    chunk.clear()

                Document.objects.create(file_id=collection_name)

        except ConnectionFailure:
            return Response(server_error(self, "Unable to connect to MongoDB"))

        if not zipfile.is_zipfile(filepath):
            return Response(error(self, "Not a valid zip file"))

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
                        return Response(error(self, str(e)))

        zip_ref.close()
        os.remove(filepath)

        if errors.__len__() > 0:
            return Response(created(self, errors))
        return Response(created(self, "Data inserted successfully"))
class ProductFilterAPIView(APIView):
    def get(self, request, format = None):
        try:
            client = MongoClient(host=env('MONGO_DB_HOST'))
            db = client[env('MONGO_DB_NAME')]
        except ConnectionFailure:
            return Response(server_error(self, "MongoDB server is not available"))
        except Exception as e:
            return Response(server_error(self, str(e)))
        try:
            file_id = Document.objects.latest('id').file_id
        except Document.DoesNotExist:
            return Response(server_error(self, "No Document objects exist"))        
        product = request.GET.get('product', None)
        country = request.GET.get('country', None)
        page = int(request.GET.get('page', '1'))
        regex_product = None
        regex_country = None
        query = []
        if product:
            regex_product = re.compile(product, re.IGNORECASE)
            product_query = {
                "$or": [
                    {"linked_products.mfact_key": regex_product},
                    {"linked_products.name": regex_product}
                ]
            }
            query.append(product_query)
        if country:
            regex_country = re.compile(country, re.IGNORECASE)
            query.append({"1_COUNTRY": regex_country})
        if query:
            cursor = db[file_id].find({"$and": query})
        else:
            cursor = db[file_id].find()
        return StreamingHttpResponse(stream_results(self, cursor, regex_product, page),content_type='application/json')
class ImageBGRemovalAPIView(APIView):
    def post(self, request):
        document_id = request.data.get('document_id')
        image_url = request.data.get('image_url')
        try:
            client = MongoClient(host=env('MONGO_DB_HOST'))
            db = client[env('MONGO_DB_NAME')]
            file_id = Document.objects.latest('id').file_id
            document = db[file_id].find_one({'_id': ObjectId(document_id)})
        except (ConnectionFailure, ObjectDoesNotExist, InvalidId) as err:
            if isinstance(err, ConnectionFailure):
                error_message = "MongoDB server is not available"
            elif isinstance(err, ObjectDoesNotExist):
                error_message = "No Document objects exist"
            elif isinstance(err, InvalidId):
                error_message = "Invalid ID"
            return Response(server_error(self, error_message))
        except Exception as e:
            return Response(server_error(self, str(e)))
        if not document.get('TRANS_IMG'):
            if image_url:
                trans_img = remove_background(self, image_url)
                db[file_id].update_one({"_id": ObjectId(document_id)}, {"$set": {"TRANS_IMG": trans_img}})
            result = {
                "CDN_URLS": document.get('CDN_URLS'),
                "TRANS_IMG": trans_img,
            }
            return Response(success(self, result))
        else:
            result = {
                "CDN_URLS": document.get('CDN_URLS'),
                "TRANS_IMG": document.get('TRANS_IMG'),
            }
            return Response(success(self, result))
class ProductImageAPIView(APIView):
    def get_template(self, template_id):
        try:
            return ComposingTemplate.objects.get(pk=template_id)
        except ComposingTemplate.DoesNotExist:
            raise Http404("The requested template does not exist")

    def validate_data(self, data):
        required_keys = ['template_id', 'background_url', 'articles']

        if not all(key in data for key in required_keys):
            raise ValidationError("Missing required field(s)")

        return data

    def post(self, request):
        try:
            data = self.validate_data(request.data)
            template = self.get_template(data['template_id'])
            product = combine_images(self, data['background_url'], data['articles'], template)
            return Response(success(self, product), status=status.HTTP_200_OK)

        except ValidationError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        except Http404 as error:
            return Response({'detail': str(error)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            return Response({'detail': str(error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)