from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('templates/', TemplateAPIView.as_view()),
    path('templates/<int:pk>/', TemplateAPIView.as_view()),
    path('template/manage/', TemplateManage.as_view()),
    path('template/manage/<int:pk>', TemplateManageDetail.as_view()),
    path('composing/manage/', ComposingManage.as_view()),
    path('composing/manage/<int:pk>', ComposingManageDetail.as_view()),
    path('templates/filter', ComposingTemplateFilter.as_view()),
    path('products/filter', ComposingProductFilter.as_view()),
    path('article-template/', ComposingArticleTemplateList.as_view()),
    path('article/', ArticleAPIView.as_view()),
    path('product/', ComposingAPIView.as_view()),
    path('articles/<int:pk>/', ComposingArticleTemplateDetail.as_view()),
    path('product/<int:pk>/', ComposingDetail.as_view()),
    path('pagedata/', PageDataAPIView.as_view()),
    path('refresh/', RefreshAPIView.as_view()),
    path('setpreview/', SetPreviewImageAPIView.as_view()),
]
