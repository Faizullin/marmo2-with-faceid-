from django.urls import path

from .views import user_face_id_auth, user_face_id_register


urlpatterns = [
    path('user-face-id/auth', user_face_id_auth, name='face-id-auth'),
    path('user-face-id/register', user_face_id_register, name='face-id-register'),
]
