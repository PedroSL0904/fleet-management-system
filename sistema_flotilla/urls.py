from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),
    # ==========================================
    # AUTHENTICATION
    # ==========================================
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="control_vehicular/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="/login/"), name="logout"),
    # ==========================================
    # PASSWORD RESET FLOW
    # ==========================================
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="control_vehicular/password_reset.html",
            email_template_name="control_vehicular/password_reset_email.html",
            subject_template_name="control_vehicular/password_reset_subject.txt",
            success_url="/password-reset/enviado/",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/enviado/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="control_vehicular/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset/confirmar/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="control_vehicular/password_reset_confirm.html",
            success_url="/password-reset/completado/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/completado/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="control_vehicular/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    # ==========================================
    # APP
    # ==========================================
    path("", include("control_vehicular.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
