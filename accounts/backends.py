from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


def axes_username(request, credentials=None):
    credentials = credentials or {}
    return (
        (
            credentials.get("username")
            or credentials.get("email")
            or request.POST.get("username", "")
        )
        .strip()
        .lower()
    )


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = (kwargs.get("email") or username or "").strip().lower()
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
