from django.urls import path 
from rest_framework import routers

from . import views

router = routers.DefaultRouter()

router.register(r'faqs', views.FrequentlyAskedQuestionViewSet, basename='faq')
router.register(r'contact-messages', views.ContactMessageViewSet, basename='contact-message')
router.register(r'book-calendar', views.BookCalendarViewSet, basename='book-calendar')
router.register(r'email-subscribe', views.EmailSubscribeViewSet, basename='email-subscribe')
router.register(r'wait-lists', views.WaitListViewSet, basename='wait-list') 
router.register(r'blog-categories', views.BlogCategoryViewSet, basename='blog-category')
router.register(r'blog-posts', views.BlogPostViewSet, basename='blog-post')
router.register(r'privacy-policy', views.PrivacyPolicyViewSet, basename='privacy-policy')
router.register(r'terms-and-conditions', views.TermsAndConditionsViewSet, basename='terms-and-conditions')
router.register(r'sessions', views.SessionViewSet, basename='session')
router.register(r'chat-windows', views.ChatWindowViewSet, basename='chat-window')

urlpatterns = [
    path('signup/', views.sign_up, name='sign_up'),
    path('signin/', views.sign_in, name='sign_in'), 
    path('signout/', views.sign_out, name='sign_out'),
    path('google/auth/', views.google_auth, name='google_auth'),
    path('google/auth/callback/', views.google_auth_callback, name='google_auth_callback'),
]

urlpatterns += router.urls
