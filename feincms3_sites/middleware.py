from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404, HttpResponsePermanentRedirect

from feincms3.apps import AppsMixin, apps_urlconf
from feincms3.utils import concrete_model

from .models import Site


def apps_urlconf_for_site(site):
    page_model = concrete_model(AppsMixin)
    fields = (
        'path', 'application', 'app_instance_namespace', 'language_code',
    )
    apps = page_model.objects.active(site).exclude(
        app_instance_namespace='',
    ).values_list(*fields).order_by(*fields)
    return apps_urlconf(apps=apps)


def site_middleware(get_response):
    def middleware(request):
        request.site = Site.objects.for_host(request.get_host())
        if request.site is None:
            raise Http404('No configuration found for %r' % request.get_host())
        return get_response(request)
    return middleware


def apps_middleware(get_response):
    def middleware(request):
        request.site = Site.objects.for_host(request.get_host())
        if request.site is None:
            raise Http404('No configuration found for %r' % request.get_host())
        request.urlconf = apps_urlconf_for_site(request.site)
        return get_response(request)
    return middleware


def redirect_to_site_middleware(get_response):
    def middleware(request):
        if not hasattr(request, 'site'):
            raise ImproperlyConfigured(
                'No "site" attribute on request. Insert site_middleware'
                ' or apps_middleware before redirect_to_site_middleware.'
            )

        # Host matches, and either no HTTPS enforcement or already HTTPS
        if request.get_host() == request.site.host and (
                not settings.SECURE_SSL_REDIRECT or request.is_secure()
        ):
            return get_response(request)

        return HttpResponsePermanentRedirect('http%s://%s%s' % (
            's' if (
                settings.SECURE_SSL_REDIRECT or request.is_secure()
            ) else '',
            request.site,
            request.get_full_path(),
        ))
    return middleware
