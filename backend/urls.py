from django.urls import path 
from rest_framework import routers

from . import views

router = routers.DefaultRouter()

router.register(r'faqs', views.FrequentlyAskedQuestionViewSet, basename='faq')
router.register(r'contact-messages', views.ContactMessageViewSet, basename='contact-message')

urlpatterns = [
    path('signup/', views.sign_up, name='sign_up'),
    path('signin/', views.sign_in, name='sign_in'), 
    path('signout/', views.sign_out, name='sign_out'), 
]

urlpatterns += router.urls
