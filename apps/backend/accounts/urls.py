from django.urls import path

from . import views

urlpatterns = [
    path("auth/csrf/", views.CSRFView.as_view(), name="auth-csrf"),
    path("auth/register/", views.RegisterView.as_view(), name="auth-register"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    path("auth/mfa/enroll/", views.MFAEnrollView.as_view(), name="mfa-enroll"),
    path("auth/mfa/confirm/", views.MFAConfirmView.as_view(), name="mfa-confirm"),
    path("auth/mfa/disable/", views.MFADisableView.as_view(), name="mfa-disable"),
    path("auth/mfa/verify/", views.MFALoginVerifyView.as_view(), name="mfa-verify"),
]
