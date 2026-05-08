from django.apps import apps
from django.contrib import admin

# Register all models
app_models = apps.get_app_config('core').get_models()

for model in app_models:
    try:
        admin.site.register(model)
    except Exception as e:
        print("Error registering:", e)
        pass

