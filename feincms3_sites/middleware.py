import contextvars
from contextlib import contextmanager

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404, HttpResponsePermanentRedirect
from django.utils import translation
from django.utils.cache import patch_vary_headers
from feincms3.applications import _del_apps_urlconf_cache

# must use this import, do not change
from .utils import get_site_model


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
        request.site = site_model.objects.for_host(request.get_host())
        if request.site is None:
            raise Http404("No configuration found for %r" % request.get_host())
        with set_current_site(request.site):
            return get_response(request)

    return middleware


def redirect_to_site_middleware(get_response):
    def middleware(request):
        if not hasattr(request, "site"):
            raise ImproperlyConfigured(
                'No "site" attribute on request. Insert site_middleware'
                " before redirect_to_site_middleware."
            )

        # Host matches, and either no HTTPS enforcement or already HTTPS
        if request.get_host() == request.site.host and (
            not settings.SECURE_SSL_REDIRECT or request.is_secure()
        ):
            return get_response(request)

        return HttpResponsePermanentRedirect(
            "http%s://%s%s"
            % (
                "s" if (settings.SECURE_SSL_REDIRECT or request.is_secure()) else "",
                request.site,
                request.get_full_path(),
            )
        )

    return middleware


def default_language_middleware(get_response):
    def middleware(request):
        if not hasattr(request, "site"):
            raise ImproperlyConfigured(
                'No "site" attribute on request. Insert site_middleware'
                " before default_language_middleware."
            )

        # No i18n_patterns handling for now.
        if request.site.default_language:
            language = request.site.default_language
        else:
            language = translation.get_language_from_request(request)
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

        response = get_response(request)

        # Maybe not necessary, but do not take chances.
        patch_vary_headers(response, ("Accept-Language",))
        response.setdefault("Content-Language", translation.get_language())
        return response

    return middleware
