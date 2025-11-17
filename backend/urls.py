from django.urls import path 
from rest_framework import routers

from . import views

router = routers.DefaultRouter()

router.register(r'faqs', views.FrequentlyAskedQuestionViewSet, basename='faq')
router.register(r'contact-messages', views.ContactMessageViewSet, basename='contact-message')

router.register(r'book-calendar', views.BookCalendarViewSet, basename='book-calendar')
router.register(r'book-meet', views.BookMeetViewSet, basename='book-meet')
router.register(r'email-subscribe', views.EmailSubscribeViewSet, basename='email-subscribe')

urlpatterns = [
    path('signup/', views.sign_up, name='sign_up'),
    path('signin/', views.sign_in, name='sign_in'), 
    path('signout/', views.sign_out, name='sign_out'),
    path('calendly/event-types/', views.get_event_types, name='get_event_types'),
]

urlpatterns += router.urls
