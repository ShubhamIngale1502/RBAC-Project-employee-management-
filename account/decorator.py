from django.contrib.auth import get_user_model
User = get_user_model()
from django.urls import reverse
from django.shortcuts import redirect

def LoginRequired(function):
    """Decorator ensuring user is authenticated before accessing view."""

    def wrap(request, *args, **kwargs):
        try:
            if request.user and request.user.is_authenticated:
                user_id = request.user.id
                User.objects.get(id=user_id)
            else:
                return redirect(
                    "%s?next=%s" % (reverse("login"), reverse("homepage"))
                )
        except (User.DoesNotExist, AttributeError):
            return redirect(
                "%s?next=%s" % (reverse("login"), reverse("homepage"))
            )

        return function(request, *args, **kwargs)

    return wrap
