from django.contrib.sites.shortcuts import get_current_site
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from accounts.serializers import *
from compose.serializers import *
from django.utils import timezone
import jwt
from app.util import *
from accounts.util import *

class LoginAPIView(APIView):
    def post(self, request, format=None):
        email = request.data['email']
        password = request.data['password']
        user = User.objects.filter(email=email).first()
        if user is None:
            raise AuthenticationFailed('User not found:)')            
        if not user.check_password(password):
            raise AuthenticationFailed('Invalid password')
        
        token = get_tokens_for_user(user)
        user.last_login = timezone.now()
        user.save()       
        user_serializer = UserSerializer(user)

        response_data = {
            'user': user_serializer.data,
            'access_token': token["access_token"],
        }
        return Response(success( response_data))

    def get(self, request):
        token = request.GET.get('token')

        if not token:
            raise AuthenticationFailed("Unauthenticated!")
        
        try:
            payload = jwt.decode(token, 'secret', algorithms="HS256")
            #decode gets the user

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Unauthenticated!")
        
        user = User.objects.filter(id=payload['id']).first()
        token = get_tokens_for_user(user)
        user.last_login = timezone.now()
        user.save()
        serializer = UserSerializer(user)
        response_data = {
            'user': serializer.data,
            'access_token': token["access_token"]
        }

        return Response(success( response_data))

class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)
    def post(self, request):
        request.user.auth_token.delete()
        return Response(success( "Logout Success"))
    
class ChangePasswordAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    def put(self, request):
        user = request.user
        body = request.data
        if 'old_password' in body and 'new_password' in body:
            if user.check_password(body['old_password']):
                user.set_password(body['new_password'])
                user.save()
                return Response(success( "Password Changed"))
            else:
                return Response(error( "Invalid Old Password"))
        else:
            return Response(error( "old_password and new_password are required"))
class UserDetailAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            user = request.user
            serializer = UserSerializer(user)
            return Response(success( serializer.data))
        except ObjectDoesNotExist:
            return Response(error(  "User does not exist."))
        except Exception as e:
            return Response(server_error( str(e)))

    def put(self, request):
        try:
            user = request.user
            body = request.data
            if 'email' in body:
                user.email = body['email']
            if 'username' in body:
                user.username = body['username']
            if 'password' in body:
                user.set_password(body['password'])
            
            user.save()
            serializer = UserSerializer(user)
            return Response(success( serializer.data))
        except ValidationError as e:
            return Response(error(  e.detail))
        except Exception as e:
            return Response(server_error( str(e)))
class UserListAPIView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def get(self, request):
        try:
            users = User.objects.all().exclude(is_superuser=True).order_by('username')
            serializer = UserSerializer(users, many=True)
            return Response(success( serializer.data))

        except ObjectDoesNotExist:
            return Response(error( "No User Found!"))

        except Exception as e:
            return Response(server_error( str(e)))  

    def post(self, request, format=None):
        try:
            user_data = request.data
            if 'password' in user_data and 'email' in user_data:
                user = User.objects.create(email = user_data['email'], username = user_data['name'])
                user.is_staff = user_data.get('is_admin', False)
                user.set_password(user_data['password'])
                user.save()
                token = get_tokens_for_user(user)
                protocol = request.scheme
                magic_link = f"{protocol}://{get_current_site(request).domain}/api/vi/user/login?token={token['jwt_token']}"
                serializer = UserSerializer(user)
                data = {'user': serializer.data,'magic_link':magic_link}
                return Response(created(self, data))                  
            else:
                return Response(error('Password and Email are Required'))

        except Exception as e:
            return Response(server_error( str(e)))

    def put(self, request,user_id):
        try:
            data = request.data
            user = User.objects.get(id=user_id)
            if 'email' in data and data['email'].strip():
                user.email = data['email']
            if 'username' in data and data['username'].strip():
                user.username = data['username']
            if 'password' in data and data['password'].strip():
                user.set_password(data['password'])
            user.is_staff = data.get('is_admin', False)
            user.save()
            serializer = UserSerializer(user)
            return Response(updated(self, serializer.data))

        except ObjectDoesNotExist:
            return Response(error( "User Not Found!"))

        except Exception as e:
            return Response(server_error( str(e)))
    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return Response(deleted(self))
        except ObjectDoesNotExist:
            return Response(error("User Not Found!"))
        except Exception as e:
            return Response(server_error(str(e)))