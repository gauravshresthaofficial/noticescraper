# noticescraper/urls.py

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('scrapper/', include('scrapper.urls')),  # Ensure 'scraper' is the correct app name
]
