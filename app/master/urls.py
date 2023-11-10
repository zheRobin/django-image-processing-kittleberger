from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.ParseAPIView.as_view()),
    path('filter', views.ProductFilterAPIView.as_view()),
    path('apikey/', views.APIKeyAPIView.as_view()),
    path('apikey/<int:pk>', views.APIKeyAPIView.as_view()),
    path('remove-background/', views.ImageBGRemovalAPIView.as_view()),
    path('product-download/', views.ProductImageAPIView.as_view()),
]