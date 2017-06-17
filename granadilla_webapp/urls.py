from django.conf.urls import include, url

from django.contrib import admin
from django.contrib.auth import views as auth_views
admin.autodiscover()

urlpatterns = [
    # accounts
    url(r'^accounts/login/$', auth_views.login),
    url(r'^accounts/logout/$', auth_views.logout, name='auth-logout'),

    # admin interface
    url(r'^admin/', admin.site.urls),

    # granadilla
    url(r'', include('granadilla.urls')),
]
