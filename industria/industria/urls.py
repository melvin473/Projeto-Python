from django.contrib import admin
from django.urls import path
from dashboard.views import index
from dashboard.views import TelemetriaVibracaoAPIView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('api/v1/telemetria/', TelemetriaVibracaoAPIView.as_view(), name='api_telemetria'),
]
