from django.urls import path
from .views import home, scrape_images

urlpatterns = [
    path('', home, name='home'),
    path('scrape/', scrape_images, name='scrape_images'),
]
