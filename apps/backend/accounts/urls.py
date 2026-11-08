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
    path("auth/passkeys/", views.PasskeyListView.as_view(), name="passkey-list"),
    path(
        "auth/passkeys/register/options/",
        views.PasskeyRegisterOptionsView.as_view(),
        name="passkey-register-options",
    ),
    path(
        "auth/passkeys/register/verify/",
        views.PasskeyRegisterVerifyView.as_view(),
        name="passkey-register-verify",
    ),
    path("auth/passkeys/<uuid:passkey_id>/remove/", views.PasskeyRemoveView.as_view(), name="passkey-remove"),
    path("auth/passkeys/only/", views.PasskeyOnlyView.as_view(), name="passkey-only"),
    path(
        "auth/passkeys/check/options/", views.PasskeyCheckOptionsView.as_view(), name="passkey-check-options"
    ),
    path("auth/passkeys/check/verify/", views.PasskeyCheckVerifyView.as_view(), name="passkey-check-verify"),
]
