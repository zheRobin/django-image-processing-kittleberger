from django.urls import path
from . import views

urlpatterns = [
    path('media/', views.ParseAPIView.as_view()),
    path('apikey/', views.APIKeyAPIView.as_view()),
    path('apikey/<int:pk>', views.APIKeyAPIView.as_view()),
    path('remove-background/', views.ImageBGRemovalAPIView.as_view()),
]