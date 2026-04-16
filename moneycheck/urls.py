from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tracker.urls')),
    # Password reset confirm (Django built-in)
    path(
        'password-reset/confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='tracker/auth/password_reset_confirm.html',
            success_url='/login/',
        ),
        name='password_reset_confirm',
    ),
]
