from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # accounts
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout'),

    # admin interface
    url(r'^admin/', include(admin.site.urls)),

    # granadilla
    (r'', include('granadilla.urls')),
)
