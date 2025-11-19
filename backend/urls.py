from django.urls import path 
from rest_framework import routers

from . import views

router = routers.DefaultRouter()

router.register(r'faqs', views.FrequentlyAskedQuestionViewSet, basename='faq')
router.register(r'contact-messages', views.ContactMessageViewSet, basename='contact-message')

router.register(r'book-calendar', views.BookCalendarViewSet, basename='book-calendar')
# router.register(r'book-meet', views.BookMeetViewSet, basename='book-meet')
router.register(r'email-subscribe', views.EmailSubscribeViewSet, basename='email-subscribe')
router.register(r'blog-categories', views.BlogCategoryViewSet, basename='blog-category')
router.register(r'blog-posts', views.BlogPostViewSet, basename='blog-post')
router.register(r'privacy-policy', views.PrivacyPolicyViewSet, basename='privacy-policy')
router.register(r'terms-and-conditions', views.TermsAndConditionsViewSet, basename='terms-and-conditions')

urlpatterns = [
    path('signup/', views.sign_up, name='sign_up'),
    path('signin/', views.sign_in, name='sign_in'), 
    path('signout/', views.sign_out, name='sign_out'),
    path('calendly/event-types/', views.get_event_types, name='get_event_types'),
    
    path('google-oauth-callback/', views.google_oauth_callback, name='google_oauth_callback'),
    path('google/auth/callback/', views.google_oauth_callback, name='google_oauth_callback_alt'),
]

urlpatterns += router.urls
