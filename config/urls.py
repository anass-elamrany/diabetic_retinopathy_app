# config/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from app.views import page_not_found as app_page_not_found

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='dashboard/', permanent=True)), 
    path('', include('app.urls')),
]

urlpatterns += [re_path(r'^.*$', app_page_not_found)]

handler404 = 'app.views.page_not_found'
