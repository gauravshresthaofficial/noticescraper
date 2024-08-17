# scraper/urls.py

from django.urls import path
from .views import scrape_images  # Adjust the import based on your view function name

urlpatterns = [
    path('scrape-images/', scrape_images, name='scrape_images'),
]
