from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.ParseAPIView.as_view()),
    path('filter', views.ProductFilterAPIView.as_view()),
    path('apikey/', views.APIKeyAPIView.as_view()),
    path('apikey/<int:pk>', views.APIKeyAPIView.as_view()),
    path('save/', views.SaveMediaAPIView.as_view()),
    path('compose/', views.ComposingGenAPIView.as_view()),
]