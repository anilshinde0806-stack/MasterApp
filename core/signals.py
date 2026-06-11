from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import UserLoginActivity


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


@receiver(user_logged_in)
def record_user_login(sender, request, user, **kwargs):
    if not request or not user:
        return

    UserLoginActivity.objects.create(
        user=user,
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
        session_key=request.session.session_key or "",
    )
