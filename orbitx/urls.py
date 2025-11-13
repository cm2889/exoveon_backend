
from django.contrib import admin
from django.urls import path, include 
from django.conf import settings 
from django.conf.urls.static import static 
from rest_framework import permissions 
from drf_yasg.views import get_schema_view 
from drf_yasg import openapi 

schema_view = get_schema_view(
    openapi.Info(
        title="OrbitX API",
        default_version='v0',
        description="API documentation for OrbitX",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="dev@orbitx.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

api_documentation_urls = [
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("backend.urls")),
] + api_documentation_urls + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
