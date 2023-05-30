import contextvars
from contextlib import contextmanager

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404, HttpResponsePermanentRedirect
from django.utils.cache import patch_vary_headers
from django.utils.translation import activate, get_language, get_language_from_request
from feincms3.applications import _del_apps_urlconf_cache

# must use this import, do not change
from feincms3_sites.utils import get_site_model


_current_site = contextvars.ContextVar("current_site")


@contextmanager
def set_current_site(site):
    token = _current_site.set(site)
    _del_apps_urlconf_cache()
    yield
    _current_site.reset(token)
    _del_apps_urlconf_cache()


def current_site():
    return _current_site.get(None)


def site_middleware(get_response):
    def middleware(request):
        site_model = get_site_model()
        if site := site_model.objects.for_host(request.get_host()):
            with set_current_site(site):
                return get_response(request)
        raise Http404("No configuration found for %r" % request.get_host())

    return middleware


def redirect_to_site_middleware(get_response):
    def middleware(request):
        site = current_site()
        if not site:
            raise ImproperlyConfigured(
                "Current site unknown. Insert site_middleware before redirect_to_site_middleware."
            )

        # Host matches, and either no HTTPS enforcement or already HTTPS
        if request.get_host() == site.host and (
            not settings.SECURE_SSL_REDIRECT or request.is_secure()
        ):
            return get_response(request)

        return HttpResponsePermanentRedirect(
            "http{}://{}{}".format(
                "s" if (settings.SECURE_SSL_REDIRECT or request.is_secure()) else "",
                site.host,
                request.get_full_path(),
            )
        )

    return middleware


def default_language_middleware(get_response):
    def middleware(request):
        site = current_site()
        if not site:
            raise ImproperlyConfigured(
                "Current site unknown. Insert site_middleware before default_language_middleware."
            )

        # No i18n_patterns handling for now.
        language = site.default_language or get_language_from_request(request)
        activate(language)
        request.LANGUAGE_CODE = get_language()

        response = get_response(request)

        # Maybe not necessary, but do not take chances.
        patch_vary_headers(response, ("Accept-Language",))
        response.setdefault("Content-Language", get_language())
        return response

    return middleware
