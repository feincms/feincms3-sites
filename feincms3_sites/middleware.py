from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, MiddlewareNotUsed
from django.db.models import Q
from django.http import Http404, HttpResponsePermanentRedirect
from django.middleware.security import SecurityMiddleware

from feincms3.apps import (
    AppsMiddleware as BaseMiddleware, AppsMixin, apps_urlconf,
)
from feincms3.utils import concrete_model

from .models import Site


def apps_urlconf_for_site(site):
    page_model = concrete_model(AppsMixin)
    fields = (
        'path', 'application', 'app_instance_namespace', 'language_code',
    )
    apps = page_model.objects.active().filter(
        Q(site=site),
        ~Q(app_instance_namespace=''),
    ).values_list(*fields).order_by(*fields)
    return apps_urlconf(apps=apps)


class SiteMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.site = Site.objects.for_host(request.get_host())
        if request.site is None:
            raise Http404('No configuration found for %r' % request.get_host())
        return self.get_response(request)


class AppsMiddleware(BaseMiddleware):
    def __call__(self, request):
        request.site = Site.objects.for_host(request.get_host())
        if request.site is None:
            raise Http404('No configuration found for %r' % request.get_host())
        request.urlconf = apps_urlconf_for_site(request.site)
        return self.get_response(request)


class CanonicalDomainMiddleware(SecurityMiddleware):
    canonical_domain_secure = None

    def __init__(self, get_response):
        super().__init__(get_response)
        if settings.DEBUG:
            raise MiddlewareNotUsed

        self.canonical_domain_secure = getattr(
            settings,
            'CANONICAL_DOMAIN_SECURE',
            False,
        )

    def process_request(self, request):
        if not hasattr(request, 'site'):
            raise ImproperlyConfigured(
                'No "site" attribute on request. Insert SiteMiddleware'
                ' or AppsMiddleware before CanonicalDomainMiddleware.'
            )

        matches = request.get_host() == request.site.host
        if matches and self.canonical_domain_secure and request.is_secure():
            return
        elif matches and not self.canonical_domain_secure:
            return

        return HttpResponsePermanentRedirect('http%s://%s%s' % (
            's' if (
                self.canonical_domain_secure or request.is_secure()
            ) else '',
            request.site,
            request.get_full_path(),
        ))
