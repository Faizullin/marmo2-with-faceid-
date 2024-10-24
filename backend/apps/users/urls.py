from django.urls import path

from .views import *

urlpatterns = [
    path('', home, name='users-home'),
    path('register/', RegisterView.as_view(), name='users-register'),
    path('profile/', profile, name='users-profile'),

    path('send_qr_code/', send_qr_code, name='send_qr_code'),
    path('qr_login/<str:token>/', qr_login, name='qr_login'),

    path('logout/', logout_view)
]
