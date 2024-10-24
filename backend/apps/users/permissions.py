from datetime import timedelta
from functools import wraps

from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode


def face_id_verified_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise Exception("Add is_authenticated permissions before")

        if request.user.face_id_verified:
            time_elapsed = timezone.now() - request.user.face_id_verified_at
            if time_elapsed < timedelta(hours=1):
                return view_func(request, *args, **kwargs)
        next_url = request.path
        return redirect(f"{reverse('face-id-auth')}?{urlencode({'next': next_url})}")

    return _wrapped_view
