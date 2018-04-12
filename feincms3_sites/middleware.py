from feincms3.apps import (
    AppsMiddleware as BaseMiddleware, AppsMixin, apps_urlconf,
)
from feincms3.utils import concrete_model

from .models import Site


class AppsMiddleware(BaseMiddleware):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.site = Site.objects.for_host(request.get_host())
        page_model = concrete_model(AppsMixin)
        fields = (
            'path', 'application', 'app_instance_namespace', 'language_code',
        )
        apps = page_model.objects.active().filter(site=request.site).exclude(
            app_instance_namespace=''
        ).values_list(*fields).order_by(*fields)
        request.urlconf = apps_urlconf(apps)
        return self.get_response(request)
