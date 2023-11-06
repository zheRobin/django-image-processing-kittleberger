from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)
urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('manage/', views.UserListAPIView.as_view(), name='user_manage'),
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('change-password/', views.ChangePasswordAPIView.as_view(), name='change_password'),
    path('setting/', views.UserDetailAPIView.as_view(), name='user_setting')
]