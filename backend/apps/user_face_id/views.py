from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings


def user_face_id_auth(request):
    context = {
        "ws_user_face_id_auth": f"{settings.FACEAPI_URL}/api/v1/user-face-id/auth"
    }
    return render(request, 'user_face_id/auth_user_face.html', context=context)

@login_required
def user_face_id_register(request):
    context = {
        "ws_user_face_id_register": f"{settings.FACEAPI_URL}/api/v1/user-face-id/register"
    }
    return render(request, 'user_face_id/register_user_face.html', context=context)
