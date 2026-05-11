# from django.contrib.auth import login
# from django.conf import settings
# from django.contrib.auth import get_user_model
#
# User = get_user_model()
#
#
# class AutoLoginMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response
#
#     def __call__(self, request):
#         if settings.DEBUG and not request.user.is_authenticated:
#             superuser = User.objects.filter(is_superuser=True).first()
#             if superuser:
#                 login(request, superuser,
#                       backend='django.contrib.auth.backends.ModelBackend')
#
#         response = self.get_response(request)
#         return response
