from django.db import models
from django.contrib.auth import get_user_model

UserModel = get_user_model()


class UserFaceId(models.Model):
    model_path = models.CharField(max_length=255)
    user = models.OneToOneField(
        UserModel, null=True, blank=True, on_delete=models.SET_NULL, related_name="face_id")
    stats = models.JSONField()
