from django.contrib.sites.shortcuts import get_current_site
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from accounts.serializers import *
from django.utils import timezone
import jwt
from app.util import *
from accounts.util import *

class LoginAPIView(APIView):
    def post(self, request, format = None):
        email = request.data['email']
        password = request.data['password']

        #find user using email
        user = User.objects.filter(email=email).first()

        if user is None:
            raise AuthenticationFailed('User not found:)')
            
        if not user.check_password(password):
            raise AuthenticationFailed('Invalid password')

        token = get_tokens_for_user(user)
        user.last_login = timezone.now()
        user.save()
        serializer = UserSerializer(user)
        response = Response()
        response.set_cookie(key="token", value=token["access_token"], httponly=True)
        response.data = {
            'user': serializer.data
        }

        #if password correct
        return response

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
        response = Response()
        response.set_cookie(key="token", value=token["access_token"], httponly=True)
        response.data = {
            'user': serializer.data
        }

        return response

class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)
    def post(self, request):
        request.user.auth_token.delete()
        return Response(success(self, "Logout Success"))
    
class ChangePasswordAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    def put(self, request):
        user = request.user
        body = request.data
        if 'old_password' in body and 'new_password' in body:
            if user.check_password(body['old_password']):
                user.set_password(body['new_password'])
                user.save()
                return Response(success(self, "Password Changed"))
            else:
                return Response(error(self, "Invalid Old Password"))
        else:
            return Response(error(self, "old_password and new_password are required"))
class UserDetailAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            user = request.user
            serializer = UserSerializer(user)
            return Response(success(self, serializer.data))
        except ObjectDoesNotExist:
            return Response(error(self,  "User does not exist."))
        except Exception as e:
            return Response(server_error(self, str(e)))

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
            return Response(success(self, serializer.data))
        except ValidationError as e:
            return Response(error(self,  e.detail))
        except Exception as e:
            return Response(server_error(self, str(e)))
class UserListAPIView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def get(self, request):
        try:
            users = User.objects.all()
            serializer = UserSerializer(users, many=True)
            return Response(success(self, serializer.data))

        except ObjectDoesNotExist:
            return Response(error(self, "No User Found!"))

        except Exception as e:
            return Response(server_error(self, str(e)))  

    def post(self, request, format=None):
        try:
            body = request.data
            if 'password' in body and 'email' in body:
                serializer = UserSerializer(data = body)
                if serializer.is_valid():
                    serializer.save()
                    user = User.objects.get(email=body['email'])
                    token = get_tokens_for_user(user)
                    protocol = request.scheme
                    magic_link = f"{protocol}://{get_current_site(request).domain}/api/vi/user/login?token={token['jwt_token']}"
                    data = {'user': serializer.data,'magic_link':magic_link}
                    return Response(created(self, data))
                return Response(error(self,'Invalid Data'))                        
            else:
                return Response(error(self,'Password and Email are Required'))

        except Exception as e:
            return Response(server_error(self, str(e)))

    def put(self, request):
        try:
            body = request.data
            user = User.objects.get(email=body['email'])
            serializer = UserSerializer(user, data=request.data, partial=True) 
            if serializer.is_valid():
                serializer.save()
                return Response(updated(self, serializer.data))
            return Response(error(self,'Invalid Data'))

        except ObjectDoesNotExist:
            return Response(error(self, "User Not Found!"))

        except Exception as e:
            return Response(server_error(self, str(e)))