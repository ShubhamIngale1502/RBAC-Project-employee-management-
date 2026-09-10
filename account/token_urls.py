from django.urls import path

from .views import blacklist_token


urlpatterns = [
    path('', blacklist_token, name='token_blacklist'),
]
