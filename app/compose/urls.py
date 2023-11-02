from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('brand/', BrandAPIView.as_view()),
    path('application/', ApplicationAPIView.as_view()),
    path('templates/', TemplateAPIView.as_view()),
    path('templates/<int:pk>/', ComposingTemplateDetail.as_view()),
    path('templates/filter/', ComposingTemplateFilter.as_view()),
    path('article-template/', ComposingArticleTemplateList.as_view()),
    path('article/', ArticleAPIView.as_view()),
    path('product/', ComposingAPIView.as_view()),
    path('articles/<int:pk>/', ComposingArticleTemplateDetail.as_view()),
    path('product/<int:pk>/', ComposingDetail.as_view()),
]
