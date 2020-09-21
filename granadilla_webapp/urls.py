from django.urls import include, path

from django.contrib import admin
from django.contrib.auth import views as auth_views
admin.autodiscover()

urlpatterns = [
    # accounts
    path('accounts/login/', auth_views.LoginView.as_view()),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='auth-logout'),

    # admin interface
    path('admin/', admin.site.urls),

    # granadilla
    path('', include('granadilla.urls')),
]
