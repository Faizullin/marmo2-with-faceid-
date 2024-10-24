from django.contrib import admin

from .models import UserFaceId


@admin.register(UserFaceId)
class UserFaceIdAdmin(admin.ModelAdmin):
    list_display = ('user', )
    search_fields = ('user',)
    ordering = ('-id',)

    # def get_urls(self):
    #     urls = super().get_urls()
    #     custom_urls = [
    #         path('perform-action/<int:obj_id>/',
    #              self.perform_action, name='perform_action'),
    #     ]
    #     return custom_urls + urls

    # def retrain_action(self, request, obj_id):
    #     response = requests.post(
    #         url=f"{settings.FACEAPI_URL}/api/v1/user-face-id/retrain",
    #         json={"key": "admin-sender-key"}
    #     )
    #     response_data = response.json()
    #     print("response", response, response_data)

    #     self.message_user(request, f"Reatrain response: {response_data}")
    #     return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    

    # def retrain_action_button(self, obj):
    #     if self.has_permission(self.request):
    #         return format_html('<a class="button" href="{}">Reatrain All</a>', 
    #                            self.get_action_url(obj.id))
