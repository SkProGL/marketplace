from django.apps import apps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

# Management view
def management_access_required(view_function):
    """
    Management access decorator; wraps around view function it is assigned to.
    Determines authentication and user category.
    """
    # Wrapper serves in deferring execution for later requests
    # No wrapper => only runs at startup
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_superuser or request.user.category in ['Admin', 'Producer']):
            raise PermissionDenied
        return view_function(request, *args, **kwargs)
    return wrapper

# Model access
def get_all_models():
    model_names = []
    for model in apps.get_app_config('core').get_models():
        model_names.append(model.__name__)
    return model_names

MANAGE_MODEL_ACCESS = {
    'Admin':   get_all_models, 
    'Producer': ['Product', 'ProductBatch', 'Order', 'Recipe', 'StoryPost'],
    'Restaurant':      [],
    'Community group': [],
    'Customer':        [],
}
